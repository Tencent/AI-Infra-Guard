import random

from deepteam.attacks import BaseAttack
from deepteam.attacks.single_turn.prompt_injection.template import (
    PromptInjectionTemplate,
)


class PromptInjection(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        return random.choice(
            [
                PromptInjectionTemplate.enhance_1(attack),
                PromptInjectionTemplate.enhance_2(attack),
            ]
        )

    def get_name(self) -> str:
        return "Prompt Injection"
