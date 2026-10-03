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

import pytest

from deepteam.attacks.single_turn import RailFence


@pytest.mark.parametrize(
    "rails,plaintext,expected",
    [
        (2, "HELLOWORLD", "HLOOLELWRD"),
        (3, "HELLOWORLD", "HOLELWRDLO"),
        (5, "HELLOWORLD", "HLERDLOLWO"),
    ],
)
def test_rail_fence_keeps_existing_output(rails, plaintext, expected):
    """rails >= 2 的既有编码结果必须保持不变。"""
    assert RailFence(rails=rails).enhance(plaintext) == expected


def test_rail_fence_single_rail_is_identity():
    """rails=1 时栅栏无法折返，以前抛 IndexError，现在退化为恒等变换。

    rails 是公开的构造参数（`cli_run.py --scan-tools techniques` 会把它作为
    可选参数列出），并由 cli/parsers.py::parse_attack 从
    `--techniques "RailFence:rails=1"` 直接透传进来。
    """
    assert RailFence(rails=1).enhance("hello world") == "hello world"
    assert RailFence(rails=1).enhance("") == ""


@pytest.mark.parametrize("rails", [0, -3])
def test_rail_fence_rejects_non_positive_rails(rails):
    """rails <= 0 没有合法的栅栏，应当给出明确的 ValueError 而不是 IndexError。"""
    with pytest.raises(ValueError, match="rails"):
        RailFence(rails=rails).enhance("hello world")
