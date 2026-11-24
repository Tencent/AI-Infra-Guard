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

"""cli.parsers 的单元测试

运行: cd AIG-PromptSecurity && uv run pytest tests/test_parsers.py -v
"""

from cli.parsers import parse_vulnerability


class _PluginVulnerability:
    def __init__(self, level=1):
        self.level = level


class _FakePluginManager:
    def create_vulnerability_instance(self, class_name, **kwargs):
        if class_name == "MyPluginVuln":
            return _PluginVulnerability(**kwargs)
        return None


def test_plugin_scenario_without_params_returns_list_and_tag():
    vulnerabilities, tag = parse_vulnerability("MyPluginVuln", _FakePluginManager())
    assert [v.level for v in vulnerabilities] == [1]
    assert tag is None


def test_plugin_scenario_with_params_returns_list_and_tag():
    """带参数的插件场景以前只返回列表，red_team_runner 解包成两个值时报错。"""
    vulnerabilities, tag = parse_vulnerability("MyPluginVuln:level=3", _FakePluginManager())
    assert [v.level for v in vulnerabilities] == [3]
    assert tag is None
