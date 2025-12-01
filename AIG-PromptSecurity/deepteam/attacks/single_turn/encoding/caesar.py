from deepteam.attacks import BaseAttack

class CaesarCipher(BaseAttack):
    def __init__(self, weight: int = 1, shift: int = 3):
        self.weight = weight
        self.shift = shift  # Traditional Caesar shift is 3

    def enhance(self, attack: str) -> str:
        result = []
        for c in attack:
            code = ord(c)
            # Only shift letters, leave other characters unchanged
            if 65 <= code <= 90:  # Uppercase letters
                shifted = ((code - 65 + self.shift) % 26) + 65
                result.append(chr(shifted))
            elif 97 <= code <= 122:  # Lowercase letters
                shifted = ((code - 97 + self.shift) % 26) + 97
                result.append(chr(shifted))
            else:
                result.append(c)
        return ''.join(result)