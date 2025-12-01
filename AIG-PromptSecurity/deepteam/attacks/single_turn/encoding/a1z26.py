from deepteam.attacks import BaseAttack
import re

class A1Z26(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        result = []
        for c in attack:
            if c.isalpha():
                # Convert character to its position in alphabet (A=1, B=2, etc.)
                num = ord(c.upper()) - 64
                result.append(f"{num}-")
            else:
                result.append(c)
        
        # Join and clean up hyphens
        encoded = ''.join(result)
        encoded = re.sub(r'-+(?!\d)', '-', encoded)  # Remove multiple hyphens not followed by digits
        encoded = re.sub(r'-+$', '', encoded)        # Remove trailing hyphens
        return encoded
