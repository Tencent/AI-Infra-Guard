import re
from deepteam.attacks import BaseAttack
from deepteam.attacks.single_turn.stratasword.template import (
    StrataSwordTemplate,
)

class CodeAttack(BaseAttack):

    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        words = re.findall(r'\w+', attack)
        
        prompt = StrataSwordTemplate.generate_code_attack(words)
        return prompt