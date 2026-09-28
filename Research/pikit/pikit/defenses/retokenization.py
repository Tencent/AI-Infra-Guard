"""Retokenization defense (Jain et al., 2023).

Breaks up the untrusted data by inserting spaces inside words, which
disrupts the tokenization of injected trigger phrases (e.g. "ignore previous
instructions") so they are less likely to be recognized as a coherent
command, while a human/model can still read the meaning. A simple, model-free
baseline defense.
"""

from __future__ import annotations

import re
from typing import Optional

from ..base import Defense
from . import register
from ._util import split_instruction_data

_WORD = re.compile(r"\S+")


@register("retokenization")
class RetokenizationDefense(Defense):
    """Insert spaces inside longer words of the untrusted data.

    Parameters
    ----------
    min_len:
        Only split words at least this long (short words are left intact).
    """

    def __init__(self, min_len: int = 4) -> None:
        self.min_len = min_len

    def _break_word(self, word: str) -> str:
        if len(word) < self.min_len:
            return word
        mid = len(word) // 2
        return f"{word[:mid]} {word[mid:]}"

    def _retokenize(self, data: str) -> str:
        return _WORD.sub(lambda m: self._break_word(m.group(0)), data)

    def apply(self, prompt: str, instruction: Optional[str] = None) -> str:
        instr, data = split_instruction_data(prompt, instruction)
        broken = self._retokenize(data)
        if instr:
            return f"{instr}\n{broken}"
        return broken
