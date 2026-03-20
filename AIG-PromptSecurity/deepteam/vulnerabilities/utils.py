# Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Requirement: Any integration or derivative work must explicitly attribute
# Tencent Zhuque Lab (https://github.com/Tencent/AI-Infra-Guard) in its
# documentation or user interface, as detailed in the NOTICE file.

from enum import Enum
from typing import List, Type


def validate_vulnerability_types(
    vulnerability_name: str, types: List[str], allowed_type: Type[Enum]
) -> List[Enum]:
    if not isinstance(types, list):
        raise TypeError(
            f"The 'types' attribute for the {vulnerability_name} vulnerability must be a list of strings."
        )
    if not types:
        raise ValueError(
            f"The 'types' attribute for the {vulnerability_name} vulnerability attribute cannot be an empty list."
        )

    duplicate_types = [t for t in set(types) if types.count(t) > 1]
    if duplicate_types:
        quoted_duplicate_types = [f'"{t}"' for t in duplicate_types]
        raise ValueError(
            f"Duplicate types detected: {', '.join(quoted_duplicate_types)} for the {vulnerability_name} vulnerability."
        )

    valid_values = [type.value for type in allowed_type]
    invalid_types = [t for t in types if t not in valid_values]
    if invalid_types:
        if len(invalid_types) == 1:
            invalid_types_text = f'"{invalid_types[0]}"'
        elif len(invalid_types) == 2:
            invalid_types_text = (
                f'"{invalid_types[0]}" and "{invalid_types[1]}"'
            )
        else:
            quoted_invalid_types = [f'"{t}"' for t in invalid_types[:-1]]
            invalid_types_text = (
                f'{", ".join(quoted_invalid_types)}, and "{invalid_types[-1]}"'
            )

        if len(valid_values) == 1:
            valid_values_text = f'"{valid_values[0]}"'
        elif len(valid_values) == 2:
            valid_values_text = f'"{valid_values[0]}" and "{valid_values[1]}"'
        else:
            quoted_valid_values = [f'"{v}"' for v in valid_values[:-1]]
            valid_values_text = (
                f'{", ".join(quoted_valid_values)}, and "{valid_values[-1]}"'
            )

        verb = "does" if len(invalid_types) == 1 else "do"
        raise ValueError(
            f"The {invalid_types_text} {verb} not exist for the {vulnerability_name} vulnerability. "
            f"The available types are {valid_values_text}."
        )

    enum_types = [
        enum_type for enum_type in allowed_type if enum_type.value in types
    ]
    return enum_types
