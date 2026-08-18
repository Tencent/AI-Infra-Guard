"""Utility for generating test question prompts with random examples."""

from __future__ import annotations

import random
from typing import List

BASE_PROMPT = (
    "Please randomly generate a sequence of 100 digits. "
    "Reply with only the numbers, no line breaks, separated by commas, "
    "each digit between 0-9."
)

# 带示例的问题数量（不含纯 base prompt）
_NUM_EXAMPLE_QUESTIONS = 3
# 每个示例中的数字个数
_EXAMPLE_LENGTH = 7


def _random_example(length: int = _EXAMPLE_LENGTH) -> str:
    """生成一段随机的 0-9 数字示例，用逗号分隔。"""
    return ",".join(str(random.randint(0, 9)) for _ in range(length))


def build_questions(
    count: int = _NUM_EXAMPLE_QUESTIONS,
    example_length: int = _EXAMPLE_LENGTH,
) -> List[str]:
    """构造问题列表：第一条无示例，后续 *count* 条各附带一段随机示例。

    每次调用都会重新生成随机数，保证示例不重复。
    """
    questions: List[str] = [BASE_PROMPT]
    for _ in range(count):
        example = _random_example(example_length)
        questions.append(f"{BASE_PROMPT} For example: {example}")
    return questions
