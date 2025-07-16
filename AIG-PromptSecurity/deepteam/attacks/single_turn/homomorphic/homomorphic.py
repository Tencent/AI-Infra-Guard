import ahocorasick
import random
import json
from pathlib import Path
from deepteam.attacks import BaseAttack


class Homomorphic(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        """Enhance the attack using Homomorphic transformation."""
        # Load homomorphic mapping
        json_path = Path(__file__).resolve().parent / "homomorphic.json"
        with open(json_path, "r", encoding="utf-8") as f:
            homomorphic_map = json.load(f)
        
        # Build AC automaton
        automaton = ahocorasick.Automaton()
        for word, homomorphs in homomorphic_map.items():
            # Store (original word, homomorph list)
            automaton.add_word(word, (word, homomorphs))
        automaton.make_automaton()
        
        # Perform replacement
        last_end = 0
        result = []
        for end_index, (word, homomorphs) in automaton.iter(attack):
            start_index = end_index - len(word) + 1
            # Add unmatched part
            result.append(attack[last_end:start_index])
            # Add random homomorphic character
            result.append(random.choice(homomorphs))
            last_end = end_index + 1
        
        result.append(attack[last_end:])
        return "".join(result)

    def get_name(self) -> str:
        return "Homomorphic"
