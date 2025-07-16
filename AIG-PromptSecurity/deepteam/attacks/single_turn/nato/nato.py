from deepteam.attacks import BaseAttack


class Nato(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        """Enhance the attack using Nato transformation."""
        nato_map = {
            "A": "Alfa",
            "B": "Bravo",
            "C": "Charlie",
            "D": "Delta",
            "E": "Echo",
            "F": "Foxtrot",
            "G": "Golf",
            "H": "Hotel",
            "I": "India",
            "J": "Juliett",
            "K": "Kilo",
            "L": "Lima",
            "M": "Mike",
            "N": "November",
            "O": "Oscar",
            "P": "Papa",
            "Q": "Quebec",
            "R": "Romeo",
            "S": "Sierra",
            "T": "Tango",
            "U": "Uniform",
            "V": "Victor",
            "W": "Whiskey",
            "X": "Xray",
            "Y": "Yankee",
            "Z": "Zulu",
        }
        return " ".join(nato_map.get(char, char) for char in attack.upper())

    def get_name(self) -> str:
        return "Nato"
