from deepteam.attacks import BaseAttack
from deepteam.attacks.single_turn.stratasword.template import (
    StrataSwordTemplate,
)

class DRAttack(BaseAttack):

    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        prompt = StrataSwordTemplate.generate_drattack(attack)
        return prompt