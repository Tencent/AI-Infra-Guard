import json
from pathlib import Path
from deepteam.attacks import BaseAttack
from deepteam.attacks.single_turn.stratasword.template import (
    StrataSwordTemplate,
)

class CharacterSplit(BaseAttack):

    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        json_path = Path(__file__).resolve().parent / "chaizi.json"
        with open(json_path, "r", encoding="utf-8") as f:
            rad_map = json.load(f)
        chunks = []
        for char in attack:
            rad = rad_map.get(char, None)
            chunk = char
            if rad:
                chunk += f"({rad[0]})"
            chunks.append(chunk)
        
        prompt = StrataSwordTemplate.generate_character_split(chunks)
        return prompt