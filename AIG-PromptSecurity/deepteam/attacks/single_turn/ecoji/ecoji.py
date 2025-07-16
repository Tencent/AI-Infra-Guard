import io
import ecoji
from deepteam.attacks import BaseAttack


class Ecoji(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        """Enhance the attack using Ecoji transformation."""
        r = io.BytesIO(attack.encode())
        w = io.StringIO()

        ecoji.encode(r, w)

        return w.getvalue()

    def get_name(self) -> str:
        return "Ecoji"
