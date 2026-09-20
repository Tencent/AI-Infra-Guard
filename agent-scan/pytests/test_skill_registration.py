"""Guard the detection-skill registration contract.

Wiring in a detection skill takes two edits that nothing checks against each other:
append the name to ``_DETECTION_SKILLS`` in ``agent_scan.core.agent``, and add
``prompt/skills/<name>/SKILL.md``. A typo in the first only surfaces at run time,
against a live target, inside a worker thread. A directory added without the first
edit never runs at all and looks complete in review.
"""

from pathlib import Path

import pytest

import agent_scan
from agent_scan.core.agent import _DETECTION_SKILLS

SKILLS_DIR = Path(agent_scan.__file__).resolve().parent / "prompt" / "skills"
ASI_SKILL_MD = SKILLS_DIR / "owasp-asi" / "SKILL.md"

# Skill directories that are not Stage 2 detection workers, and so are correctly
# absent from _DETECTION_SKILLS.
NON_DETECTION_SKILLS = {"owasp-asi"}

# Directories that ship a SKILL.md but are wired to nothing as of this commit --
# no reference to any of them exists outside their own directory, so they never
# run. Pinned rather than fixed here: the regression worth catching is this set
# growing, and removing a dead skill is a separate decision from this test.
UNREGISTERED_SKILLS = {
    "direct-injection-detection",
    "file-path-traversal-detection",
    "hardcoded-secret-detection",
    "memory-poisoning-detection",
}

# Registered skills with no row in the owasp-asi Detection Source -> ASI table.
ASI_TABLE_GAPS = {"web-exfiltration-detection"}


def _skill_directories() -> set[str]:
    return {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()}


def test_skills_directory_exists():
    assert SKILLS_DIR.is_dir(), f"skills directory missing at {SKILLS_DIR}"


def test_registration_list_has_no_duplicates():
    duplicates = {s for s in _DETECTION_SKILLS if _DETECTION_SKILLS.count(s) > 1}
    assert not duplicates, f"_DETECTION_SKILLS lists these more than once: {sorted(duplicates)}"


@pytest.mark.parametrize("skill", _DETECTION_SKILLS)
def test_registered_skill_has_skill_md(skill):
    skill_md = SKILLS_DIR / skill / "SKILL.md"
    assert skill_md.is_file(), (
        f"_DETECTION_SKILLS registers {skill!r} but {skill_md} does not exist. "
        f"Existing directories: {sorted(_skill_directories())}"
    )


@pytest.mark.parametrize("skill", _DETECTION_SKILLS)
def test_registered_skill_frontmatter_name_matches_directory(skill):
    text = (SKILLS_DIR / skill / "SKILL.md").read_text(encoding="utf-8")
    declared = None
    for line in text.splitlines()[1:]:
        if line.strip() == "---":
            break
        if line.startswith("name:"):
            declared = line.split(":", 1)[1].strip()
            break
    assert declared == skill, (
        f"{skill}/SKILL.md declares name: {declared!r}, which does not match its directory"
    )


def test_no_new_unregistered_skill_directories():
    orphans = (
        _skill_directories() - set(_DETECTION_SKILLS) - NON_DETECTION_SKILLS - UNREGISTERED_SKILLS
    )
    assert not orphans, (
        f"these skill directories are not in _DETECTION_SKILLS and so never run: "
        f"{sorted(orphans)}. Register them, or add them to UNREGISTERED_SKILLS with "
        f"a note saying why they are dead."
    )


@pytest.mark.parametrize("skill", sorted(set(_DETECTION_SKILLS) - ASI_TABLE_GAPS))
def test_registered_skill_has_asi_table_row(skill):
    table = ASI_SKILL_MD.read_text(encoding="utf-8")
    assert f"`{skill}`" in table, (
        f"{skill} is registered but has no row in the owasp-asi Detection Source -> ASI table"
    )
