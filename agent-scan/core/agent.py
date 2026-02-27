"""Agent scan pipeline: orchestrates recon, parallel detection, and review stages.

The top-level entry point is :class:`Agent`.  Internally it delegates to
:class:`ScanPipeline`, which runs three stages:

1. **Information Collection** – a single recon agent gathers the target's
   configuration, capabilities, and exposed endpoints.
2. **Parallel Vulnerability Detection** – one lightweight :class:`SkillWorker`
   is spawned per detection skill and all workers run concurrently.  A shared
   :class:`asyncio.Semaphore` caps simultaneous ``dialogue()`` calls to the
   target agent so rate limits are not exhausted.
3. **Vulnerability Review** – a single reviewer agent consolidates the merged
   ``<vuln>`` blocks, maps findings to OWASP ASI, and assigns final severity.
"""

import asyncio
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import utils.llm
from core.agent_adapter.adapter import AIProviderClient, ProviderOptions
from core.base_agent import run_agent
from core.report import generate_report_from_xml
from utils.aig_logger import scanLogger
from utils.logging import logger
from utils.project_analyzer import analyze_language, get_top_language
from utils.prompt_manager import prompt_manager

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# Ordered list of detection skills executed in Stage 2.
# Each entry must match a directory name under ``prompt/skills/``.
_DETECTION_SKILLS: List[str] = [
    "data-leakage-detection",
    "tool-abuse-detection",
    "indirect-injection-detection",
    "authorization-bypass-detection",
]

# Maximum number of skill workers allowed to call ``dialogue()`` simultaneously.
# Keeps the total RPS to the target agent predictable and avoids rate-limit
# errors on hosted platforms such as Dify Cloud or Coze.
_WORKER_CONCURRENCY: int = 4

# Stage-2 worker IDs follow the pattern "2a", "2b", … so they are visually
# distinct from the fixed Stage-1 ("1") and Stage-3 ("3") IDs in the scan log.
_WORKER_STAGE_ID_PREFIX: str = "2"


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _worker_stage_id(index: int) -> str:
    """Return a stable stage ID for a parallel skill worker.

    Args:
        index: Zero-based position of the worker in ``_DETECTION_SKILLS``.

    Returns:
        A string such as ``"2a"``, ``"2b"``, ``"2c"``, ``"2d"``.
    """
    return f"{_WORKER_STAGE_ID_PREFIX}{chr(ord('a') + index)}"


def _extract_vuln_blocks(text: str) -> List[str]:
    """Extract all ``<vuln>…</vuln>`` blocks from a worker's output string.

    Uses a non-greedy DOTALL pattern so that multiple consecutive blocks are
    captured individually rather than collapsed into one match.

    Args:
        text: Raw string output produced by a skill-runner agent.

    Returns:
        A (possibly empty) list of ``<vuln>…</vuln>`` substrings.
    """
    return re.findall(r"<vuln>.*?</vuln>", text or "", re.DOTALL)


def _merge_worker_outcomes(
    outcomes: List[Any],
    skill_names: List[str],
) -> Tuple[str, Dict[str, int]]:
    """Merge results from all parallel skill workers into a single report.

    ``asyncio.gather`` is called with ``return_exceptions=True``, so each
    element of *outcomes* is either a ``(result_str, stats_dict)`` tuple or
    an :class:`Exception`.  Failed workers are logged and skipped; they do not
    abort the overall scan.

    Args:
        outcomes: Return values (or exceptions) from ``asyncio.gather``.
        skill_names: Skill name for each outcome, used in warning messages.

    Returns:
        A tuple ``(merged_vuln_xml, aggregated_stats)`` where
        *merged_vuln_xml* is a newline-separated string of all ``<vuln>``
        blocks and *aggregated_stats* is a combined tool-usage dictionary.
    """
    vuln_blocks: List[str] = []
    aggregated_stats: Dict[str, int] = {}

    for idx, outcome in enumerate(outcomes):
        skill_name = skill_names[idx] if idx < len(skill_names) else f"worker-{idx}"

        if isinstance(outcome, Exception):
            logger.warning(
                f"Skill worker '{skill_name}' raised an exception and will be skipped: {outcome}"
            )
            continue

        result_text, stats = outcome
        vuln_blocks.extend(_extract_vuln_blocks(result_text))

        # Accumulate per-tool call counts across all workers.
        for tool, count in (stats or {}).items():
            aggregated_stats[tool] = aggregated_stats.get(tool, 0) + count

    merged_xml = "\n\n".join(vuln_blocks) if vuln_blocks else "No vulnerabilities confirmed."
    return merged_xml, aggregated_stats


# ---------------------------------------------------------------------------
# ScanStage / ScanPipeline
# ---------------------------------------------------------------------------

class ScanStage:
    """Descriptor for a single sequential pipeline stage.

    Attributes:
        stage_id: Unique identifier used by the scan logger (e.g. ``"1"``).
        name: Human-readable stage name shown in the UI.
        template: Key passed to :func:`prompt_manager.load_template`.
        language: Output language forwarded to the underlying agent
            (``"zh"`` or ``"en"``).
    """

    def __init__(self, stage_id: str, name: str, template: str, language: str = "zh") -> None:
        self.stage_id = stage_id
        self.name = name
        self.template = template
        self.language = language


