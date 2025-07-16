from deepteam.attacks import BaseAttack


class Leetspeak(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        """Enhance the attack using Leetspeak transformation."""
        leet_map = {
            "a": "4",
            "e": "3",
            "i": "1",
            "o": "0",
            "s": "5",
            "t": "7",
            "l": "1",
            "A": "4",
            "E": "3",
            "I": "1",
            "O": "0",
            "S": "5",
            "T": "7",
            "L": "1",
        }
        return "".join(leet_map.get(char, char) for char in attack)

    def get_name(self) -> str:
        return "Leetspeak"
