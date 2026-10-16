"""Convenciones del equipo: memoria de proyecto, reglas por ruta y preferencias personales."""

import subprocess
from pathlib import Path

import pytest
from frontmatter import parse_frontmatter

ROOT = Path(__file__).resolve().parents[2]
RULES = sorted((ROOT / ".claude" / "rules").glob("*.md"))
PERSONAL = ["CLAUDE.local.md", ".claude/settings.local.json"]
TEAM_FILES = [
    "CLAUDE.md",
    "docs/convenciones.md",
    "mcp_server/CLAUDE.md",
    "due_diligence/CLAUDE.md",
    ".claude/settings.json",
    ".claude/rules/tests.md",
    ".claude/rules/datos-ficticios.md",
    ".claude/rules/specs.md",
]


def git(*args):
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
    )


# --------------------------------------------------------------------------- memoria de proyecto


def test_the_root_memory_is_short_and_imports_the_conventions():
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert len(text.splitlines()) < 200
    assert "@docs/convenciones.md" in text
    assert (ROOT / "docs" / "convenciones.md").is_file()


@pytest.mark.parametrize("path", ["mcp_server/CLAUDE.md", "due_diligence/CLAUDE.md"])
def test_each_code_area_has_its_own_memory_file(path):
    assert (ROOT / path).is_file()
    assert (ROOT / path).read_text(encoding="utf-8").strip()


def test_the_root_memory_points_to_the_constitution_and_the_ticket_order():
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert ".specify/memory/constitution.md" in text
    assert "#9" in text and "#10" in text


# --------------------------------------------------------------------------- reglas por ruta


def paths_of(rule):
    value = parse_frontmatter(rule.read_text(encoding="utf-8")).get("paths")
    return value if isinstance(value, list) else []


def test_at_least_two_rules_are_scoped_by_path_with_globs():
    scoped = [rule for rule in RULES if paths_of(rule)]
    assert len(scoped) >= 2
    for rule in scoped:
        assert all("*" in glob or "/" in glob for glob in paths_of(rule)), rule.name


def test_the_tests_rule_covers_every_test_location():
    rule = ROOT / ".claude" / "rules" / "tests.md"
    assert "**/tests/**/*.py" in paths_of(rule)
    assert "**/test_*.py" in paths_of(rule)


def test_every_rule_has_content_beyond_its_frontmatter():
    for rule in RULES:
        body = rule.read_text(encoding="utf-8").split("---", 2)[-1].strip()
        assert len(body) > 80, rule.name


# ----------------------------------------------------------------- preferencias personales


@pytest.mark.parametrize("path", PERSONAL)
def test_personal_files_are_ignored_by_git_and_never_tracked(path):
    assert git("check-ignore", "-q", path).returncode == 0, f"{path} no está en .gitignore"
    assert path not in git("ls-files").stdout.splitlines()


@pytest.mark.parametrize("path", TEAM_FILES)
def test_team_files_are_not_ignored_so_a_clean_clone_receives_them(path):
    assert (ROOT / path).is_file(), f"falta {path}"
    assert git("check-ignore", "-q", path).returncode == 1, f"{path} está ignorado por git"