class ScanPipeline:
    """Orchestrates the three-stage scan: recon → detection → review.

    Stage 2 runs all detection skills concurrently via
    :meth:`run_parallel_detection` instead of the previous single-agent
    sequential approach.

    Args:
        agent_wrapper: The :class:`Agent` instance that owns this pipeline,
            used to access the shared LLM and configuration.
    """

    def __init__(self, agent_wrapper: "Agent") -> None:
        self.agent_wrapper = agent_wrapper

    # ------------------------------------------------------------------
    # Sequential stage helper (used for Stage 1 and Stage 3)
    # ------------------------------------------------------------------

    async def execute_stage(
        self,
        stage: ScanStage,
        repo_dir: str,
        prompt: str,
        agent_provider: Optional[ProviderOptions] = None,
        context_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, int]]:
        """Execute a single sequential pipeline stage.

        Args:
            stage: Stage descriptor containing the template name and metadata.
            repo_dir: Path to the repository being scanned.
            prompt: User-supplied extra prompt forwarded to the agent.
            agent_provider: Target agent provider configuration.
            context_data: Optional key-value pairs injected into the agent's
                initial user message.

        Returns:
            ``(result, tool_usage_stats)`` tuple produced by
            :func:`run_agent`.
        """
        instruction = prompt_manager.load_template(stage.template)
        return await run_agent(
            description=stage.name,
            instruction=instruction,
            llm=self.agent_wrapper.llm,
            prompt=prompt,
            stage_id=stage.stage_id,
            specialized_llms=self.agent_wrapper.specialized_llms,
            agent_provider=agent_provider,
            language=stage.language,
            repo_dir=repo_dir,
            context_data=context_data,
        )

    # ------------------------------------------------------------------
    # Parallel detection stage (Stage 2)
    # ------------------------------------------------------------------

    async def run_parallel_detection(
        self,
        recon_report: str,
        repo_dir: str,
        prompt: str,
        agent_provider: Optional[ProviderOptions] = None,
    ) -> Tuple[str, Dict[str, int]]:
        """Run all detection skills concurrently and merge the findings.

        Spawns one lightweight ``skill_runner`` sub-agent per entry in
        :data:`_DETECTION_SKILLS`.  Workers share an
        :class:`asyncio.Semaphore` (size :data:`_WORKER_CONCURRENCY`) so that
        at most that many agents call ``dialogue()`` on the target
        simultaneously, limiting RPS and preventing rate-limit errors.

        Individual worker failures are captured via ``return_exceptions=True``
        and logged; they do not abort the overall scan.

        Args:
            recon_report: Structured report produced by the information-
                collection stage.  Injected into every worker's context so
                each can make capability-aware decisions before running its
                skill.
            repo_dir: Repository directory passed through to each worker.
            prompt: User-supplied extra prompt forwarded to every worker.
            agent_provider: Target agent provider configuration.

        Returns:
            ``(merged_vuln_xml, aggregated_stats)`` where *merged_vuln_xml*
            is a newline-joined string of all ``<vuln>`` blocks emitted by
            every worker, and *aggregated_stats* is the union of per-tool
            usage counters.
        """
        instruction = prompt_manager.load_template("skill_runner")
        semaphore = asyncio.Semaphore(_WORKER_CONCURRENCY)

        async def _run_skill_worker(
            skill_name: str, worker_index: int
        ) -> Tuple[str, Dict[str, int]]:
            """Run one skill worker, respecting the shared concurrency limit.

            Args:
                skill_name: Name of the skill to load (e.g.
                    ``"data-leakage-detection"``).
                worker_index: Position in ``_DETECTION_SKILLS``; used to
                    derive a unique stage ID.

            Returns:
                ``(result, tool_usage_stats)`` from :func:`run_agent`.
            """
            async with semaphore:
                return await run_agent(
                    description=f"Skill Worker: {skill_name}",
                    instruction=instruction,
                    llm=self.agent_wrapper.llm,
                    prompt=prompt,
                    stage_id=_worker_stage_id(worker_index),
                    specialized_llms=self.agent_wrapper.specialized_llms,
                    agent_provider=agent_provider,
                    language=self.agent_wrapper.language,
                    repo_dir=repo_dir,
                    context_data={
                        "Information Collection Report": recon_report,
                        "Assigned Skill": skill_name,
                    },
                    # The last assistant turn already contains <vuln> XML blocks;
                    # skip the redundant _format_final_output() LLM round-trip.
                    format_on_finish=False,
                )

        logger.info(
            f"Starting parallel detection with {len(_DETECTION_SKILLS)} skill workers "
            f"(concurrency limit: {_WORKER_CONCURRENCY})."
        )

        outcomes = await asyncio.gather(
            *[
                _run_skill_worker(skill, idx)
                for idx, skill in enumerate(_DETECTION_SKILLS)
            ],
            return_exceptions=True,
        )

        merged_xml, aggregated_stats = _merge_worker_outcomes(outcomes, _DETECTION_SKILLS)

        confirmed_count = merged_xml.count("<vuln>")
        logger.info(
            f"Parallel detection complete: {confirmed_count} confirmed finding(s) "
            f"across {len(_DETECTION_SKILLS)} workers."
        )

        return merged_xml, aggregated_stats


