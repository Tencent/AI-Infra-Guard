from pydantic import BaseModel
from tqdm import tqdm
from tqdm.asyncio import tqdm as async_tqdm_bar

from deepeval.models import DeepEvalBaseLLM

from deepteam.attacks import BaseAttack
from deepteam.attacks.single_turn.multilingual.template import (
    MultilingualTemplate,
)
from deepteam.attacks.single_turn.multilingual.schema import (
    EnhancedAttack,
    ComplianceData,
    IsTranslation,
)
from deepteam.attacks.attack_simulator.utils import (
    generate_schema,
    a_generate_schema,
)


class Multilingual(BaseAttack):
    def __init__(self, weight: int = 1, max_retries: int = 5):
        self.weight = weight
        self.max_retries = max_retries

    def enhance(self, attack: str, simulator_model: DeepEvalBaseLLM) -> str:
        self.simulator_model = simulator_model
        prompt = MultilingualTemplate.enhance(attack)

        # Progress bar for retries (total count is double the retries: 1 for generation, 1 for compliance check)
        with tqdm(
            total=self.max_retries * 3,
            desc="...... 🌍 Multilingual Enhancement",
            unit="step",
            leave=False,
        ) as pbar:
            for _ in range(self.max_retries):
                try:
                    # Generate the enhanced prompt
                    res: EnhancedAttack = self._generate_schema(
                        prompt, EnhancedAttack
                    )
                    enhanced_attack = res.input
                    pbar.update(1)  # Update the progress bar for generation

                    # Check for compliance using a compliance template
                    compliance_prompt = MultilingualTemplate.non_compliant(
                        res.model_dump()
                    )
                    compliance_res: ComplianceData = self._generate_schema(
                        compliance_prompt, ComplianceData
                    )
                    pbar.update(1)  # Update the progress bar for compliance

                    # Check if rewritten prompt is a translation
                    is_translation_prompt = MultilingualTemplate.is_translation(
                        res.model_dump()
                    )
                    is_translation_res: IsTranslation = self._generate_schema(
                        is_translation_prompt, IsTranslation
                    )
                    pbar.update(1)  # Update the progress bar for is a translation

                    if (
                        not compliance_res.non_compliant
                        and is_translation_res.is_translation
                    ):
                        # If it's compliant and is a translation, return the enhanced prompt
                        return enhanced_attack
                except Exception as e:
                    continue

        # If all retries fail, return the original prompt
        return attack

    async def a_enhance(
        self, attack: str, simulator_model: DeepEvalBaseLLM
    ) -> str:
        self.simulator_model = simulator_model
        prompt = MultilingualTemplate.enhance(attack)

        # Async progress bar for retries (double the count to cover both generation and compliance check)
        pbar = async_tqdm_bar(
            total=self.max_retries * 3,
            desc="...... 🌍 Multilingual Enhancement",
            unit="step",
            leave=False,
        )

        for _ in range(self.max_retries):
            try:
                # Generate the enhanced prompt asynchronously
                res: EnhancedAttack = await self._a_generate_schema(
                    prompt, EnhancedAttack
                )
                enhanced_attack = res.input
                pbar.update(1)  # Update the progress bar for generation

                # Check for compliance using a compliance template
                compliance_prompt = MultilingualTemplate.non_compliant(
                    res.model_dump()
                )
                compliance_res: ComplianceData = await self._a_generate_schema(
                    compliance_prompt, ComplianceData
                )
                pbar.update(1)  # Update the progress bar for compliance

                # Check if rewritten prompt is a translation
                is_translation_prompt = MultilingualTemplate.is_translation(
                    res.model_dump()
                )
                is_translation_res: IsTranslation = (
                    await self._a_generate_schema(
                        is_translation_prompt, IsTranslation
                    )
                )
                pbar.update(1)  # Update the progress bar for is a translation

                if (
                    not compliance_res.non_compliant
                    and is_translation_res.is_translation
                ):
                    # If it's compliant and is a translation, return the enhanced prompt
                    return enhanced_attack

            finally:
                # Close the progress bar after the loop
                pbar.close()

        # If all retries fail, return the original prompt
        return attack

    ##################################################
    ### Helper Methods ###############################
    ##################################################

    def _generate_schema(self, prompt: str, schema: BaseModel):
        return generate_schema(prompt, schema, self.simulator_model)

    async def _a_generate_schema(self, prompt: str, schema: BaseModel):
        return await a_generate_schema(prompt, schema, self.simulator_model)

    def get_name(self) -> str:
        return "Multilingual"
