"""Revisores, skill de cumplimiento y comando del pull request."""

from pathlib import Path

import pytest
from frontmatter import as_list, parse_frontmatter

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / ".claude" / "agents"
SKILLS = ROOT / ".claude" / "skills"
COMMAND = ROOT / ".claude" / "commands" / "abrir-pr.md"
READ_ONLY = ["Read", "Grep", "Glob"]
WRITERS = {"Write", "Edit", "Bash", "NotebookEdit", "MultiEdit"}


def read(path):
    return path.read_text(encoding="utf-8")


def body(path):
    return read(path).split("---", 2)[-1]


# --------------------------------------------------------------------------- subagentes


@pytest.mark.parametrize("name", ["code-reviewer", "compliance-reviewer"])
def test_each_reviewer_is_read_only_and_well_described(name):
    path = AGENTS / f"{name}.md"
    assert path.is_file(), f"falta {path.name}"
    meta = parse_frontmatter(read(path))
    assert meta["name"] == name
    assert len(meta["description"]) > 40
    assert as_list(meta["tools"]) == READ_ONLY
    assert not WRITERS & set(as_list(meta["tools"]))


def test_the_reviewers_are_distinct_missions():
    code = body(AGENTS / "code-reviewer.md")
    compliance = body(AGENTS / "compliance-reviewer.md")
    assert code != compliance
    assert "cumplimiento" in compliance.lower()


def test_the_compliance_reviewer_covers_the_five_business_rules():
    text = body(AGENTS / "compliance-reviewer.md")
    for number in range(1, 6):
        assert f"Regla {number}" in text, f"falta la regla {number}"
    assert "cumplida" in text and "parcial" in text and "ausente" in text


def test_a_rule_that_depends_only_on_a_prompt_is_a_grave_failure():
    text = body(AGENTS / "compliance-reviewer.md").lower()
    assert "falta grave" in text
    assert "solo" in text and "prompt" in text and "hook" in text


def test_the_compliance_reviewer_ends_with_a_verdict_and_reports_evidence():
    text = body(AGENTS / "compliance-reviewer.md")
    assert "VEREDICTO" in text
    assert "evidencia" in text.lower()


# --------------------------------------------------------------------------- skill


def test_the_compliance_skill_runs_isolated_with_restricted_tools_and_an_argument_hint():
    path = SKILLS / "revisar-cumplimiento" / "SKILL.md"
    assert path.is_file()
    meta = parse_frontmatter(read(path))
    assert meta["name"] == "revisar-cumplimiento"
    assert meta["context"] == "fork"
    assert len(meta["description"]) > 40
    assert meta["argument-hint"].strip()
    tools = as_list(meta["allowed-tools"])
    assert tools and set(tools) <= set(READ_ONLY)
    assert "$ARGUMENTS" in body(path)
    assert "compliance-reviewer" in read(path)


# --------------------------------------------------------------------------- /abrir-pr


def test_open_pr_launches_both_reviews():
    text = read(COMMAND)
    assert "code-reviewer" in text
    assert "compliance-reviewer" in text


def test_open_pr_does_not_open_the_pr_on_a_grave_failure():
    text = read(COMMAND).lower()
    assert "incumplimiento grave" in text
    assert "no abras el pr" in text or "no abrir el pr" in text


def test_open_pr_puts_both_verdicts_in_the_description_and_still_closes_the_issue():
    text = read(COMMAND)
    assert "veredicto" in text.lower()
    assert "descripción del PR" in text
    assert "Closes #$ARGUMENTS" in text


def test_open_pr_keeps_its_argument_hint_and_a_description():
    meta = parse_frontmatter(read(COMMAND))
    assert meta["argument-hint"].strip()
    assert "cumplimiento" in meta["description"].lower()
