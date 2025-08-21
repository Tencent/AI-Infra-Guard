from deepteam.attacks import BaseAttack


class Raw(BaseAttack):

    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        """Enhance the attack using noting."""
        return attack

    def get_name(self) -> str:
        return "RedTeam"
