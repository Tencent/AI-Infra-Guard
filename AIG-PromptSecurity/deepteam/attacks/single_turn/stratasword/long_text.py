from deepteam.attacks import BaseAttack
from deepteam.attacks.single_turn.stratasword.template import (
    StrataSwordTemplate,
)

from deepteam.utils import judge_language

class LongText(BaseAttack):

    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        if judge_language(attack) == "chinese":
            prompt = StrataSwordTemplate.generate_long_text_zh(attack)
        else:
            prompt = StrataSwordTemplate.generate_long_text_en(attack)
        
        return prompt