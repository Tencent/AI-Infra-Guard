"""Regression tests for issue #723 — non-standard skill packages.

Two zips each holding a single .docx produced inconsistent outcomes: one
scan finished with status=done / score=100, the other died with status=error,
because the result depended on whether the LLM happened to call the finish
tool for content it could not audit anyway. A static gate in Agent.scan()
must return a deterministic result for packages with no SKILL.md and no
auditable text/code files.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import skill_scan.tools  # noqa: F401  # register local tools
from skill_scan.agent.agent import Agent, _is_non_skill_package
from skill_scan.utils import config
from skill_scan.utils.llm import LLM


def _make_llm() -> LLM:
    return LLM(
        model=config.DEFAULT_MODEL,
        api_key="test-key",
        base_url=config.DEFAULT_BASE_URL,
        context_window=config.DEFAULT_MODEL_CONTEXT_WINDOW,
    )


def _make_repo(tmp_path: Path, files: dict[str, bytes]) -> str:
    repo = tmp_path / "repo"
    repo.mkdir()
    for rel, payload in files.items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        target.write_bytes(payload)
    return str(repo)


def test_docx_only_package_is_non_skill(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, {"report.docx": b"PK\x03\x04-fake-docx"})

    assert _is_non_skill_package(repo) is True


def test_skill_md_makes_package_standard(tmp_path: Path) -> None:
    repo = _make_repo(
        tmp_path,
        {"SKILL.md": b"---\nname: demo\n---\n", "report.docx": b"PK\x03\x04"},
    )

    assert _is_non_skill_package(repo) is False


def test_code_file_makes_package_standard(tmp_path: Path) -> None:
    repo = _make_repo(
        tmp_path,
        {"scripts/run.py": "print('hi')\n", "sheet.xlsx": b"PK\x05\x06"},
    )

    assert _is_non_skill_package(repo) is False


def test_extensionless_file_counts_as_auditable(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, {"LICENSE": "Apache-2.0\n"})

    assert _is_non_skill_package(repo) is False


def test_bytecode_only_package_stays_auditable(tmp_path: Path) -> None:
    # Issues #630/#631: compiled bytecode must stay on the audit surface;
    # a .pyc-only package must not short-circuit into the not-a-skill gate.
    repo = _make_repo(tmp_path, {"__pycache__/evil.cpython-312.pyc": b"\x00raw-bytecode"})

    assert _is_non_skill_package(repo) is False


def test_metadata_only_package_is_empty_not_non_skill(tmp_path: Path) -> None:
    # Pure OS-metadata dirs are handled by the earlier empty-project path.
    repo = _make_repo(tmp_path, {".DS_Store": b""})

    assert _is_non_skill_package(repo) is True


def test_scan_returns_deterministic_result_for_docx_only(tmp_path: Path) -> None:
    """The gate must fire before any LLM call, for both zh and en languages."""
    from types import SimpleNamespace

    agent = Agent(llm=_make_llm(), language="zh")
    # A dispatched LLM call would fail the test: the gate must not need the LLM.
    agent.llm = SimpleNamespace(model_name="stub")  # type: ignore[assignment]

    repo = _make_repo(tmp_path, {"only.docx": b"PK\x03\x04"})

    import asyncio

    result = asyncio.run(agent.scan(repo, "", "zh"))

    assert result["score"] == 100
    assert result["results"] == []
    assert "非标准" in result["readme"]

    result_en = asyncio.run(agent.scan(repo, "", "en"))
    assert "not a standard Agent Skill package" in result_en["readme"]
    assert agent.last_verdict == "normal"
