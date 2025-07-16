import json
from pathlib import Path
from deepteam.attacks import BaseAttack


class Emoji(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        """Enhance the attack using Emoji transformation."""
        # 加载Emoji映射
        json_path = Path(__file__).resolve().parent / "emoji.json"
        with open(json_path, "r", encoding="utf-8") as f:
            emoji_map = json.load(f)
        
        # 按旧词长度降序排序，避免短词误匹配
        sorted_words = sorted(emoji_map.keys(), key=lambda x: -len(x))
        
        # 记录所有需要替换的位置和对应的新词
        replacements = []
        
        for word in sorted_words:
            if word in attack:
                # 找到所有匹配的位置
                start_index = 0
                while True:
                    index = attack.find(word, start_index)
                    if index == -1:
                        break
                    # 记录替换信息：(start_index, end_index, new_word)
                    replacements.append((index, index + len(word), emoji_map[word][0]))
                    start_index = index + len(word)  # 移动到匹配词之后，避免重叠匹配
        
        # 如果没有需要替换的内容，直接返回原文本
        if not replacements:
            return attack
        
        # 按照起始位置排序替换信息
        replacements.sort(key=lambda x: x[0])
        
        # 构建结果字符串
        result = []
        last_end = 0
        
        for start, end, new_word in replacements:
            # 添加未匹配的部分
            result.append(attack[last_end:start])
            # 添加新词
            result.append(new_word)
            last_end = end
        
        result.append(attack[last_end:])
        return "".join(result)

    def get_name(self) -> str:
        return "Emoji"
