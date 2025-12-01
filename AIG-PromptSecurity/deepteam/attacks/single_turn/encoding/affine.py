from deepteam.attacks import BaseAttack

class AffineCipher(BaseAttack):
    def __init__(self, weight: int = 1, a: int = 5, b: int = 8, m: int = 26):
        self.weight = weight
        self.a = a
        self.b = b
        self.m = m

    def enhance(self, attack: str) -> str:
        """Encrypt text using Affine Cipher"""
        result = []
        for c in attack:
            code = ord(c)
            if 65 <= code <= 90:  # Uppercase letters
                encrypted = (self.a * (code - 65) + self.b) % self.m
                result.append(chr(65 + encrypted))
            elif 97 <= code <= 122:  # Lowercase letters
                encrypted = (self.a * (code - 97) + self.b) % self.m
                result.append(chr(97 + encrypted))
            else:
                result.append(c)
        return ''.join(result)
