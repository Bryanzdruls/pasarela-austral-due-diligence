import json

import pytest
from helpers import make_repo, payload, run_hook

SCRIPT = "spec_gate.py"
TODOS = ("spec.md", "plan.md", "tasks.md")
ARTEFACTOS = [(), ("spec.md",), ("spec.md", "plan.md"), TODOS]
PRODUCCION = ["mcp_server/tools/nuevo.py", "due_diligence/x.py", "chat/app.py"]
NO_PRODUCCION = [
    "mcp_server/tests/test_x.py",
    "docs/nota.md",
    "specs/009-feature/extra.md",
    "scripts/util.py",
    "mcp_server/data/x.json",
    "pyproject.toml",
    ".claude/settings.json",
    "README.md",
]


def write(repo, path):
    return payload("Write", repo, file_path=str(repo / path), content="x = 1\n")


def edit(repo, path):
    return payload("Edit", repo, file_path=str(repo / path), old_string="a", new_string="b")


def bash(repo, command):
    return payload("Bash", repo, command=command)


@pytest.mark.parametrize("herramienta", [write, edit])
@pytest.mark.parametrize("artefactos", ARTEFACTOS)
@pytest.mark.parametrize("ruta", PRODUCCION)
def test_production_code_needs_spec_plan_and_tasks(tmp_path, herramienta, artefactos, ruta):
    repo = make_repo(tmp_path, "009-feature", artefactos)
    code, _, err = run_hook(SCRIPT, herramienta(repo, ruta), repo)
    if set(artefactos) == set(TODOS):
        assert code == 0, err
    else:
        assert code == 2
        faltan = [a for a in TODOS if a not in artefactos]
        assert faltan[0] in err
        assert "specs/009-feature" in err


@pytest.mark.parametrize(
    "artefactos, comando",
    [
        ((), "/speckit-specify"),
        (("spec.md",), "/speckit-plan"),
        (("spec.md", "plan.md"), "/speckit-tasks"),
    ],
)
def test_the_message_names_the_missing_artifact_and_the_command_that_creates_it(
    tmp_path, artefactos, comando
):
    repo = make_repo(tmp_path, "009-feature", artefactos)
    code, _, err = run_hook(SCRIPT, write(repo, "mcp_server/a.py"), repo)
    assert code == 2 and comando in err


@pytest.mark.parametrize("ruta", NO_PRODUCCION)
def test_everything_that_is_not_production_code_is_always_allowed(tmp_path, ruta):
    repo = make_repo(tmp_path, "009-feature", ())  # sin ningún artefacto
    code, _, err = run_hook(SCRIPT, write(repo, ruta), repo)
    assert code == 0, err


def test_a_branch_without_ticket_blocks_production_code(tmp_path):
    repo = make_repo(tmp_path, "main")
    code, _, err = run_hook(SCRIPT, write(repo, "mcp_server/a.py"), repo)
    assert code == 2 and "La rama no corresponde a un ticket" in err


def test_a_branch_without_ticket_still_allows_documents(tmp_path):
    repo = make_repo(tmp_path, "main")
    assert run_hook(SCRIPT, write(repo, "docs/x.md"), repo)[0] == 0


def test_the_pointer_is_the_fallback_when_the_branch_has_no_number(tmp_path):
    repo = make_repo(tmp_path, "main", carpeta="009-feature", artefactos=TODOS)
    (repo / ".specify").mkdir()
    (repo / ".specify" / "feature.json").write_text(
        json.dumps({"feature_directory": "specs/009-feature"}), encoding="utf-8"
    )
    assert run_hook(SCRIPT, write(repo, "mcp_server/a.py"), repo)[0] == 0


def test_the_branch_wins_over_a_stale_pointer(tmp_path):
    repo = make_repo(tmp_path, "002-otro", ("spec.md",))
    stale = repo / "specs" / "009-feature"
    stale.mkdir(parents=True)
    for name in TODOS:
        (stale / name).write_text("x", encoding="utf-8")
    (repo / ".specify").mkdir()
    (repo / ".specify" / "feature.json").write_text(
        json.dumps({"feature_directory": "specs/009-feature"}), encoding="utf-8"
    )
    code, _, err = run_hook(SCRIPT, write(repo, "mcp_server/a.py"), repo)
    assert code == 2 and "specs/002-feature" in err  # la de la rama, no la del puntero obsoleto
    assert "specs/009-feature" not in err


