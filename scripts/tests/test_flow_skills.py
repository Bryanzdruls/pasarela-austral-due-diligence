"""Skills del flujo de tickets y ampliación de `/abrir-pr` (ticket #10)."""

from pathlib import Path

import pytest
from frontmatter import as_list, parse_frontmatter

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".claude" / "skills"
COMMAND = ROOT / ".claude" / "commands" / "abrir-pr.md"

MCP_READ = {"mcp__github__projects_list", "mcp__github__issue_read"}
MCP_WRITE = "mcp__github__projects_write"
STATES = ["Todo", "In Progress", "In review", "Done"]
FILE_WRITERS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}


def read(path):
    return path.read_text(encoding="utf-8")


def tools_of(path):
    return as_list(parse_frontmatter(read(path)).get("allowed-tools"))


def assert_read_only_shell(tools):
    """Solo `git`/`gh` de lectura: ningún `Bash` sin argumento ni escritura de archivos."""
    assert not FILE_WRITERS & set(tools)
    shell = [tool for tool in tools if tool.startswith("Bash")]
    assert "Bash" not in shell
    for entry in shell:
        assert entry.startswith(("Bash(git status", "Bash(git log", "Bash(git branch")), entry


# --------------------------------------------------------------------------- siguiente-ticket

NEXT = SKILLS / "siguiente-ticket" / "SKILL.md"


def test_the_next_ticket_skill_exists_with_its_metadata():
    assert NEXT.is_file(), "falta .claude/skills/siguiente-ticket/SKILL.md"
    meta = parse_frontmatter(read(NEXT))
    assert meta["name"] == "siguiente-ticket"
    assert len(meta["description"]) > 40
    assert meta.get("argument-hint")


def test_the_next_ticket_skill_only_has_the_tools_it_needs():
    assert NEXT.is_file()
    tools = tools_of(NEXT)
    assert MCP_READ <= set(tools)
    assert MCP_WRITE in tools
    assert_read_only_shell(tools)


@pytest.mark.parametrize("state", STATES)
def test_the_next_ticket_skill_uses_the_exact_state_names(state):
    assert NEXT.is_file()
    assert state in read(NEXT)


def test_the_next_ticket_skill_states_the_order_and_the_guards():
    assert NEXT.is_file()
    text = read(NEXT).lower()
    assert "#9" in text and "#10" in text  # configuración del entorno primero
    assert "número" in text  # y luego por número ascendente
    assert "sincronizar-tickets" in text  # sincroniza antes de elegir
    assert "confirmación" in text  # si ya hay un ticket en progreso
    assert "/speckit-specify" in text  # el contenido es el insumo de la especificación
    assert "no modifiques nada" in text  # servidor o toolset no disponibles
    assert "toolset" in text


# --------------------------------------------------------------------------- sincronizar-tickets

SYNC = SKILLS / "sincronizar-tickets" / "SKILL.md"


def test_the_sync_skill_exists_with_its_metadata():
    assert SYNC.is_file(), "falta .claude/skills/sincronizar-tickets/SKILL.md"
    meta = parse_frontmatter(read(SYNC))
    assert meta["name"] == "sincronizar-tickets"
    assert len(meta["description"]) > 40


def test_the_sync_skill_reads_the_project_and_pull_requests_and_writes_only_the_status():
    assert SYNC.is_file()
    tools = tools_of(SYNC)
    assert {
        "mcp__github__projects_list",
        "mcp__github__list_pull_requests",
        "mcp__github__pull_request_read",
    } <= set(tools)
    assert MCP_WRITE in tools
    assert_read_only_shell(tools)


@pytest.mark.parametrize("state", STATES)
def test_the_sync_skill_uses_the_exact_state_names(state):
    assert SYNC.is_file()
    assert state in read(SYNC)


@pytest.mark.parametrize(
    "fragment",
    [
        "idempotente",  # repetirla sin cambios en la realidad no modifica nada
        "cerrado sin fusionar",  # no produce Done
        "closes #",  # señal de asociación PR-ticket
        "rama",  # la otra señal: el prefijo numérico de la rama
        "no modifiques nada",  # servidor o toolset no disponibles
        "autorización",  # invocar la skill es la autorización de los cambios
        "todo está al día",  # informe cuando no hay cambios
    ],
)
def test_the_sync_skill_describes_its_rules(fragment):
    assert SYNC.is_file()
    assert fragment in read(SYNC).lower()


# --------------------------------------------------------------------------- /abrir-pr ampliado


def test_the_pr_command_moves_the_ticket_and_comments_through_the_mcp():
    text = read(COMMAND)
    tools = as_list(parse_frontmatter(text).get("allowed-tools"))
    assert MCP_WRITE in tools
    assert "mcp__github__add_issue_comment" in tools
    assert not any(tool.startswith("Bash(gh issue comment") for tool in tools)


@pytest.mark.parametrize("section", ["Especificado", "Decidido", "Pendiente"])
def test_the_pr_command_requires_the_three_part_progress_comment(section):
    assert section in read(COMMAND)


def test_the_pr_command_keeps_its_guards():
    text = read(COMMAND)
    assert "In review" in text and "toolset" in text
    assert "code-reviewer" in text and "compliance-reviewer" in text
    assert "Closes #" in text
