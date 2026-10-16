"""Evasiones de la sexta revisión: tuberías desde `ls`, texto unido por el shell y `>|`."""

import common
import pytest
from helpers import make_repo, payload, run_hook

NOMBRE = "." + "env"


def bloqueado(tmp_path, herramienta, comando):
    repo = make_repo(tmp_path, "009-x")
    return run_hook("secrets_guard.py", payload(herramienta, repo, command=comando), repo)


@pytest.mark.parametrize(
    "comando",
    [
        f"ls {NOMBRE} | xargs cat",
        f"dir {NOMBRE} | Get-Content",
        f"stat {NOMBRE} | cat",
        f"cat .e''{NOMBRE[2:]}",
        f'cat .e""{NOMBRE[2:]}',
        f"cat .e'n'{NOMBRE[3:]}",
        "cat .en\\v",
        f"ls (gc .e''{NOMBRE[2:]})",
    ],
)
def test_nothing_hides_a_protected_file(tmp_path, comando):
    tool = "PowerShell" if comando.startswith(("dir", "ls (")) else "Bash"
    code, _, err = bloqueado(tmp_path, tool, comando)
    assert code == 2 and "secretos" in err


def test_a_windows_path_with_backslashes_is_still_recognized(tmp_path):
    code, _, err = bloqueado(tmp_path, "Bash", "type config\\secrets\\clave.txt")
    assert code == 2 and "secretos" in err


def test_the_clobber_redirect_is_detected():
    assert "mcp_server/app.py" in common.bash_write_targets("echo x >| mcp_server/app.py")
