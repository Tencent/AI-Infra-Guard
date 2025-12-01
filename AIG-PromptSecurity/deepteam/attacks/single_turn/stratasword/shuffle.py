import re
import random
from deepteam.attacks import BaseAttack

from deepteam.utils import judge_language

class Shuffle(BaseAttack):

    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
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
        prompt = ''.join(parts)
        return prompt