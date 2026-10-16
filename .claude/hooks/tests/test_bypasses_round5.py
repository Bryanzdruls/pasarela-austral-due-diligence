"""Evasiones de la quinta revisión: sin poda de mensajes no hay nada que esquivar."""

import pytest
from helpers import make_repo, payload, run_hook


@pytest.mark.parametrize(
    "comando",
    [
        "git commit -m ok; echo '-m \"'; cat .env; echo '\"'",
        "git commit <<<EOF\ncat .env\nEOF",
    ],
)
def test_nothing_in_a_commit_command_hides_a_protected_file(tmp_path, comando):
    repo = make_repo(tmp_path, "009-x")
    code, _, err = run_hook("secrets_guard.py", payload("Bash", repo, command=comando), repo)
    assert code == 2 and "secretos" in err
