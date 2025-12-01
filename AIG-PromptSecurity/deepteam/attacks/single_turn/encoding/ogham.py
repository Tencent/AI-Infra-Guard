from deepteam.attacks import BaseAttack

class Ogham(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight
        self.map = {
            'a': 'ᚐ', 'b': 'ᚁ', 'c': 'ᚉ', 'd': 'ᚇ', 'e': 'ᚓ', 'f': 'ᚃ', 'g': 'ᚌ', 'h': 'ᚆ', 'i': 'ᚔ',
            'j': 'ᚈ', 'k': 'ᚊ', 'l': 'ᚂ', 'm': 'ᚋ', 'n': 'ᚅ', 'o': 'ᚑ', 'p': 'ᚚ', 'q': 'ᚊ', 'r': 'ᚏ',
            's': 'ᚄ', 't': 'ᚈ', 'u': 'ᚒ', 'v': 'ᚃ', 'w': 'ᚃ', 'x': 'ᚊ', 'y': 'ᚔ', 'z': 'ᚎ',
            'A': 'ᚐ', 'B': 'ᚁ', 'C': 'ᚉ', 'D': 'ᚇ', 'E': 'ᚓ', 'F': 'ᚃ', 'G': 'ᚌ', 'H': 'ᚆ', 'I': 'ᚔ',
            'J': 'ᚈ', 'K': 'ᚊ', 'L': 'ᚂ', 'M': 'ᚋ', 'N': 'ᚅ', 'O': 'ᚑ', 'P': 'ᚚ', 'Q': 'ᚊ', 'R': 'ᚏ',
            'S': 'ᚄ', 'T': 'ᚈ', 'U': 'ᚒ', 'V': 'ᚃ', 'W': 'ᚃ', 'X': 'ᚊ', 'Y': 'ᚔ', 'Z': 'ᚎ'
        }

    def enhance(self, attack: str) -> str:
        return ''.join(self.map.get(c.lower(), c) for c in attack)
