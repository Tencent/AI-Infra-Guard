import random
from deepteam.attacks import BaseAttack
from deepteam.attacks.single_turn.stratasword.template import (
    StrataSwordTemplate,
)

from deepteam.utils import judge_language

class Opposing(BaseAttack):

    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        if judge_language(attack) == "chinese":
            enhancement_methods = [
                StrataSwordTemplate.generate_opposing_1_zh, 
                StrataSwordTemplate.generate_opposing_2_zh,
                StrataSwordTemplate.generate_opposing_3_zh
            ]
        else:
            enhancement_methods = [
                StrataSwordTemplate.generate_opposing_1_en, 
                StrataSwordTemplate.generate_opposing_2_en,
                StrataSwordTemplate.generate_opposing_3_en
            ]
        
        method = random.choice(enhancement_methods)
        prompt = method(attack)
        return prompt