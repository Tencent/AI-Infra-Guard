from pydantic import BaseModel
from tqdm import tqdm
from tqdm.asyncio import tqdm as async_tqdm_bar
import jieba

from deepeval.models import DeepEvalBaseLLM

from deepteam.attacks import BaseAttack
from deepteam.attacks.single_turn.stego.template import (
    StegoTemplate,
)
from deepteam.attacks.single_turn.stego.schema import (
    SteganographicParagraph
)
from deepteam.attacks.attack_simulator.utils import (
    generate_schema,
    a_generate_schema,
)
from deepteam.utils import judge_language

class Stego(BaseAttack):

    def __init__(self, weight: int = 1, max_retries: int = 3):
        self.weight = weight
        self.max_retries = max_retries

    def enhance(self, attack: str, simulator_model: DeepEvalBaseLLM) -> str:
        self.simulator_model = simulator_model

        if judge_language(attack) == "chinese":
            words = list(jieba.cut(attack))
            generate_steganographic_text = StegoTemplate.generate_steganographic_text_zh
            implement_jailbreak = StegoTemplate.implement_jailbreak_zh
        else:
            words = attack.split()
            generate_steganographic_text = StegoTemplate.generate_steganographic_text_en
            implement_jailbreak = StegoTemplate.implement_jailbreak_en
            
        words = [word for word in words if len(word.strip()) > 0 and word not in "，。？！"""]
        prompt = generate_steganographic_text(word_list=words)

        # Progress bar for retries (total count is double the retries: 1 for generation, 1 for compliance check)
        with tqdm(
            total=self.max_retries * 2,
            desc="...... 🔎 Generating steganographic text",
            unit="step",
            leave=False,
        ) as pbar:

            for _ in range(self.max_retries):
                try:
                    # Generate the enhanced attack
                    res: SteganographicParagraph = self._generate_schema(
                        prompt, SteganographicParagraph
                    )
                    stego_paragraph = res.paragraph
                    pbar.update(1)

                    enhanced_attack = implement_jailbreak(stego_paragraph=stego_paragraph)
                    pbar.update(1)  # Update the progress bar for compliance

                    return enhanced_attack
                except Exception as e:
                    continue

        # If all retries fail, return the original attack
        return attack

    async def a_enhance(
        self, attack: str, simulator_model: DeepEvalBaseLLM
    ) -> str:
        self.simulator_model = simulator_model
        if judge_language(attack) == "chinese":
            words = list(jieba.cut(attack))
            generate_steganographic_text = StegoTemplate.generate_steganographic_text_zh
            implement_jailbreak = StegoTemplate.implement_jailbreak_zh
        else:
            words = attack.split()
            generate_steganographic_text = StegoTemplate.generate_steganographic_text_en
            implement_jailbreak = StegoTemplate.implement_jailbreak_en
            
        words = [word for word in words if len(word.strip()) > 0 and word not in "，。？！"""]
        prompt = generate_steganographic_text(word_list=words)

        # Async progress bar for retries (double the count to cover both generation and compliance check)
        pbar = async_tqdm_bar(
            total=self.max_retries * 2,
            desc="...... 🔎 Generating steganographic text",
            unit="step",
            leave=False,
        )

        for _ in range(self.max_retries):
            try:
                # Generate the enhanced attack asynchronously
                res: SteganographicParagraph = await self._a_generate_schema(
                    prompt, SteganographicParagraph
                )
                stego_paragraph = res.paragraph
                pbar.update(1)  # Update the progress bar for generation

                enhanced_attack = implement_jailbreak(stego_paragraph=stego_paragraph)
                pbar.update(1)  # Update the progress bar for compliance
                pbar.close()
                return enhanced_attack
            except Exception as e:
                continue

        # Close the progress bar after the loop
        pbar.close()

        # If all retries fail, return the original attack
        return attack

    ##################################################
    ### Helper Methods ################################
    ##################################################

    def _generate_schema(self, prompt: str, schema: BaseModel):
        return generate_schema(prompt, schema, self.simulator_model)

    async def _a_generate_schema(self, prompt: str, schema: BaseModel):
        return await a_generate_schema(prompt, schema, self.simulator_model)

    def get_name(self) -> str:
        return "Stego"