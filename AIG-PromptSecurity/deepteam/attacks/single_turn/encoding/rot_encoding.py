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

from deepteam.attacks import BaseAttack
import random

class ROTEncoding(BaseAttack):
    """ROT系列编码攻击类，支持ROT5/13/18/47编码"""
    
    def __init__(self, rot_type: str = "random", weight: int = 1):
        """
        初始化ROT编码攻击类
        
        Args:
            rot_type: ROT类型，可选值: 'rot5', 'rot13', 'rot18', 'rot47', 'random'
            weight: 攻击权重
        """
        self.weight = weight
        self.rot_type = rot_type.lower()
    
    def _rot5(self, text: str) -> str:
        """应用ROT5密码到数字(0-9)"""
        result = []
        for c in text:
            if '0' <= c <= '9':
                # 数字旋转5个位置
                rotated = str((int(c) + 5) % 10)
                result.append(rotated)
            else:
                result.append(c)
        return ''.join(result)
    
    def _rot13(self, text: str) -> str:
        """应用ROT13编码"""
        return text.translate(
            str.maketrans(
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
                "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm",
            )
        )
    
    def _rot18(self, text: str) -> str:
        """应用ROT18编码（ROT13 + ROT5）"""
        # 先应用ROT13，再应用ROT5
        return self._rot5(self._rot13(text))
    
    def _rot47(self, text: str) -> str:
        """应用ROT47编码"""
        result = []
        for c in text:
            code = ord(c)
            # ROT47操作于ASCII 33到126的字符集
            if 33 <= code <= 126:
                rotated = 33 + ((code - 33 + 47) % 94)
                result.append(chr(rotated))
            else:
                result.append(c)
        return ''.join(result)
    
    def _get_random_rot_type(self) -> str:
        """随机选择ROT类型"""
        rot_types = ['rot5', 'rot13', 'rot18', 'rot47']
        return random.choice(rot_types)
    
    def enhance(self, attack: str) -> str:
        """使用指定ROT类型增强攻击字符串"""
        
        # 确定实际使用的ROT类型
        actual_rot_type = self.rot_type
        if actual_rot_type == 'random':
            actual_rot_type = self._get_random_rot_type()
        
        # 执行对应的ROT编码
        if actual_rot_type == 'rot5':
            return self._rot5(attack)
        
        elif actual_rot_type == 'rot13':
            return self._rot13(attack)
        
        elif actual_rot_type == 'rot18':
            return self._rot18(attack)
        
        elif actual_rot_type == 'rot47':
            return self._rot47(attack)
        
        else:
            raise ValueError(f"不支持的ROT类型: {actual_rot_type}。"
                           f"支持的ROT类型: rot5, rot13, rot18, rot47, random")
