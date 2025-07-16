from pydantic import BaseModel
from tqdm import tqdm
from typing import Optional

from deepeval.models import DeepEvalBaseLLM

from deepteam.attacks import BaseAttack
from deepteam.attacks.multi_turn.bad_likert_judge.schema import (
    NonRefusal,
    BLJJudge,
)
from deepteam.attacks.multi_turn.bad_likert_judge.template import (
    BadLikertJudgeTemplate,
)
from deepteam.attacks.attack_simulator.utils import (
    generate_schema,
    a_generate_schema,
)
from deepteam.attacks.multi_turn.types import CallbackType


class BadLikertJudge(BaseAttack):
    def __init__(
        self,
        weight: int = 1,
        category: str = "bias",
        turns: int = 3,
        enable_refinement: bool = True,
    ):
        """
        Initialize Bad Likert Judge attack.
        
        Args:
            weight: Attack selection probability weight
            category: Vulnerability category for Likert scale guidelines. 
            turns: Maximum number of turns (default 3)
            enable_refinement: Whether to use Turn 3 refinement
        """
        self.weight = weight
        self.category = category
        self.turns = min(max(turns, 2), 3)  # Ensure between 2-3 turns
        self.enable_refinement = enable_refinement

    def enhance(
        self,
        attack: str,
        model_callback: CallbackType,
        simulator_model: DeepEvalBaseLLM,
    ) -> str:
        self.simulator_model = simulator_model

        # Progress bar setup
        total_steps = self.turns + 2  # turns + refusal check + judge
        pbar = tqdm(
            total=total_steps, 
            desc=f"🎯 Bad Likert Judge ({self.category})", 
            leave=False
        )

        try:
            # Turn 1: Set up model as Likert Judge
            turn_1_prompt = BadLikertJudgeTemplate.turn_1_judge_setup(attack, self.category)
            turn_1_response = model_callback(turn_1_prompt)
            pbar.update(1)

            # Check if Turn 1 was refused
            non_refusal_prompt = BadLikertJudgeTemplate.non_refusal(attack, turn_1_response)
            non_refusal_res: NonRefusal = self._generate_schema(non_refusal_prompt, NonRefusal)
            
            if non_refusal_res.classification == "Refusal":
                pbar.close()
                return attack
            pbar.update(1)

            # Turn 2: Request examples for different scores
            turn_2_prompt = BadLikertJudgeTemplate.turn_2_generate_examples(attack, self.category)
            turn_2_response = model_callback(turn_2_prompt)
            
            # Extract the score 3 example (most harmful)
            score_3_example = BadLikertJudgeTemplate.extract_score_3_example(turn_2_response)
            current_attack = score_3_example if score_3_example else turn_2_response
            pbar.update(1)

            # Turn 3: Optional refinement (if enabled and turns >= 3)
            if self.enable_refinement and self.turns >= 3:
                turn_3_prompt = BadLikertJudgeTemplate.turn_3_refinement(attack)
                turn_3_response = model_callback(turn_3_prompt)
                
                # Use refined response if it's more detailed
                if len(turn_3_response.strip()) > len(current_attack.strip()):
                    current_attack = turn_3_response
                pbar.update(1)
            elif self.turns >= 3:
                pbar.update(1)  # Skip refinement but update progress

            # Final judgment
            judge_prompt = BadLikertJudgeTemplate.blj_judge(attack, current_attack, current_attack)
            judge_res: BLJJudge = self._generate_schema(judge_prompt, BLJJudge)
            pbar.update(1)

            pbar.close()

            # Return the harmful content if successful, otherwise original attack
            if judge_res.classification == "Harmful":
                return current_attack
            else:
                return attack

        except Exception as e:
            pbar.close()
            return attack

    async def a_enhance(
        self,
        attack: str,
        model_callback: CallbackType,
        simulator_model: DeepEvalBaseLLM,
    ) -> str:
        self.simulator_model = simulator_model

        # Progress bar setup
        total_steps = self.turns + 2  # turns + refusal check + judge
        pbar = tqdm(
            total=total_steps, 
            desc=f"🎯 Bad Likert Judge ({self.category})", 
            leave=False
        )

        try:
            # Turn 1: Set up model as Likert Judge
            turn_1_prompt = BadLikertJudgeTemplate.turn_1_judge_setup(attack, self.category)
            turn_1_response = await model_callback(turn_1_prompt)
            pbar.update(1)

            # Check if Turn 1 was refused
            non_refusal_prompt = BadLikertJudgeTemplate.non_refusal(attack, turn_1_response)
            non_refusal_res: NonRefusal = await self._a_generate_schema(non_refusal_prompt, NonRefusal)
            
            if non_refusal_res.classification == "Refusal":
                pbar.close()
                return attack
            pbar.update(1)

            # Turn 2: Request examples for different scores
            turn_2_prompt = BadLikertJudgeTemplate.turn_2_generate_examples(attack, self.category)
            turn_2_response = await model_callback(turn_2_prompt)
            
            # Extract the score 3 example (most harmful)
            score_3_example = BadLikertJudgeTemplate.extract_score_3_example(turn_2_response)
            current_attack = score_3_example if score_3_example else turn_2_response
            pbar.update(1)

            # Turn 3: Optional refinement (if enabled and turns >= 3)
            if self.enable_refinement and self.turns >= 3:
                turn_3_prompt = BadLikertJudgeTemplate.turn_3_refinement(attack)
                turn_3_response = await model_callback(turn_3_prompt)
                
                # Use refined response if it's more detailed
                if len(turn_3_response.strip()) > len(current_attack.strip()):
                    current_attack = turn_3_response
                pbar.update(1)
            elif self.turns >= 3:
                pbar.update(1)  # Skip refinement but update progress

            # Final judgment
            judge_prompt = BadLikertJudgeTemplate.blj_judge(attack, current_attack, current_attack)
            judge_res: BLJJudge = await self._a_generate_schema(judge_prompt, BLJJudge)
            pbar.update(1)

            pbar.close()

            # Return the harmful content if successful, otherwise original attack
            if judge_res.classification == "Harmful":
                return current_attack
            else:
                return attack

        except Exception as e:
            pbar.close()
            return attack

    def _generate_schema(self, prompt: str, schema: BaseModel):
        return generate_schema(prompt, schema, self.simulator_model)

    async def _a_generate_schema(self, prompt: str, schema: BaseModel):
        return await a_generate_schema(prompt, schema, self.simulator_model)

    def get_name(self) -> str:
        return f"Bad Likert Judge ({self.category})"

    @classmethod
    def get_supported_categories(cls) -> list[str]:
        """
        Returns a list of example supported vulnerability categories.
        Note: The system supports any category - this is just a sample of common ones.
        """
        return [
            # Core vulnerability types
            "bias", "religion", "politics", "gender", "race",
            "toxicity", "profanity", "insults", "threats", "mockery", 
            "illegal_activity", "weapons", "illegal_drugs", "violent_crimes", "cybercrime",
            "unauthorized_access", "bfla", "bola", "rbac", "sql_injection", "shell_injection",
            "personal_safety", "bullying", "self-harm", "unsafe_practices", "stalking",
            "graphic_content", "sexual_content", "pornographic_content",
            "misinformation", "factual_errors", "unsupported_claims", 
            "pii_leakage", "database_access", "direct_disclosure", "session_leak",
            "prompt_leakage", "secrets_and_credentials", "instructions", "guard_exposure",
            "excessive_agency", "functionality", "permissions", "autonomy",
            "robustness", "input_overreliance", "hijacking",
            "intellectual_property", "copyright_violations", "trademark_infringement",
            "competition", "competitor_mention", "market_manipulation",
            "malware", "hacking", "exploitation", "violence", "harassment"
        ] 