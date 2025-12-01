from deepteam.attacks import BaseAttack

class Vaporwave(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        return ' '.join(attack)