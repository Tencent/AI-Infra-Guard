from deepteam.attacks import BaseAttack
from deepteam.attacks.single_turn.stratasword.template import (
    StrataSwordTemplate,
)

class AcrosticPoem(BaseAttack):

    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        line_specs = []
        for i, word in enumerate(attack, start=1):
            line_specs.append(f"第{i}个句的第1个字是{word}")
        
        prompt = StrataSwordTemplate.generate_acrostic_poem(line_specs)
        return prompt