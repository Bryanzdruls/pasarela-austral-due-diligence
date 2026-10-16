"""Pruebas de `.claude/settings.json`: hooks de proyecto y permisos."""

import fnmatch
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SETTINGS = ROOT / ".claude" / "settings.json"
HOOKS_DIR = ROOT / ".claude" / "hooks"
PROJECT_VAR = "${CLAUDE_PROJECT_DIR}"


@pytest.fixture(scope="module")
def settings():
    return json.loads(SETTINGS.read_text(encoding="utf-8"))


def groups(settings, event):
    return settings["hooks"][event]


def scripts_by_matcher(settings, event):
    result = {}
    for group in groups(settings, event):
        for hook in group["hooks"]:
            script = Path(hook["args"][0]).name
            result.setdefault(group["matcher"], []).append(script)
    return result


def all_hooks(settings):
    for event, event_groups in settings["hooks"].items():
        for group in event_groups:
            for hook in group["hooks"]:
                yield event, group, hook


def test_the_settings_file_is_valid_json():
    assert isinstance(json.loads(SETTINGS.read_text(encoding="utf-8")), dict)


def test_the_blocking_hooks_are_registered_for_pre_tool_use(settings):
    by_matcher = scripts_by_matcher(settings, "PreToolUse")
    assert by_matcher["Edit|Write|Bash|PowerShell"] == ["spec_gate.py", "real_data_guard.py"]
    assert by_matcher["Read|Edit|Write|Bash|PowerShell|Grep|Glob"] == ["secrets_guard.py"]


def test_every_hook_is_a_python_command_with_a_timeout_and_an_existing_script(settings):
    hooks = list(all_hooks(settings))
    assert hooks, "no hay hooks registrados"
    for _event, _group, hook in hooks:
        assert hook["type"] == "command"
        assert hook["command"] == "python"
        assert len(hook["args"]) == 1
        assert hook["args"][0].startswith(PROJECT_VAR + "/.claude/hooks/")
        assert hook["timeout"] == 30
        script = HOOKS_DIR / Path(hook["args"][0]).name
        assert script.is_file(), f"no existe {script}"


# --------------------------------------------------------------------------- permisos

PROTECTED = [".env", ".env.local", ".env.production", "secrets/**", "*.pem", "*.key"]


def deny_rules(settings):
    return settings["permissions"]["deny"]


@pytest.mark.parametrize("pattern", PROTECTED)
@pytest.mark.parametrize("action", ["Read", "Edit"])
def test_deny_covers_reading_and_editing_each_protected_pattern(settings, action, pattern):
    assert f"{action}({pattern})" in deny_rules(settings)


def test_deny_never_covers_the_template(settings):
    for rule in deny_rules(settings):
        inner = re.fullmatch(r"\w+\((.*)\)", rule).group(1)
        assert not fnmatch.fnmatch(".env.example", inner.lstrip("./")), rule
        assert not fnmatch.fnmatch("./.env.example", inner), rule


def test_the_settings_contain_no_credentials(settings):
    text = SETTINGS.read_text(encoding="utf-8")
    pattern = (
        r"sk-ant-[A-Za-z0-9_-]{20,}|gh[po]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
        r"|BEGIN [A-Z ]*PRIVATE KEY"
    )
    assert re.search(pattern, text) is None


def test_the_format_hook_is_registered_for_post_tool_use(settings):
    assert scripts_by_matcher(settings, "PostToolUse") == {"Edit|Write": ["format_after_edit.py"]}


def test_there_is_exactly_one_post_edit_hook_and_it_never_blocks_by_design(settings):
    hooks = [h for g in groups(settings, "PostToolUse") for h in g["hooks"]]
    assert len(hooks) == 1
    source = (HOOKS_DIR / "format_after_edit.py").read_text(encoding="utf-8")
    assert "common.block" not in source  # un hook posterior a la edición nunca bloquea
