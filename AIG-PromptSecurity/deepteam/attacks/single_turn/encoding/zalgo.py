from zalgolib.zalgolib import enzalgofy
from deepteam.attacks import BaseAttack

class Zalgo(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        """Enhance the attack using Zalgo transformation."""
        return enzalgofy(text=attack, intensity=5)

    def get_name(self) -> str:
        return "Zalgo"
