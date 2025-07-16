import random
from deepteam.attacks import BaseAttack


class Zerowidth(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        """Enhance the attack using Zerowidth transformation."""
        max_inserts = len(attack) // 5
        min_inserts = min(max_inserts // 2, 2)

        # 定义支持的零宽字符
        zero_width_chars = [
            '\u200b',  # 零宽度空格
            '\u200c',  # 零宽度非连接符
            '\u200d',  # 零宽度连接符
            '\u200e',  # 从左至右书写标记
            '\u200f',  # 从右至左书写标记
        ]

        # 确定插入次数
        num_inserts = random.randint(min_inserts, max_inserts)

        # 生成所有可能的插入位置（不包括字符串末尾）
        possible_positions = list(range(1, len(attack)))

        # 如果可能的位置少于需要的插入次数，则调整插入次数
        if len(possible_positions) < num_inserts:
            num_inserts = len(possible_positions)
            if num_inserts <= 0:
                return attack

        # 随机选择插入位置
        selected_positions = random.sample(possible_positions, num_inserts)

        # 对选定的位置进行排序，以便按顺序插入
        selected_positions.sort()

        # 初始化结果字符串和上一个插入的位置
        result = []
        last_insert_pos = 0
        zero_width_char = None

        for i, pos in enumerate(selected_positions):
            # 添加从上一个插入位置到当前插入位置之间的字符
            result.append(attack[last_insert_pos:pos])
            # 随机选择一个零宽字符
            zero_width_char = random.choice(zero_width_chars)
            result.append(zero_width_char)
            last_insert_pos = pos

        # 添加剩余的字符
        result.append(attack[last_insert_pos:])

        # 确保没有连续的零宽字符
        # 由于我们按顺序插入，并且每次选择的位置不重叠，理论上不会有连续的零宽字符
        # 但为了确保，可以进一步检查并调整
        # 这里我们假设随机选择的位置不会导致连续插入，因为 selected_positions 是按顺序处理的

        return ''.join(result)

    def get_name(self) -> str:
        return "Zerowidth"
