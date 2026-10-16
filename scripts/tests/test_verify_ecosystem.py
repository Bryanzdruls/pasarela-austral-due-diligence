"""Verificación automática de los mínimos del enunciado, sobre árboles sintéticos."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
import verify_ecosystem as v

SCRIPT = Path(__file__).resolve().parents[1] / "verify_ecosystem.py"

AGENT = (
    "---\nname: {n}\ndescription: Revisor de solo lectura\ntools: Read, Grep, Glob\n---\ncuerpo\n"
)
RULE = '---\npaths:\n  - "{glob}"\n---\ncuerpo de la regla\n'


def skill(name, extra):
    return f"---\nname: {name}\ndescription: Una skill\n{extra}---\ncuerpo\n"


def settings(pre=("a.py",), post=("b.py",)):
    def group(matcher, scripts):
        return {
            "matcher": matcher,
            "hooks": [
                {
                    "type": "command",
                    "command": "python",
                    "args": ["${CLAUDE_PROJECT_DIR}/.claude/hooks/" + s],
                    "timeout": 30,
                }
                for s in scripts
            ],
        }

    hooks = {}
    if pre:
        hooks["PreToolUse"] = [group("Edit|Write", pre)]
    if post:
        hooks["PostToolUse"] = [group("Edit|Write", post)]
    return json.dumps({"permissions": {"deny": ["Read(.env)"]}, "hooks": hooks})


def mcp(github=True, projects=True, own=True, token="${GITHUB_PERSONAL_ACCESS_TOKEN}"):
    servers = {}
    if github:
        toolsets = "default,projects" if projects else "default"
        servers["github"] = {
            "type": "http",
            "url": "https://api.githubcopilot.com/mcp/",
            "headers": {"Authorization": f"Bearer {token}", "X-MCP-Toolsets": toolsets},
        }
    if own:
        servers["pasarela-fuentes"] = {"type": "stdio", "command": "python", "args": ["-m", "x"]}
    return json.dumps({"mcpServers": servers})


PIECES = [
    "CLAUDE.md",
    "mcp_server/CLAUDE.md",
    "docs/convenciones.md",
    ".claude/rules/a.md",
    ".claude/rules/b.md",
    ".claude/agents/uno.md",
    ".claude/agents/dos.md",
    ".claude/skills/s1/SKILL.md",
    ".claude/skills/s2/SKILL.md",
    ".claude/commands/abrir-pr.md",
    ".claude/settings.json",
    ".claude/hooks/a.py",
    ".claude/hooks/b.py",
    ".mcp.json",
    "scripts/verify_ecosystem.py",
]


def inventory(paths=PIECES):
    header = "| Pieza | Tipo | Necesidad | Ubicación | Por qué ahí | Alternativa descartada |\n"
    separator = "|---|---|---|---|---|---|\n"
    rows = "".join(f"| `{p}` | tipo | N1 | aquí | porque sí | otra |\n" for p in paths)
    return "# Ecosistema\n\n" + header + separator + rows


def build(root: Path, **override):
    files = {
        "CLAUDE.md": "# Proyecto\n@docs/convenciones.md\n",
        "docs/convenciones.md": "convenciones",
        "mcp_server/CLAUDE.md": "zona",
        ".claude/rules/a.md": RULE.format(glob="**/tests/**/*.py"),
        ".claude/rules/b.md": RULE.format(glob="specs/**"),
        ".claude/agents/uno.md": AGENT.format(n="uno"),
        ".claude/agents/dos.md": AGENT.format(n="dos"),
        ".claude/skills/s1/SKILL.md": skill(
            "s1", "context: fork\nallowed-tools: Read Grep\nargument-hint: <ticket>\n"
        ),
        ".claude/skills/s2/SKILL.md": skill(
            "s2", "allowed-tools: Bash(python x*)\nargument-hint: [--json]\n"
        ),
        ".claude/skills/speckit-plan/SKILL.md": skill("speckit-plan", ""),
        ".claude/commands/abrir-pr.md": "---\ndescription: Abre el PR\n---\ncuerpo\n",
        ".claude/settings.json": settings(),
        ".claude/hooks/a.py": "",
        ".claude/hooks/b.py": "",
        ".mcp.json": mcp(),
        "scripts/verify_ecosystem.py": "",
        "docs/ECOSISTEMA.md": inventory(),
    }
    files.update({k: val for k, val in override.items() if val is not None})
    for name in [k for k, val in override.items() if val is None]:
        files.pop(name, None)
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root


def failures(root):
    return {c.name: c.detail for c in v.check_all(root) if not c.ok}


# --------------------------------------------------------------------------- árbol completo


def test_a_complete_tree_passes_every_check(tmp_path):
    build(tmp_path)
    assert failures(tmp_path) == {}


def test_the_cli_exits_0_on_a_complete_tree_and_1_otherwise(tmp_path):
    build(tmp_path)
    ok = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path)], capture_output=True, text=True
    )
    assert ok.returncode == 0 and "FALLA" not in ok.stdout
    (tmp_path / "CLAUDE.md").unlink()
    bad = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path)], capture_output=True, text=True
    )
    assert bad.returncode == 1 and "FALLA" in bad.stdout and v.CHECK_MEMORY in bad.stdout


def test_json_output_is_a_valid_object_with_every_check(tmp_path):
    build(tmp_path)
    out = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
    )
    data = json.loads(out.stdout)
    assert data["ok"] is True
    assert {c["name"] for c in data["checks"]} == set(v.ALL_CHECKS)


# --------------------------------------------------------------------------- CLAUDE.md


def test_a_missing_root_memory_fails(tmp_path):
    build(tmp_path, **{"CLAUDE.md": None})
    assert v.CHECK_MEMORY in failures(tmp_path)


def test_memory_needs_an_import_or_a_subdirectory_file(tmp_path):
    build(tmp_path, **{"CLAUDE.md": "# solo\n", "mcp_server/CLAUDE.md": None})
    assert v.CHECK_MEMORY in failures(tmp_path)


def test_an_import_alone_is_enough(tmp_path):
    build(tmp_path, **{"mcp_server/CLAUDE.md": None})
    assert v.CHECK_MEMORY not in failures(tmp_path)


def test_a_subdirectory_file_alone_is_enough(tmp_path):
    build(tmp_path, **{"CLAUDE.md": "# solo\n"})
    assert v.CHECK_MEMORY not in failures(tmp_path)


def test_an_import_to_a_missing_file_fails(tmp_path):
    build(tmp_path, **{"docs/convenciones.md": None, "mcp_server/CLAUDE.md": None})
    assert v.CHECK_MEMORY in failures(tmp_path)


# --------------------------------------------------------------------------- reglas


def test_fewer_than_two_rules_with_paths_fails(tmp_path):
    build(tmp_path, **{".claude/rules/b.md": None})
    assert v.CHECK_RULES in failures(tmp_path)


def test_a_rule_without_paths_does_not_count(tmp_path):
    build(tmp_path, **{".claude/rules/b.md": "---\ndescription: sin alcance\n---\ncuerpo\n"})
    assert v.CHECK_RULES in failures(tmp_path)


# --------------------------------------------------------------------------- subagentes


def test_fewer_than_two_restricted_agents_fails(tmp_path):
    build(tmp_path, **{".claude/agents/dos.md": None})
    assert v.CHECK_AGENTS in failures(tmp_path)


def test_an_agent_that_can_write_does_not_count(tmp_path):
    build(
        tmp_path,
        **{".claude/agents/dos.md": "---\nname: dos\ndescription: d\ntools: Read, Edit\n---\n"},
    )
    assert v.CHECK_AGENTS in failures(tmp_path)


def test_an_agent_without_a_tools_field_does_not_count(tmp_path):
    build(tmp_path, **{".claude/agents/dos.md": "---\nname: dos\ndescription: d\n---\ncuerpo\n"})
    assert v.CHECK_AGENTS in failures(tmp_path)  # hereda todas las herramientas


# --------------------------------------------------------------------------- skills


def test_fewer_than_two_skills_fails_and_speckit_skills_do_not_count(tmp_path):
    build(tmp_path, **{".claude/skills/s2/SKILL.md": None})
    assert v.CHECK_SKILLS in failures(tmp_path)  # solo queda s1; speckit-plan no cuenta


@pytest.mark.parametrize(
    "falta, s1, s2",
    [
        ("context: fork", "allowed-tools: Read\nargument-hint: <t>\n", "allowed-tools: Read\n"),
        ("allowed-tools", "context: fork\nargument-hint: <t>\n", "argument-hint: <x>\n"),
        ("argument-hint", "context: fork\nallowed-tools: Read\n", "allowed-tools: Read\n"),
    ],
)
def test_the_skills_together_must_use_fork_allowed_tools_and_argument_hint(tmp_path, falta, s1, s2):
    build(
        tmp_path,
        **{
            ".claude/skills/s1/SKILL.md": skill("s1", s1),
            ".claude/skills/s2/SKILL.md": skill("s2", s2),
        },
    )
    problems = failures(tmp_path)
    assert v.CHECK_SKILL_OPTIONS in problems
    assert falta in problems[v.CHECK_SKILL_OPTIONS]


# --------------------------------------------------------------------------- hooks


def test_without_a_post_edit_hook_fails(tmp_path):
    build(tmp_path, **{".claude/settings.json": settings(post=())})
    assert v.CHECK_HOOKS in failures(tmp_path)


def test_without_a_blocking_pre_hook_fails(tmp_path):
    build(tmp_path, **{".claude/settings.json": settings(pre=())})
    assert v.CHECK_HOOKS in failures(tmp_path)


def test_fewer_than_two_hooks_fails(tmp_path):
    only = json.dumps(
        {
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Edit", "hooks": [{"type": "command", "command": "python"}]}
                ]
            }
        }
    )
    build(tmp_path, **{".claude/settings.json": only})
    assert v.CHECK_HOOKS in failures(tmp_path)


def test_a_hook_whose_script_does_not_exist_fails(tmp_path):
    build(tmp_path, **{".claude/hooks/b.py": None})
    problems = failures(tmp_path)
    assert v.CHECK_HOOKS in problems and "b.py" in problems[v.CHECK_HOOKS]


# --------------------------------------------------------------------------- comando


def test_without_a_project_command_fails(tmp_path):
    build(tmp_path, **{".claude/commands/abrir-pr.md": None})
    assert v.CHECK_COMMAND in failures(tmp_path)


def test_spec_kit_commands_do_not_count(tmp_path):
    build(
        tmp_path,
        **{
            ".claude/commands/abrir-pr.md": None,
            ".claude/commands/speckit.plan.md": "---\ndescription: d\n---\n",
        },
    )
    assert v.CHECK_COMMAND in failures(tmp_path)


# --------------------------------------------------------------------------- MCP


def test_without_the_github_server_fails(tmp_path):
    build(tmp_path, **{".mcp.json": mcp(github=False)})
    assert v.CHECK_MCP in failures(tmp_path)


def test_github_without_the_projects_toolset_fails(tmp_path):
    build(tmp_path, **{".mcp.json": mcp(projects=False)})
    problems = failures(tmp_path)
    assert v.CHECK_MCP in problems and "projects" in problems[v.CHECK_MCP]


def test_without_the_project_own_server_fails(tmp_path):
    build(tmp_path, **{".mcp.json": mcp(own=False)})
    assert v.CHECK_MCP in failures(tmp_path)


def test_a_literal_credential_in_the_mcp_config_fails(tmp_path):
    token = "gh" + "p_" + "a" * 30  # generado en tiempo de ejecución, nunca literal en el archivo
    build(tmp_path, **{".mcp.json": mcp(token=token)})
    problems = failures(tmp_path)
    assert v.CHECK_CREDENTIALS in problems
    assert token not in problems[v.CHECK_CREDENTIALS]  # el detalle no repite la credencial


def test_a_header_that_is_not_an_environment_reference_fails(tmp_path):
    build(tmp_path, **{".mcp.json": mcp(token="valor-pegado-a-mano")})
    assert v.CHECK_CREDENTIALS in failures(tmp_path)


# --------------------------------------------------------------------------- inventario


def test_a_piece_on_disk_without_a_row_fails_and_is_named(tmp_path):
    build(tmp_path, **{"docs/ECOSISTEMA.md": inventory([p for p in PIECES if p != ".mcp.json"])})
    problems = failures(tmp_path)
    assert v.CHECK_INVENTORY in problems and ".mcp.json" in problems[v.CHECK_INVENTORY]


def test_a_row_whose_path_does_not_exist_fails(tmp_path):
    build(tmp_path, **{"docs/ECOSISTEMA.md": inventory([*PIECES, ".claude/rules/fantasma.md"])})
    problems = failures(tmp_path)
    assert v.CHECK_INVENTORY in problems and "fantasma" in problems[v.CHECK_INVENTORY]


def test_a_missing_inventory_fails(tmp_path):
    build(tmp_path, **{"docs/ECOSISTEMA.md": None})
    assert v.CHECK_INVENTORY in failures(tmp_path)


def test_several_rows_may_point_to_the_same_file_with_a_fragment(tmp_path):
    paths = [*PIECES, ".claude/settings.json#permissions.deny"]
    build(tmp_path, **{"docs/ECOSISTEMA.md": inventory(paths)})
    assert failures(tmp_path) == {}


def test_spec_kit_skills_and_commands_need_no_row(tmp_path):
    build(tmp_path)
    assert (tmp_path / ".claude/skills/speckit-plan/SKILL.md").is_file()
    assert v.CHECK_INVENTORY not in failures(tmp_path)


def test_hook_helpers_that_settings_does_not_invoke_need_no_row(tmp_path):
    build(tmp_path, **{".claude/hooks/common.py": "", ".claude/hooks/tests/test_x.py": ""})
    assert v.CHECK_INVENTORY not in failures(tmp_path)
