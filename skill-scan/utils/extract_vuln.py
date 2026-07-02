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

"""
skill-scan 漏洞信息提取器

从 LLM 输出的 <vuln> XML 中提取漏洞结果，转为 results 列表。
对齐 mcp-scan 的 VulnerabilityExtractor 实现。
"""

import re
from typing import Optional


class VulnerabilityExtractor:
    """漏洞信息提取器"""

    def __init__(self):
        self.pattern = re.compile(
            r"<vuln>\s*(.*?)\s*</vuln>",
            re.DOTALL,  # 使 . 匹配包括换行符在内的所有字符
        )

    def extract_vulnerabilities(self, text: str) -> list[dict[str, str]]:
        """
        从文本中提取所有漏洞信息

        Args:
            text: 包含漏洞信息的文本

        Returns:
            漏洞信息字典列表
        """
        vulnerabilities = []

        # 查找所有vuln块
        vuln_blocks = self.pattern.findall(text)

        for i, block in enumerate(vuln_blocks, 1):
            try:
                vuln_info = self._parse_vuln_block(block, i)
                if vuln_info:
                    vulnerabilities.append(vuln_info)
            except Exception as e:
                print(f"解析第 {i} 个漏洞块时出错: {e}")
                continue

        return vulnerabilities

    def _parse_vuln_block(self, block: str, index: int) -> dict[str, str] | None:
        """解析单个vuln块"""

        # 提取各个字段
        title = self._extract_tag_content(block, "title")
        desc = self._extract_tag_content(block, "desc")
        risk_type = self._extract_tag_content(block, "risk_type")
        level = self._extract_tag_content(block, "level")
        suggestion = self._extract_tag_content(block, "suggestion")

        # 验证必要字段
        if not all([title, desc, risk_type]):
            print(f"第 {index} 个漏洞块缺少必要字段，跳过")
            return None

        return {
            "title": title.strip(),
            "description": desc.strip(),
            "risk_type": risk_type.strip(),
            "level": level.strip(),
            "suggestion": suggestion.strip(),
        }

    def _extract_tag_content(self, text: str, tag: str) -> str | None:
        """提取指定标签的内容"""
        pattern = re.compile(rf"<{tag}>\s*(.*?)\s*</{tag}>", re.DOTALL)
        match = pattern.search(text)
        return match.group(1) if match else None


def extract_result(text: str) -> Optional[dict]:
    """从 LLM 输出中提取首个漏洞结果（兜底函数）。

    解析 <vuln> XML 结构，返回首个漏洞的
    {title, description, risk_type, level, suggestion} 字典，
    解析失败返回 None。
    """
    extractor = VulnerabilityExtractor()
    results = extractor.extract_vulnerabilities(text)
    return results[0] if results else None
