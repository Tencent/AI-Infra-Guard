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
Core data models for security report generation.

This module defines the data structures used for generating frontend-compatible
security reports (schema: agent-security-report@1).
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class Severity(str, Enum):
    """Severity levels for security findings."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ConversationTurn(BaseModel):
    """Single turn in a conversation for vulnerability evidence."""

    prompt: Optional[str] = None
    response: Optional[str] = None


class VulnerabilityFinding(BaseModel):
    """Single vulnerability finding for frontend display."""

    id: str
    type: str  # e.g., "data_leakage", "prompt_injection"
    title: str
    description: str  # Markdown supported
    level: str  # "High", "Medium", "Low"
    owasp: List[str] = Field(default_factory=list)  # e.g., ["ASI06"]
    suggestion: str  # Markdown supported
    conversation: List[ConversationTurn] = Field(default_factory=list)


class OWASPASISummary(BaseModel):
    """OWASP ASI category summary for frontend display."""

    id: str  # e.g., "ASI06"
    name: str  # e.g., "Memory & Context Poisoning"
    total: int
    high_or_above: int
    max_level: str  # "HIGH", "MEDIUM", "LOW"
    findings: List[str] = Field(default_factory=list)


class AgentSecurityReport(BaseModel):
    """
    Final security report format for frontend integration.

    Schema version: agent-security-report@1
    """

    schema_version: str = "agent-security-report@1"
    agent_name: str = ""
    agent_type: str = ""  # e.g., "dify", "langchain", "custom"
    model_name: str = ""  # e.g., "openai/gpt-4"
    start_time: int  # Unix timestamp
    end_time: int  # Unix timestamp
    plugins: List[str] = Field(default_factory=list)
    score: int = 100  # Security score (0-100)
    risk_type: str = "safe"  # "high", "medium", "low", "safe"
    total_tests: int = 0
    vulnerable_tests: int = 0
    results: List[VulnerabilityFinding] = Field(default_factory=list)
    owasp_agentic_2026_top10: List[OWASPASISummary] = Field(default_factory=list)
    report_description: str = ""
