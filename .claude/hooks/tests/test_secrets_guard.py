import pytest
from helpers import make_repo, payload, run_hook

SCRIPT = "secrets_guard.py"

PROTEGIDOS = [
    ".env",
    ".env.local",
    ".env.production",
    ".ENV",
    ".Env.Local",
    ".envrc",
    "secrets/clave.txt",
    "config/secrets/x.json",
    "clave.pem",
    "certs/servidor.pem",
    "llave.key",
    "credentials.json",
    "credentials-prod.json",
    "id_rsa",
]
PERMITIDOS = [
    ".env.example",
    ".ENV.EXAMPLE",
    "environment.py",
    "mcp_server/env_utils.py",
    "docs/secrets.md",
    "README.md",
    "pyproject.toml",
    "keyboard.py",
]


@pytest.fixture
def repo(tmp_path):
    return make_repo(tmp_path, "009-feature", ("spec.md", "plan.md", "tasks.md"))


def herramienta(nombre, repo, ruta):
    if nombre == "Read":
        return payload("Read", repo, file_path=ruta)
    if nombre == "Edit":
        return payload("Edit", repo, file_path=ruta, old_string="a", new_string="b")
    return payload("Write", repo, file_path=ruta, content="X=1\n")


@pytest.mark.parametrize("tool", ["Read", "Edit", "Write"])
@pytest.mark.parametrize("ruta", PROTEGIDOS)
def test_protected_files_cannot_be_read_or_modified(repo, tool, ruta):
    code, _, err = run_hook(SCRIPT, herramienta(tool, repo, ruta), repo)
    assert code == 2
    assert "secretos" in err and ruta.split("/")[-1] in err


@pytest.mark.parametrize("tool", ["Read", "Edit", "Write"])
@pytest.mark.parametrize("ruta", PERMITIDOS)
def test_the_template_and_ordinary_files_are_allowed(repo, tool, ruta):
    code, _, err = run_hook(SCRIPT, herramienta(tool, repo, ruta), repo)
    assert code == 0, err


@pytest.mark.parametrize("forma", ["relativa", "absoluta", "barras_invertidas", "punto_barra"])
def test_the_same_file_is_recognized_however_the_path_is_written(repo, forma):
    ruta = {
        "relativa": ".env",
        "absoluta": str(repo / ".env"),
        "barras_invertidas": str(repo / ".env").replace("/", "\\"),
        "punto_barra": "./.env",
    }[forma]
    code, _, err = run_hook(SCRIPT, herramienta("Read", repo, ruta), repo)
    assert code == 2 and "secretos" in err


# --------------------------------------------------------------------------- Bash


@pytest.mark.parametrize(
    "comando",
    [
        "cat .env",
        "type .env",
        "Get-Content .env",
        "gc .env.local",
        "head .env",
        "tail -n 5 .env.production",
        "less .env",
        "sed -n 1p .env",
        "grep API .env",
        "cp .env copia.txt",
        "mv .env .env.bak2",
        "echo X=1 > .env",
        "echo X=1 >> .env.local",
        "git add .env",
        "cat secrets/clave.txt",
        "cat llave.key",
        "cat certs/servidor.pem",
        "python -c \"print(open('.env').read())\"",
        "python -c \"import pathlib; pathlib.Path('.env').read_text()\"",
        "cat C:\\proyecto\\.env",
        'type ".env"',
        "CAT .ENV",
        "cp .env.example .env.example.bak",  # solo `.env.example` exacto es la plantilla
    ],
)
def test_terminal_commands_that_touch_protected_files_are_blocked(repo, comando):
    code, _, err = run_hook(SCRIPT, payload("Bash", repo, command=comando), repo)
    assert code == 2 and "secretos" in err


@pytest.mark.parametrize(
    "comando",
    [
        "ls",
        "ls -la",
        "cat .env.example",
        "type .env.example",
        "git status",
        "git add .gitignore",
        "python -m uv run pytest -q",
        "echo hola",
        "cat mcp_server/environment.py",
        "ls .env",  # solo lista el nombre; no lee el contenido
    ],
)
def test_ordinary_terminal_commands_and_the_template_are_allowed(repo, comando):
    code, _, err = run_hook(SCRIPT, payload("Bash", repo, command=comando), repo)
    assert code == 0, err


# ------------------------------------------------------- mensajes (hallazgo del uso real)


@pytest.mark.parametrize(
    "comando",
    [
        'git commit -m "no se versiona el archivo .env"',
        "git commit -m 'secrets/ y *.pem quedan fuera'",
        "git commit -F - <<'EOF'\nHook de secretos\n\n- .env, .env.* y secrets/ no se leen\nEOF",
        "cd repo && git add docs && git commit -q -F - <<'EOF'\nCubre .env y llave.key\nEOF\ngit log",  # noqa: E501
        'gh issue comment 9 --body "ignora .env y secrets/"',
        "gh pr create --title \"Protege .env\" --body 'texto con secrets/x'",
    ],
)
def test_text_of_commit_and_pull_request_messages_is_not_a_file_access(repo, comando):
    code, _, err = run_hook(SCRIPT, payload("Bash", repo, command=comando), repo)
    assert code == 0, err


@pytest.mark.parametrize(
    "comando",
    [
        'git commit .env -m "mensaje"',  # el archivo sí se compromete
        "git commit -F - .env <<'EOF'\nmensaje\nEOF",
        "python - <<'PY'\nprint(open('.env').read())\nPY",  # un heredoc de código sí se ejecuta
        "cat <<'EOF' > .env\nX=1\nEOF",  # escribe en el archivo protegido
        "git add .env && git commit -m ok",
    ],
)
def test_a_message_does_not_hide_a_real_access_to_a_protected_file(repo, comando):
    code, _, err = run_hook(SCRIPT, payload("Bash", repo, command=comando), repo)
    assert code == 2 and "secretos" in err


def test_the_message_reaches_the_user_as_valid_utf8_even_without_pythonioencoding(repo):
    import json
    import os
    import subprocess
    import sys

    from helpers import HOOKS_DIR

    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    proc = subprocess.run(
        [sys.executable, str(HOOKS_DIR / SCRIPT)],
        input=json.dumps(payload("Read", repo, file_path=".env")).encode("utf-8"),
        capture_output=True,
        env=env,
        cwd=str(repo),
    )
    assert proc.returncode == 2
    assert "sí está permitida" in proc.stderr.decode("utf-8")  # sin � ni cp1252


# --------------------------------------------------------------------------- otras herramientas


@pytest.mark.parametrize("tool", ["Grep", "Glob", "WebFetch"])
def test_tools_without_a_file_path_are_ignored(repo, tool):
    assert run_hook(SCRIPT, payload(tool, repo, pattern="x"), repo)[0] == 0


# --------------------------------------------------------------------------- fallo seguro


def test_invalid_input_fails_closed(repo):
    code, _, err = run_hook(SCRIPT, "no es json", repo)
    assert code == 2 and "deniega por seguridad" in err


def test_an_unexpected_shape_of_the_input_fails_closed(repo):
    data = {"tool_name": "Read", "tool_input": ["no", "es", "un", "objeto"]}
    code, _, err = run_hook(SCRIPT, data, repo)
    assert code == 2 and "deniega por seguridad" in err