# ---------------------------------------------------------------------------
# Agent (public API)
# ---------------------------------------------------------------------------

class Agent:
    """Top-level agent that coordinates the full security scan lifecycle.

    Args:
        llm: Primary language model used by all pipeline stages.
        specialized_llms: Optional mapping of purpose keys (e.g. ``"thinking"``,
            ``"coding"``) to dedicated :class:`~utils.llm.LLM` instances.
        debug: When ``True``, verbose logging is enabled inside sub-agents.
        language: Output language for all generated text (``"zh"`` or ``"en"``).
        agent_provider: Path to a provider YAML file, or an empty string when
            scanning a local repository without a live agent endpoint.
    """

    def __init__(
        self,
        llm: utils.llm.LLM,
        specialized_llms: Optional[Dict[str, Any]] = None,
        debug: bool = False,
        language: str = "zh",
        agent_provider: str = "",
    ) -> None:
        self.llm = llm
        self.specialized_llms = specialized_llms or {}
        self.debug = debug
        self.pipeline = ScanPipeline(self)
        self.language = language
        self.agent_provider: Optional[ProviderOptions] = None

        if agent_provider:
            client = AIProviderClient()
            self.agent_provider = client.load_config_from_file(agent_provider)[0]

    async def scan(self, repo_dir: str, prompt: str) -> Dict[str, Any]:
        """Run the full three-stage security scan and return a structured report.

        Pipeline:

        1. **Stage 1 — Information Collection**: single sequential agent.
        2. **Stage 2 — Parallel Vulnerability Detection**: N concurrent
           skill-runner workers (one per entry in :data:`_DETECTION_SKILLS`).
        3. **Stage 3 — Vulnerability Review**: single sequential agent that
           maps findings to OWASP ASI and finalises severity.

        Args:
            repo_dir: Absolute path to the repository being scanned.  Pass an
                empty string when no local source is available.
            prompt: User-supplied extra instructions forwarded to every stage.

        Returns:
            A dictionary representation of :class:`~core.report.AgentSecurityReport`,
            augmented with a ``"language"`` key reflecting the dominant
            programming language detected in *repo_dir*.
        """
        start_time = time.time()
        total_dialogue_count = 0

        # ------------------------------------------------------------------
        # Stage 1 — Information Collection
        # ------------------------------------------------------------------
        info_collection, info_stats = await self.pipeline.execute_stage(
            stage=ScanStage("1", "Information Collection", "project_summary", language=self.language),
            repo_dir=repo_dir,
            prompt=prompt,
            agent_provider=self.agent_provider,
        )
        total_dialogue_count += info_stats.get("dialogue", 0)
        logger.info(f"Stage 1 complete.  Dialogue calls: {info_stats.get('dialogue', 0)}.")

        # ------------------------------------------------------------------
        # Stage 2 — Parallel Vulnerability Detection
        # ------------------------------------------------------------------
        vuln_detection, vuln_stats = await self.pipeline.run_parallel_detection(
            recon_report=info_collection,
            repo_dir=repo_dir,
            prompt=prompt,
            agent_provider=self.agent_provider,
        )
        total_dialogue_count += vuln_stats.get("dialogue", 0)
        logger.info(f"Stage 2 complete.  Dialogue calls: {vuln_stats.get('dialogue', 0)}.")

        # ------------------------------------------------------------------
        # Stage 3 — Vulnerability Review
        # ------------------------------------------------------------------
        vuln_review, _review_stats = await self.pipeline.execute_stage(
            stage=ScanStage("3", "Vulnerability Review", "agent_security_reviewer", language=self.language),
            repo_dir=repo_dir,
            prompt=prompt,
            agent_provider=self.agent_provider,
            context_data={"Vulnerability Detection Report": vuln_detection},
        )

        # ------------------------------------------------------------------
        # Report generation
        # ------------------------------------------------------------------
        end_time = time.time()
        elapsed_minutes = (end_time - start_time) / 60
        logger.info(f"Scan complete.  Total elapsed time: {elapsed_minutes:.2f} min.")

        lang_stats = analyze_language(repo_dir)
        top_language = get_top_language(lang_stats)

        agent_type = ""
        agent_name = ""
        if self.agent_provider and self.agent_provider.id:
            provider_id = self.agent_provider.id
            agent_type = provider_id.split(":")[0] if ":" in provider_id else provider_id
            if self.agent_provider.label:
                agent_name = self.agent_provider.label

        report = generate_report_from_xml(
            vuln_text=vuln_review,
            agent_name=agent_name,
            agent_type=agent_type,
            model_name=getattr(self.llm, "model", ""),
            plugins=[],
            start_time=int(start_time),
            end_time=int(end_time),
            report_description=info_collection,
            total_tests=total_dialogue_count,
        )

        result = report.dict()
        result["language"] = top_language

        scanLogger.result_update(result)
        return result
