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

import base64
import random
import string
from deepteam.attacks import BaseAttack

class BaseEncoding(BaseAttack):
    """多编码类型攻击类，支持Base32/45/58/62/64/64URL编码"""
    
    def __init__(self, encoding_type: str = "random", weight: int = 1):
        """
        初始化编码攻击类
        
        Args:
            encoding_type: 编码类型，可选值: 'base32', 'base45', 'base58', 'base62', 'base64', 'base64url', 'random'
            weight: 攻击权重
        """
        self.weight = weight
        self.encoding_type = encoding_type.lower()
        
        # 各编码类型的字母表
        self.base45_alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:'
        self.base58_alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
        self.base62_alphabet = string.digits + string.ascii_letters

    def _encode_base45(self, attack: str) -> str:
        """Base45编码"""
        bytes_data = attack.encode('utf-8')
        chars = []
        i = 0
        
        while i < len(bytes_data):
            if i + 1 < len(bytes_data):
                # 处理两个字节
                x = 256 * bytes_data[i] + bytes_data[i+1]
                e = x % 45
                d = (x // 45) % 45
                c = (x // (45 * 45)) % 45
                chars.extend([self.base45_alphabet[e], self.base45_alphabet[d], self.base45_alphabet[c]])
                i += 2
            else:
                # 处理单个字节
                x = bytes_data[i]
                e = x % 45
                d = (x // 45) % 45
                chars.extend([self.base45_alphabet[e], self.base45_alphabet[d]])
                i += 1
                
        return ''.join(chars)

    def _encode_base58(self, attack: str) -> str:
        """Base58编码（比特币/IPFS风格）"""
        bytes_str = attack.encode()
        n = int.from_bytes(bytes_str, 'big')
        enc = []
        base = len(self.base58_alphabet)
        
        while n > 0:
            n, rem = divmod(n, base)
            enc.append(self.base58_alphabet[rem])
        return ''.join(reversed(enc)) if enc else self.base58_alphabet[0]

    def _encode_base62(self, attack: str) -> str:
        """Base62编码（0-9A-Za-z）"""
        bytes_str = attack.encode()
        n = int.from_bytes(bytes_str, 'big')
        enc = []
        base = len(self.base62_alphabet)
        
        while n > 0:
            n, rem = divmod(n, base)
            enc.append(self.base62_alphabet[rem])
        return ''.join(reversed(enc)) if enc else self.base62_alphabet[0]

    def _get_random_encoding_type(self) -> str:
        """随机选择编码类型"""
        encoding_types = ['base32', 'base45', 'base58', 'base62', 'base64', 'base64url']
        return random.choice(encoding_types)

    def enhance(self, attack: str) -> str:
        """使用指定编码类型增强攻击字符串"""
        
        # 确定实际使用的编码类型
        actual_encoding_type = self.encoding_type
        if actual_encoding_type == 'random':
            actual_encoding_type = self._get_random_encoding_type()
        
        if actual_encoding_type == 'base32':
            return base64.b32encode(attack.encode()).decode()
        
        elif actual_encoding_type == 'base45':
            return self._encode_base45(attack)
        
        elif actual_encoding_type == 'base58':
            return self._encode_base58(attack)
        
        elif actual_encoding_type == 'base62':
            return self._encode_base62(attack)
        
        elif actual_encoding_type == 'base64':
            return base64.b64encode(attack.encode()).decode()
        
        elif actual_encoding_type == 'base64url':
            std_b64 = base64.b64encode(attack.encode()).decode()
            return std_b64.replace('+', '-').replace('/', '_').rstrip('=')
        
        else:
            raise ValueError(f"不支持的编码类型: {actual_encoding_type}。"
                           f"支持的编码类型: base32, base45, base58, base62, base64, base64url, random")