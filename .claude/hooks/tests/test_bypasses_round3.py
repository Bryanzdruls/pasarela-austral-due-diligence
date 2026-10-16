"""Evasiones halladas en la tercera revisión independiente del ticket #9."""

import pytest
from helpers import make_repo, payload, run_hook

SECRETS = "secrets_guard.py"
CUERPO = "print(open('.env').read())"


@pytest.mark.parametrize(
    "comando",
    [
        f"python - git commit <<'PY'\n{CUERPO}\nPY",
        f"python - \"git commit\" <<'PY'\n{CUERPO}\nPY",
        f"git commit -m x & python - <<'PY'\n{CUERPO}\nPY",
        f"git commit -m \"$(python - <<'PY'\n{CUERPO}\nPY\n)\"",
        f"echo hola\ngit commit -m x && python - <<'PY'\n{CUERPO}\nPY",
    ],
)
def test_a_heredoc_of_another_command_is_always_inspected(tmp_path, comando):
    repo = make_repo(tmp_path, "009-x")
    code, _, err = run_hook(SECRETS, payload("Bash", repo, command=comando), repo)
    assert code == 2 and "secretos" in err


@pytest.mark.parametrize(
    "comando",
    [
        "git commit -F - <<'EOF'\nmenciona .env en el mensaje\nEOF",
        "gh pr create --title x --body-file - <<'EOF'\nmenciona .env\nEOF",
        "git commit -m 'menciona .env'",
    ],
)
def test_a_plain_message_heredoc_stays_allowed(tmp_path, comando):
    repo = make_repo(tmp_path, "009-x")
    code, _, err = run_hook(SECRETS, payload("Bash", repo, command=comando), repo)
    assert code == 0, err
