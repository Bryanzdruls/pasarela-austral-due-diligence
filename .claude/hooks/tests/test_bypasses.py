"""Evasiones halladas en la revisión independiente del ticket #9."""

import common
import pytest
from helpers import make_repo, payload, run_hook

SECRETS = "secrets_guard.py"


@pytest.mark.parametrize(
    "comando",
    [
        "ls && cat .env",
        "ls | xargs cat .env",
        "dir ; type .env",
        'git commit -m "$(cat .env)"',
        'gh pr create --body "$(cat .env)"',
        "git commit -m `cat .env`",
    ],
)
def test_a_safe_command_or_a_message_cannot_hide_a_real_access(tmp_path, comando):
    repo = make_repo(tmp_path, "009-x")
    code, _, _ = run_hook(SECRETS, payload("Bash", repo, command=comando), repo)
    assert code == 2


@pytest.mark.parametrize(
    "herramienta, entrada",
    [
        ("Grep", {"pattern": "a", "path": ".env"}),
        ("Grep", {"pattern": "a", "glob": ".env*"}),
        ("Glob", {"pattern": "**/.env.local"}),
        ("PowerShell", {"command": "Get-Content .env"}),
    ],
)
def test_search_tools_and_powershell_are_covered(tmp_path, herramienta, entrada):
    repo = make_repo(tmp_path, "009-x")
    code, _, _ = run_hook(SECRETS, payload(herramienta, repo, **entrada), repo)
    assert code == 2


def test_a_normal_search_is_allowed(tmp_path):
    repo = make_repo(tmp_path, "009-x")
    entrada = {"pattern": "def ", "path": "mcp_server"}
    code, _, _ = run_hook(SECRETS, payload("Grep", repo, **entrada), repo)
    assert code == 0


@pytest.mark.parametrize(
    "comando",
    ["echo x>mcp_server/a.py", 'echo "x">mcp_server/a.py', "echo x >> mcp_server/a.py"],
)
def test_a_redirection_glued_to_the_word_is_detected(comando):
    assert "mcp_server/a.py" in common.bash_write_targets(comando)
