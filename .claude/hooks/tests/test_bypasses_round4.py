"""Evasiones halladas en la cuarta revisión independiente del ticket #9."""

import pytest
from helpers import make_repo, payload, run_hook

SECRETS = "secrets_guard.py"


@pytest.mark.parametrize(
    "comando",
    [
        'git commit -m "x <<EOF"\ncat .env\nEOF',
        "git commit -m 'x <<EOF'\ncat .env\nEOF",
        "git commit -m x # <<EOF\ncat .env\nEOF",
        "git commit -F - <<-EOF\nmsg\n\tEOF\ncat .env\nEOF",
    ],
)
def test_a_heredoc_lookalike_never_hides_a_protected_file(tmp_path, comando):
    repo = make_repo(tmp_path, "009-x")
    code, _, err = run_hook(SECRETS, payload("Bash", repo, command=comando), repo)
    assert code == 2 and "secretos" in err
