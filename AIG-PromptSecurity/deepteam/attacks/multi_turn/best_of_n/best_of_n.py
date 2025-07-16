from pydantic import BaseModel
from tqdm import tqdm
from typing import Callable, Sequence

from deepeval.models import DeepEvalBaseLLM

from deepteam.attacks import BaseAttack
from deepteam.attacks.attack_simulator.utils import (
    generate_schema,
    a_generate_schema,
)
from deepteam.attacks.multi_turn.types import CallbackType
from deepteam.attacks.multi_turn.best_of_n.template import BoNTemplate
from deepteam.attacks.multi_turn.best_of_n.schema import NonRefusal
import random


class BoNUtil():

    @staticmethod
    def apply_word_scrambling(text: str, sigma: float = 0.4):
        words = text.split()
        scrambled_words = []
        for word in words:
            if len(word) > 3 and random.random() < sigma ** (1 / 2):
                chars = list(word)
                middle_chars = chars[1:-1]
                random.shuffle(middle_chars)
                scrambled_word = chars[0] + "".join(middle_chars) + chars[-1]
                scrambled_words.append(scrambled_word)
            else:
                scrambled_words.append(word)
        return " ".join(scrambled_words)

    @staticmethod
    def apply_random_captialization(text: str, sigma: float = 0.4):
        new_text = []
        for c in text:
            if c.isalpha() and random.random() < sigma ** (1 / 2):
                if "a" <= c <= "z":
                    new_text.append(chr(ord(c) - 32))  # Convert to uppercase
                elif "A" <= c <= "Z":
                    new_text.append(chr(ord(c) + 32))  # Convert to lowercase
            else:
                new_text.append(c)
        return "".join(new_text)

    @staticmethod
    def apply_character_noising(text: str, sigma: float = 0.4):
        new_text = []
        for c in text:
            if c.isprintable() and random.random() < sigma**3:
                perturbation = random.choice([-1, 1])
                new_char_code = ord(c) + perturbation
                # Ensure new character is printable ASCII
                if 32 <= new_char_code <= 126:
                    new_text.append(chr(new_char_code))
                else:
                    new_text.append(c)
            else:
                new_text.append(c)
        return "".join(new_text)


class BestofN(BaseAttack):
    def __init__(
        self,
        weight: int = 1,
        max_n: int = 10
    ):
        self.weight = weight
        self.max_n = max_n

    def enhance(
        self,
        attack: str,
        model_callback: CallbackType,
        simulator_model: DeepEvalBaseLLM,
    ) -> str:
        self.simulator_model = simulator_model

        for _ in tqdm(
            range(self.max_n),
            desc="...... ☠️ Best of N Enhancement: Rounds",
            leave=False,
        ):
            try:
                enhance_attack = attack
                aug_funcs: Sequence[Callable[..., str]] = BoNUtil.apply_character_noising, BoNUtil.apply_word_scrambling, BoNUtil.apply_random_captialization
                for f in aug_funcs:
                    enhance_attack = f(enhance_attack)
                
                target_response = model_callback(enhance_attack)
                non_refusal_prompt = BoNTemplate.harm_judge(attack, target_response)
                non_refusal_res: NonRefusal = self._generate_schema(non_refusal_prompt, NonRefusal)
                if non_refusal_res.answer == "Yes":
                    return enhance_attack
            except Exception as e:
                continue
        
        return enhance_attack

    async def a_enhance(
        self,
        attack: str,
        model_callback: CallbackType,
        simulator_model: DeepEvalBaseLLM,
    ) -> str:
        self.simulator_model = simulator_model

        for _ in tqdm(
            range(self.max_n),
            desc="...... ☠️ Best of N Enhancement: Rounds",
            leave=False,
        ):
            try:
                enhance_attack = attack
                aug_funcs: Sequence[Callable[..., str]] = BoNUtil.apply_character_noising, BoNUtil.apply_word_scrambling, BoNUtil.apply_random_captialization
                for f in aug_funcs:
                    enhance_attack = f(enhance_attack)
                
                target_response = await model_callback(enhance_attack)
                non_refusal_prompt = BoNTemplate.harm_judge(attack, target_response)
                non_refusal_res: NonRefusal = await self._a_generate_schema(non_refusal_prompt, NonRefusal)
                if non_refusal_res.answer == "Yes":
                    return enhance_attack
            except Exception as e:
                continue
        
        return enhance_attack
    
    def _generate_schema(self, prompt: str, schema: BaseModel):
        return generate_schema(prompt, schema, self.simulator_model)

    async def _a_generate_schema(self, prompt: str, schema: BaseModel):
        return await a_generate_schema(prompt, schema, self.simulator_model)

    def get_name(self) -> str:
        return "Best of N"
