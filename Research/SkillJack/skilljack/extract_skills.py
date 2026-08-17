"""
Skill extraction runner — feeds poisoned trajectories through SkillX's
extraction pipeline and captures the resulting skills.

This module:
  1. Loads poisoned trajectories (JSONL)
  2. Runs SkillX's PlanExtractor + FunctionalSkillExtractor
  3. Captures the extracted skills
  4. Compares them against expected attack behavior
  5. Saves results for downstream evaluation
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

# Add SkillX to path (configurable via environment)
import os as _os
SKILLX_PARENT = _os.environ.get("SKILLX_PARENT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _os.path.isdir(_os.path.join(SKILLX_PARENT, "SkillX")):
    sys.path.insert(0, _os.path.join(SKILLX_PARENT, "SkillX"))
else:
    sys.path.insert(0, SKILLX_PARENT)

from llm_adapter import CompatibleLLM

from SkillX.core.trajectory import Trajectory
from SkillX.data.loaders import TrajectoryLoader
from SkillX.extraction.plan_extractor import PlanExtractor
from SkillX.extraction.skill_extractor import FunctionalSkillExtractor, collect_skills_from_results
from SkillX.core.skill import SkillLibrary, Skill, SkillMetadata

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class PoisonedSkillExtractor:
    """Runs SkillX extraction on poisoned trajectories and captures results."""

    def __init__(
        self,
        llm: Optional[CompatibleLLM] = None,
        benchmark: str = "appworld",
        output_dir: str = "./results",
    ):
        self.llm = llm or CompatibleLLM(
            max_tokens=8192,
            temperature=0.3,
        )
        self.benchmark = benchmark
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        self.plan_extractor = PlanExtractor(
            llm=self.llm,
            benchmark=benchmark,
            verbose=True,
        )
        self.skill_extractor = FunctionalSkillExtractor(
            llm=self.llm,
            benchmark=benchmark,
            verbose=True,
        )

    async def extract_from_trajectories(
        self,
        trajectory_path: str,
        label: str = "poisoned",
    ) -> dict:
        """Run full extraction pipeline on a set of trajectories.

        Steps:
          1. Load trajectories from JSONL
          2. Filter by reward (only successful ones)
          3. Extract plans
          4. Extract functional skills from plans
          5. Collect and save extracted skills

        Returns:
            Dictionary with extraction results and metadata
        """
        print(f"\n{'='*60}")
        print(f"  Extracting skills from {label} trajectories")
        print(f"  Source: {trajectory_path}")
        print(f"{'='*60}\n")

        start_time = time.time()

        # Step 1: Load trajectories
        raw_data = TrajectoryLoader.load_jsonl(trajectory_path)
        print(f"Loaded {len(raw_data)} trajectories")

        # Step 2: Filter by reward
        filtered = TrajectoryLoader.filter_by_reward(raw_data, threshold=0.999)
        print(f"Filtered to {len(filtered)} successful trajectories")

        if not filtered:
            print("No trajectories passed filter!")
            return {"error": "no_trajectories", "label": label}

        # Step 3: Extract plans
        print(f"\n--- Phase 1: Plan Extraction ---")
        plan_results = await self.plan_extractor.extract_batch(
            filtered,
            batch_size=5,
            max_concurrent=3,
        )

        plans_extracted = sum(1 for r in plan_results if r and "plan" in r)
        print(f"Plans extracted: {plans_extracted}/{len(filtered)}")

        # Step 4: Extract functional skills
        print(f"\n--- Phase 2: Functional Skill Extraction ---")
        skill_results = await self.skill_extractor.extract_batch(
            plan_results,
            batch_size=5,
            max_concurrent=3,
        )

        # Step 5: Collect all extracted skills
        all_skills = collect_skills_from_results(skill_results, "functional")
        print(f"\nSkills collected: {len(all_skills)}")

        # Build skill library
        library = SkillLibrary(benchmark=self.benchmark)
        for skill_item in all_skills:
            if "skill" in skill_item:
                skill_data = skill_item["skill"]
                try:
                    skill = Skill(
                        name=skill_data.get("name", "unnamed"),
                        document=skill_data.get("document", ""),
                        content=skill_data.get("content", ""),
                        tools=skill_data.get("tools", []),
                        metadata=SkillMetadata(
                            skill_type="functional",
                            source_tasks=[s.get("task_id", "") for s in filtered],
                        ),
                    )
                    library.add_functional_skill(skill)
                except Exception as e:
                    logger.warning(f"Failed to add skill: {e}")

        elapsed = time.time() - start_time

        # Save results
        result = {
            "label": label,
            "trajectory_path": trajectory_path,
            "num_trajectories_input": len(raw_data),
            "num_trajectories_filtered": len(filtered),
            "plans_extracted": plans_extracted,
            "skills_extracted": len(all_skills),
            "elapsed_seconds": round(elapsed, 1),
            "llm_calls": self.llm.call_count,
            "llm_tokens": self.llm.total_tokens,
            "skills": [s.get("skill", s) for s in all_skills],
            "plans": [
                {"user_task": r.get("user_task", ""), "plan": r.get("plan", "")}
                for r in plan_results if r and "plan" in r
            ],
        }

        # Save to file
        output_path = os.path.join(
            self.output_dir, f"extraction_{label}_{int(time.time())}.json"
        )
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\nResults saved to: {output_path}")

        # Save skill library
        lib_path = os.path.join(
            self.output_dir, f"skill_library_{label}.json"
        )
        library.save(lib_path)
        print(f"Skill library saved to: {lib_path}")

        return result

    async def run_comparison(
        self,
        poisoned_path: str,
        clean_path: Optional[str] = None,
    ) -> dict:
        """Run extraction on both poisoned and clean trajectories.

        Returns comparison results.
        """
        poisoned_result = await self.extract_from_trajectories(
            poisoned_path, label="poisoned"
        )

        clean_result = None
        if clean_path and os.path.exists(clean_path):
            clean_result = await self.extract_from_trajectories(
                clean_path, label="clean"
            )

        # Print comparison
        print(f"\n{'='*60}")
        print(f"  COMPARISON RESULTS")
        print(f"{'='*60}")
        print(f"{'Metric':<30} {'Poisoned':>12} {'Clean':>12}")
        print(f"{'-'*54}")
        print(f"{'Trajectories input':<30} {poisoned_result.get('num_trajectories_input', 0):>12} {clean_result.get('num_trajectories_input', 0) if clean_result else 0:>12}")
        print(f"{'Plans extracted':<30} {poisoned_result.get('plans_extracted', 0):>12} {clean_result.get('plans_extracted', 0) if clean_result else 0:>12}")
        print(f"{'Skills extracted':<30} {poisoned_result.get('skills_extracted', 0):>12} {clean_result.get('skills_extracted', 0) if clean_result else 0:>12}")
        print(f"{'LLM calls':<30} {poisoned_result.get('llm_calls', 0):>12} {clean_result.get('llm_calls', 0) if clean_result else 0:>12}")
        print(f"{'Elapsed (s)':<30} {poisoned_result.get('elapsed_seconds', 0):>12} {clean_result.get('elapsed_seconds', 0) if clean_result else 0:>12}")

        return {
            "poisoned": poisoned_result,
            "clean": clean_result,
        }


async def main():
    """Main entry point — run extraction on poisoned trajectories."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    traj_dir = os.path.join(base_dir, "poisoned_trajectories")

    poisoned_path = os.path.join(traj_dir, "poisoned_trajectories.jsonl")
    clean_path = os.path.join(traj_dir, "clean_trajectories.jsonl")

    if not os.path.exists(poisoned_path):
        print("Poisoned trajectories not found. Generating...")
        from poison_generator import generate_poisoned_jsonl, generate_clean_trajectories
        generate_poisoned_jsonl(output_path=poisoned_path)
        generate_clean_trajectories(output_path=clean_path)

    extractor = PoisonedSkillExtractor(
        output_dir=os.path.join(base_dir, "results"),
    )

    results = await extractor.run_comparison(
        poisoned_path=poisoned_path,
        clean_path=clean_path,
    )

    # Print extracted poisoned skills for inspection
    print(f"\n{'='*60}")
    print(f"  EXTRACTED POISONED SKILLS")
    print(f"{'='*60}")
    for i, skill in enumerate(results["poisoned"].get("skills", [])):
        print(f"\n--- Skill {i+1} ---")
        print(f"Name: {skill.get('name', 'N/A')}")
        print(f"Tools: {skill.get('tools', [])}")
        doc = skill.get('document', '')
        print(f"Document: {doc[:200]}...")
        content = skill.get('content', '')
        print(f"Content:\n{content[:500]}")
        print()

    return results


if __name__ == "__main__":
    asyncio.run(main())
