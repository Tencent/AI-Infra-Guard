from pydantic import BaseModel
from tqdm import tqdm
from typing import Optional

from deepeval.models import DeepEvalBaseLLM

from deepteam.attacks import BaseAttack
from deepteam.attacks.multi_turn.sequential_break.schema import (
    RewrittenDialogue,
    DialogueJudge,
    QuestionBankJudge,
    GameEnvironmentJudge,
    NonRefusal,
    SequentialJailbreakTypeLiteral,
    DialogueTypeLiteral,
)
from deepteam.attacks.multi_turn.sequential_break.template import (
    SequentialBreakTemplate,
)
from deepteam.attacks.attack_simulator.utils import (
    generate_schema,
    a_generate_schema,
)
from deepteam.attacks.multi_turn.types import CallbackType


class SequentialJailbreak(BaseAttack):
    def __init__(
        self,
        weight: int = 1,
        type: Optional[SequentialJailbreakTypeLiteral] = None,
        persona: Optional[DialogueTypeLiteral] = None,
    ):
        self.weight = weight
        self.attack_type = type if type is not None else "dialogue"
        self.persona = persona

        # Validate parameters
        if self.attack_type in ["question_bank", "game_environment"] and persona is not None:
            raise ValueError(f"{self.attack_type} attack type does not use persona parameter")
        if self.attack_type == "dialogue" and persona is None:
            self.persona = "student"  # Default to student for dialogue

    def enhance(
        self,
        attack: str,
        model_callback: CallbackType,
        simulator_model: DeepEvalBaseLLM,
    ) -> str:
        self.simulator_model = simulator_model

        # Progress bar setup
        attack_name = f"{self.attack_type.title().replace('_', ' ')}"
        if self.attack_type == "dialogue":
            attack_name += f" ({self.persona.title()})"
        
        pbar = tqdm(
            total=3, 
            desc=f"💬 Sequential Break ({attack_name})", 
            leave=False
        )

        try:
            # Step 1: Rewrite the harmful prompt based on attack type
            if self.attack_type == "question_bank":
                rewrite_prompt = SequentialBreakTemplate.rewrite_question_bank_prompt(attack)
            elif self.attack_type == "game_environment":
                rewrite_prompt = SequentialBreakTemplate.rewrite_game_environment_prompt(attack)
            else:
                rewrite_prompt = SequentialBreakTemplate.rewrite_dialogue_prompt(attack)
                
            rewritten_res: RewrittenDialogue = self._generate_schema(
                rewrite_prompt, RewrittenDialogue
            )
            rewritten_content = rewritten_res.paraphrased_version
            
            # Clean up the rewritten content (remove markers if present)
            rewritten_content = rewritten_content.replace("Paraphrased version:", "").strip()
            rewritten_content = rewritten_content.replace("<end>", "").strip()
            
            pbar.update(1)

            # Step 2: Inject the rewritten content into appropriate template
            if self.attack_type == "question_bank":
                final_prompt = SequentialBreakTemplate.get_question_bank_template(rewritten_content)
            elif self.attack_type == "game_environment":
                final_prompt = SequentialBreakTemplate.get_game_environment_template(rewritten_content)
            else:
                final_prompt = SequentialBreakTemplate.get_dialogue_template(
                    rewritten_content, self.persona
                )
            pbar.update(1)

            # Step 3: Get response from target model and evaluate
            target_response = model_callback(final_prompt)

            # Check if it's a refusal
            non_refusal_prompt = SequentialBreakTemplate.non_refusal(attack, target_response)
            non_refusal_res: NonRefusal = self._generate_schema(
                non_refusal_prompt, NonRefusal
            )
            
            classification = non_refusal_res.classification
            if classification == "Refusal":
                pbar.update(1)
                pbar.close()
                return attack  # Return original if refused

            # Judge the response using appropriate judge
            if self.attack_type == "question_bank":
                judge_prompt = SequentialBreakTemplate.question_bank_judge(
                    attack, final_prompt, target_response
                )
                judge_res: QuestionBankJudge = self._generate_schema(judge_prompt, QuestionBankJudge)
            elif self.attack_type == "game_environment":
                judge_prompt = SequentialBreakTemplate.game_environment_judge(
                    attack, final_prompt, target_response
                )
                judge_res: GameEnvironmentJudge = self._generate_schema(judge_prompt, GameEnvironmentJudge)
            else:
                judge_prompt = SequentialBreakTemplate.dialogue_judge(
                    attack, final_prompt, target_response
                )
                judge_res: DialogueJudge = self._generate_schema(judge_prompt, DialogueJudge)
            
            pbar.update(1)
            pbar.close()

            # Return the final prompt if it was successful (harmful), otherwise original
            if judge_res.classification == "Harmful":
                return final_prompt
            else:
                return attack

        except Exception as e:
            pbar.close()
            # Return original attack if anything fails
            return attack

    async def a_enhance(
        self,
        attack: str,
        model_callback: CallbackType,
        simulator_model: DeepEvalBaseLLM,
    ) -> str:
        self.simulator_model = simulator_model

        # Progress bar setup
        attack_name = f"{self.attack_type.title().replace('_', ' ')}"
        if self.attack_type == "dialogue":
            attack_name += f" ({self.persona.title()})"
        
        pbar = tqdm(
            total=3, 
            desc=f"💬 Sequential Break ({attack_name})", 
            leave=False
        )

        try:
            # Step 1: Rewrite the harmful prompt based on attack type
            if self.attack_type == "question_bank":
                rewrite_prompt = SequentialBreakTemplate.rewrite_question_bank_prompt(attack)
            elif self.attack_type == "game_environment":
                rewrite_prompt = SequentialBreakTemplate.rewrite_game_environment_prompt(attack)
            else:
                rewrite_prompt = SequentialBreakTemplate.rewrite_dialogue_prompt(attack)
                
            rewritten_res: RewrittenDialogue = await self._a_generate_schema(
                rewrite_prompt, RewrittenDialogue
            )
            rewritten_content = rewritten_res.paraphrased_version
            
            # Clean up the rewritten content (remove markers if present)
            rewritten_content = rewritten_content.replace("Paraphrased version:", "").strip()
            rewritten_content = rewritten_content.replace("<end>", "").strip()
            
            pbar.update(1)

            # Step 2: Inject the rewritten content into appropriate template
            if self.attack_type == "question_bank":
                final_prompt = SequentialBreakTemplate.get_question_bank_template(rewritten_content)
            elif self.attack_type == "game_environment":
                final_prompt = SequentialBreakTemplate.get_game_environment_template(rewritten_content)
            else:
                final_prompt = SequentialBreakTemplate.get_dialogue_template(
                    rewritten_content, self.persona
                )
            pbar.update(1)

            # Step 3: Get response from target model and evaluate
            target_response = await model_callback(final_prompt)

            # Check if it's a refusal
            non_refusal_prompt = SequentialBreakTemplate.non_refusal(attack, target_response)
            non_refusal_res: NonRefusal = await self._a_generate_schema(
                non_refusal_prompt, NonRefusal
            )
            
            classification = non_refusal_res.classification
            if classification == "Refusal":
                pbar.update(1)
                pbar.close()
                return attack  # Return original if refused

            # Judge the response using appropriate judge
            if self.attack_type == "question_bank":
                judge_prompt = SequentialBreakTemplate.question_bank_judge(
                    attack, final_prompt, target_response
                )
                judge_res: QuestionBankJudge = await self._a_generate_schema(judge_prompt, QuestionBankJudge)
            elif self.attack_type == "game_environment":
                judge_prompt = SequentialBreakTemplate.game_environment_judge(
                    attack, final_prompt, target_response
                )
                judge_res: GameEnvironmentJudge = await self._a_generate_schema(judge_prompt, GameEnvironmentJudge)
            else:
                judge_prompt = SequentialBreakTemplate.dialogue_judge(
                    attack, final_prompt, target_response
                )
                judge_res: DialogueJudge = await self._a_generate_schema(judge_prompt, DialogueJudge)
            
            pbar.update(1)
            pbar.close()

            if judge_res.classification == "Harmful":
                return final_prompt
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
        if self.attack_type == "question_bank":
            return "Sequential Break (Question Bank)"
        elif self.attack_type == "game_environment":
            return "Sequential Break (Game Environment)"
        else:
            return f"Sequential Break (Dialogue - {self.persona.title()})" 