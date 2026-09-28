"""Shared helpers for defenses."""

from __future__ import annotations

from typing import Optional, Tuple


def split_instruction_data(
    prompt: str, instruction: Optional[str]
) -> Tuple[str, str]:
    """Separate the benign instruction from the untrusted data region.

    When the caller passes ``instruction`` and it prefixes ``prompt``, the
    remainder is treated as untrusted data. Otherwise the whole prompt is
    treated as data (instruction returned empty), which is the safe default
    for defenses that still work without knowing the original instruction.

    Returns
    -------
    (instruction, data)
    """
    if instruction:
        stripped = prompt
        if stripped.startswith(instruction):
            data = stripped[len(instruction):].lstrip()
            return instruction, data
        # Instruction given but not a literal prefix: keep them separate,
        # treating the entire prompt as the data region.
        return instruction, prompt
    return "", prompt
