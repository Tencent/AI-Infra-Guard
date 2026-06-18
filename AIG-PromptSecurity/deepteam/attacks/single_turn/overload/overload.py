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

import random
import string
from typing import Dict

from deepteam.attacks import BaseAttack
from deepteam.attacks.single_turn.overload.template import OVERLOAD_INSTRUCTION


class Overload(BaseAttack):
    """Add decoding workload before the original instruction."""

    def __init__(
        self,
        weight: int = 1,
        dict_type: str = "all",
        random_dict: int = 30,
        lenmin: int = 1,
        lenmax: int = 5,
        value_len: int = 1,
        strlen: int = 1,
        mask_loc: str = "before",
    ):
        self.weight = weight
        self.dict_type = dict_type
        self.random_dict = random_dict
        self.lenmin = lenmin
        self.lenmax = lenmax
        self.value_len = value_len
        self.strlen = strlen
        self.mask_loc = mask_loc

    def enhance(self, attack: str) -> str:
        mapping = self._generate_mapping()
        keys = list(mapping.keys())
        values = list(mapping.values())

        context_key = " ".join(keys[: self.strlen])
        context_value = " ".join(values[: self.strlen])

        encoded_pairs = [
            random.choice(list(mapping.items())) for _ in range(self.strlen)
        ]
        encoded_string = " ".join([pair[0] for pair in encoded_pairs])

        if self.mask_loc == "before":
            question = "[mask] " + attack
        elif self.mask_loc == "after":
            question = attack + ". [mask]"
        else:
            question = attack

        return OVERLOAD_INSTRUCTION.format(
            char_map=str(mapping),
            context_key=context_key,
            context_value=context_value,
            encoded_string=encoded_string,
            question=question,
        )

    def _generate_mapping(self) -> Dict[str, str]:
        charset = self._build_charset()

        def random_token() -> str:
            length = random.randint(self.lenmin, self.lenmax)
            return "".join(random.choice(charset) for _ in range(length))

        if self.random_dict > 0:
            key_list = [random_token() for _ in range(self.random_dict * 2)]
            value_list = [random_token() for _ in range(self.random_dict * 2)]
        else:
            key_list = list(charset)
            value_list = list(charset)

        random.shuffle(key_list)
        random.shuffle(value_list)

        if self.value_len > 0:
            mapping = {
                key_list[i]: value_list[i][: self.value_len]
                for i in range(len(key_list))
            }
        else:
            mapping = {
                key_list[i]: value_list[i] for i in range(len(key_list))
            }

        if self.random_dict > 0:
            trimmed_keys = list(mapping.keys())[: self.random_dict]
            mapping = {key: mapping[key] for key in trimmed_keys}

        return mapping

    def _build_charset(self) -> str:
        dict_type = (self.dict_type or "").lower()
        charset = ""
        if "all" in dict_type:
            return string.printable[:-6]
        if "uppercase" in dict_type:
            charset += string.ascii_uppercase
        if "lowercase" in dict_type:
            charset += string.ascii_lowercase
        if "digits" in dict_type:
            charset += string.digits
        if "punctuation" in dict_type:
            charset += string.punctuation
        if not charset:
            charset = string.printable[:-6]
        return charset

    def get_name(self) -> str:
        return "Overload"
