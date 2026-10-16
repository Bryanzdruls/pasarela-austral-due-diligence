"""Disposición y autocontención del plugin `pasarela-revision` (no importa nada del repositorio)."""

import ast
import json
import re
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
HOOK_REF = "${CLAUDE_PLUGIN_ROOT}/hooks/real_data_guard.py"
# Prefijos de credenciales conocidas, armados por partes para no escribirlos completos aquí.
SECRET = re.compile(
    "|".join(
        ["sk-" + "ant-[A-Za-z0-9_-]{16,}", "gh[pousr]" + "_[A-Za-z0-9]{20,}", "github" + "_pat_"]
    )
)
FORBIDDEN_REFERENCES = [".claude/hooks", "scripts/", "specs/0", "docs/ECOSISTEMA", "C:\\Users"]


def read(relative):
    return (PLUGIN / relative).read_text(encoding="utf-8")


def frontmatter(text):
    lines = text.splitlines()
    assert lines and lines[0].strip() == "---", "sin frontmatter"
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    data = {}
    for line in lines[1:end]:
        key, _, value = line.partition(":")
        if _:
            data[key.strip()] = value.strip()
    return data


def plugin_files():
    return [
        path
        for path in PLUGIN.rglob("*")
        if path.is_file()
        and "tests" not in path.relative_to(PLUGIN).parts
        and "__pycache__" not in path.parts
    ]


# --------------------------------------------------------------------------- manifiesto


def test_the_manifest_is_valid_json_with_name_version_and_description():
    manifest = json.loads(read(".claude-plugin/plugin.json"))
    assert manifest["name"] == "pasarela-revision"
    assert manifest["version"] == "0.1.0"
    assert len(manifest["description"]) > 20


# --------------------------------------------------------------------------- piezas


def test_the_subagent_is_read_only_and_described():
    meta = frontmatter(read("agents/compliance-reviewer.md"))
    assert meta["name"] == "compliance-reviewer"
    assert len(meta["description"]) > 40
    assert [tool.strip() for tool in meta["tools"].split(",")] == ["Read", "Grep", "Glob"]


def test_the_skill_forks_and_declares_its_tools_and_argument():
    meta = frontmatter(read("skills/revisar-cumplimiento/SKILL.md"))
    assert meta["name"] == "revisar-cumplimiento"
    assert meta["context"] == "fork"
    assert meta["allowed-tools"].split() == ["Read", "Grep", "Glob"]
    assert meta["argument-hint"]


def test_the_hook_is_registered_for_pre_tool_use_and_its_script_exists():
    config = json.loads(read("hooks/hooks.json"))
    groups = config["hooks"]["PreToolUse"]
    commands = [hook for group in groups for hook in group["hooks"]]
    assert any(HOOK_REF in hook.get("args", []) for hook in commands)
    assert all(hook["command"] == "python" for hook in commands)
    matchers = "|".join(group["matcher"] for group in groups)
    for tool in ("Edit", "Write", "Bash", "PowerShell"):
        assert tool in matchers
    assert (PLUGIN / "hooks" / "real_data_guard.py").is_file()


def test_the_plugin_documents_installation_use_and_limits():
    text = read("README.md").lower()
    for fragment in ("marketplace", "install", "uninstall", "límites", "amenaza"):
        assert fragment in text


# --------------------------------------------------------------------------- autocontención


@pytest.mark.parametrize("reference", FORBIDDEN_REFERENCES)
def test_no_piece_references_paths_that_only_exist_in_this_repository(reference):
    for path in plugin_files():
        assert reference not in path.read_text(encoding="utf-8"), (path.name, reference)


def test_the_hook_only_imports_the_standard_library():
    tree = ast.parse(read("hooks/real_data_guard.py"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    assert modules <= set(sys.stdlib_module_names), modules - set(sys.stdlib_module_names)


def test_no_file_contains_a_credential():
    for path in plugin_files():
        assert not SECRET.search(path.read_text(encoding="utf-8")), path.name