def test_windows_paths_with_backslashes_are_recognized(tmp_path):
    repo = make_repo(tmp_path, "009-feature", ())
    data = payload("Write", repo, file_path="mcp_server\\tools\\a.py", content="x")
    code, _, err = run_hook(SCRIPT, data, repo)
    assert code == 2 and "spec.md" in err and "specs/009-feature" in err


def test_a_file_outside_the_repository_is_not_production_code(tmp_path):
    repo = make_repo(tmp_path / "repo_dir" if False else tmp_path, "009-feature", ())
    outside = tmp_path.parent / "otro_proyecto" / "app.py"
    data = payload("Write", repo, file_path=str(outside), content="x")
    assert run_hook(SCRIPT, data, repo)[0] == 0


# --------------------------------------------------------------------------- Bash


@pytest.mark.parametrize(
    "comando",
    [
        "echo x > mcp_server/a.py",
        "echo x >> mcp_server/a.py",
        "cat plantilla | tee chat/app.py",
        "Set-Content -Path mcp_server/a.py -Value x",
        "'x' | Out-File mcp_server/a.py",
        "sed -i s/a/b/ mcp_server/a.py",
        "cp tmp/x.py due_diligence/a.py",
        "mv tmp/x.py due_diligence/a.py",
        "python -c \"open('mcp_server/a.py','w').write('x')\"",
    ],
)
def test_terminal_writes_to_production_are_blocked_without_the_artifacts(tmp_path, comando):
    repo = make_repo(tmp_path, "009-feature", ("spec.md",))
    code, _, err = run_hook(SCRIPT, bash(repo, comando), repo)
    assert code == 2 and "plan.md" in err


@pytest.mark.parametrize(
    "comando",
    [
        "echo x > mcp_server/a.py",
        "cat plantilla | tee chat/app.py",
        "sed -i s/a/b/ mcp_server/a.py",
    ],
)
def test_terminal_writes_to_production_are_allowed_with_the_artifacts(tmp_path, comando):
    repo = make_repo(tmp_path, "009-feature", TODOS)
    assert run_hook(SCRIPT, bash(repo, comando), repo)[0] == 0


@pytest.mark.parametrize(
    "comando",
    [
        "cat mcp_server/a.py",
        "ls mcp_server",
        "python -m uv run pytest -q",
        "git status",
        "echo x > docs/nota.md",
        "echo x > mcp_server/tests/test_a.py",
        "cp mcp_server/a.py /tmp/copia.py",
    ],
)
def test_terminal_commands_that_do_not_write_production_code_are_allowed(tmp_path, comando):
    repo = make_repo(tmp_path, "009-feature", ())
    code, _, err = run_hook(SCRIPT, bash(repo, comando), repo)
    assert code == 0, err


# --------------------------------------------------------------------------- tools ajenas


@pytest.mark.parametrize("herramienta", ["Read", "Grep", "Glob", "WebFetch"])
def test_tools_that_do_not_write_are_ignored(tmp_path, herramienta):
    repo = make_repo(tmp_path, "main")
    data = payload(herramienta, repo, file_path=str(repo / "mcp_server" / "a.py"))
    assert run_hook(SCRIPT, data, repo)[0] == 0


# --------------------------------------------------------------------------- fallo seguro


def test_invalid_input_fails_closed(tmp_path):
    repo = make_repo(tmp_path, "009-feature", TODOS)
    code, _, err = run_hook(SCRIPT, "esto no es json", repo)
    assert code == 2 and "deniega por seguridad" in err


def test_a_corrupt_pointer_fails_closed(tmp_path):
    repo = make_repo(tmp_path, "main")
    (repo / ".specify").mkdir()
    (repo / ".specify" / "feature.json").write_text("{corrupto", encoding="utf-8")
    code, _, err = run_hook(SCRIPT, write(repo, "mcp_server/a.py"), repo)
    assert code == 2 and "deniega por seguridad" in err
