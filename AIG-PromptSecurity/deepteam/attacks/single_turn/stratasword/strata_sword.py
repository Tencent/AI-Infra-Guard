import re
import json
import random
from pathlib import Path
from deepteam.attacks import BaseAttack
from deepteam.attacks.single_turn.stratasword.template import (
    StrataSwordTemplate,
)

from deepteam.utils import judge_language

class StrataSword(BaseAttack):

    def __init__(self, weight: int = 1):
        self.weight = weight

    @staticmethod
    def _ascii_drawing(attack: str) -> str:
        if judge_language(attack) == "chinese":
            words = list(attack)
            prompt = StrataSwordTemplate.generate_ascii_drawing_zh(words)
        else:
            words = attack.split()
            prompt = StrataSwordTemplate.generate_ascii_drawing_en(words)
        
        return prompt

    @staticmethod
    def _contradictory(attack: str) -> str:
        if judge_language(attack) == "chinese":
            prompt = StrataSwordTemplate.generate_contradictory_zh(attack)
        else:
            prompt = StrataSwordTemplate.generate_contradictory_en(attack)
        
        return prompt

    @staticmethod
    def _long_text(attack: str) -> str:
        if judge_language(attack) == "chinese":
            prompt = StrataSwordTemplate.generate_long_text_zh(attack)
        else:
            prompt = StrataSwordTemplate.generate_long_text_en(attack)
        
        return prompt

    @staticmethod
    def _opposing(attack: str) -> str:
        if judge_language(attack) == "chinese":
            enhancement_methods = [
                StrataSwordTemplate.generate_opposing_1_zh, 
                StrataSwordTemplate.generate_opposing_2_zh,
                StrataSwordTemplate.generate_opposing_3_zh
            ]
        else:
            enhancement_methods = [
                StrataSwordTemplate.generate_opposing_1_en, 
                StrataSwordTemplate.generate_opposing_2_en,
                StrataSwordTemplate.generate_opposing_3_en
            ]
        
        method = random.choice(enhancement_methods)
        prompt = method(attack)
        return prompt

    @staticmethod
    def _shuffle(attack: str) -> str:
        parts = re.split(r'([,.!?;:，。！？；：])', attack)
        
        # 遍历每个部分，打乱非标点的内容
        for i in range(len(parts)):
            part = parts[i]
            if not re.match(r'^[,.!?;:，。！？；：]$', part):  # 如果不是标点
                if judge_language(part) == "chinese":
                    words = list(part)
                    random.shuffle(words)
                    parts[i] = "".join(words)
                else:
                    words = part.split()
                    random.shuffle(words)
                    parts[i] = " ".join(words)
        
        # 重新组合结果
        shuffled_text = ''.join(parts)
        return shuffled_text

    @staticmethod
    def _template(attack: str) -> str:
        if judge_language(attack) == "chinese":
            enhancement_methods = [
                StrataSwordTemplate.generate_template_1_zh, 
                StrataSwordTemplate.generate_template_2_zh,
                StrataSwordTemplate.generate_template_3_zh
            ]
        else:
            enhancement_methods = [
                StrataSwordTemplate.generate_template_1_en, 
                StrataSwordTemplate.generate_template_2_en,
                StrataSwordTemplate.generate_template_3_en
            ]
        
        method = random.choice(enhancement_methods)
        prompt = method(attack)
        return prompt

    @staticmethod
    def _acrostic_poem(attack: str) -> str:
        line_specs = []
        for i, word in enumerate(attack, start=1):
            line_specs.append(f"第{i}个句的第1个字是{word}")
        
        prompt = StrataSwordTemplate.generate_acrostic_poem(line_specs)
        return prompt
    
    @staticmethod
    def _character_split(attack: str) -> str:
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

    @staticmethod
    def _lantern_riddle(attack: str) -> str:        
        prompt = StrataSwordTemplate.generate_lantern_riddle(attack)
        return prompt
    
    @staticmethod
    def _code_attack(attack: str) -> str:
        words = re.findall(r'\w+', attack)
        
        prompt = StrataSwordTemplate.generate_code_attack(words)
        return prompt

    @staticmethod
    def _drattack(attack: str) -> str:
        prompt = StrataSwordTemplate.generate_drattack(attack)
        return prompt
    
    @staticmethod
    def _script_template(attack: str) -> str:
        if judge_language(attack) == "chinese":
            words = list(attack)
            prompt = StrataSwordTemplate.generate_script_template_zh(words)
        else:
            words = attack.split()
            prompt = StrataSwordTemplate.generate_script_template_en(words)
        
        return prompt
    
    @staticmethod
    def _shuffle_template(attack: str) -> str:
        shuffled_text = StrataSword._shuffle(attack)

        if judge_language(attack) == "chinese":
            prompt = StrataSword._template(shuffled_text)
        else:
            prompt = StrataSword._template(shuffled_text)
        return prompt