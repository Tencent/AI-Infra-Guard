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

import json

from deepteam.attacks import BaseAttack
from deepteam.attacks.single_turn.code_chameleon.template import (
    BINARY_TREE_DECRYPTION,
    CODE_CHAMELEON_PROMPT,
)


class CodeChameleon(BaseAttack):
    """CodeChameleon single-turn prompt wrapper using binary tree encryption."""

    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        encrypted_query = self._encrypt_binary_tree(attack)
        return CODE_CHAMELEON_PROMPT.format(
            decryption_function=BINARY_TREE_DECRYPTION,
            query=encrypted_query,
        )

    def _encrypt_binary_tree(self, sentence: str) -> str:
        class TreeNode:
            def __init__(self, value):
                self.value = value
                self.left = None
                self.right = None

        def build_tree(words, start, end):
            if start > end:
                return None
            mid = (start + end) // 2
            node = TreeNode(words[mid])
            node.left = build_tree(words, start, mid - 1)
            node.right = build_tree(words, mid + 1, end)
            return node

        def tree_to_json(node):
            if node is None:
                return None
            return {
                "value": node.value,
                "left": tree_to_json(node.left),
                "right": tree_to_json(node.right),
            }

        words = sentence.split()
        root = build_tree(words, 0, len(words) - 1)
        tree_representation = tree_to_json(root)
        return json.dumps(tree_representation)

    def get_name(self) -> str:
        return "CodeChameleon"
