"""Evasiones halladas en la segunda revisión independiente del ticket #9."""

import pytest
from helpers import make_repo, payload, run_hook

SECRETS = "secrets_guard.py"


@pytest.mark.parametrize(
    "comando",
    [
        "git commit -m x && python - <<'PY'\nprint(open('.env').read())\nPY",
        "gh pr create --title x; cat <<EOF\n.env\nEOF",
        "ls > .env",
        "stat x >.env",
    ],
)
def test_a_second_command_or_a_redirect_cannot_hide_a_protected_file(tmp_path, comando):
    repo = make_repo(tmp_path, "009-x")
    code, _, err = run_hook(SECRETS, payload("Bash", repo, command=comando), repo)
    assert code == 2 and "secretos" in err


@pytest.mark.parametrize(
    "comando",
    [
        "git commit -F - <<'EOF'\nmenciona .env en el mensaje\nEOF",
        "git commit -m 'menciona .env' && git status",
        "ls .env.example",
    ],
)
def test_ordinary_messages_and_listings_stay_allowed(tmp_path, comando):
    repo = make_repo(tmp_path, "009-x")
    code, _, err = run_hook(SECRETS, payload("Bash", repo, command=comando), repo)
    assert code == 0, err
