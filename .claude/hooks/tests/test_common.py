import io
import json
import subprocess

import common
import pytest

# --------------------------------------------------------------------------- entrada


def test_reads_a_valid_json_payload():
    payload = {"tool_name": "Edit", "tool_input": {"file_path": "a.py"}}
    assert common.read_payload(io.StringIO(json.dumps(payload))) == payload


@pytest.mark.parametrize("raw", ["", "   ", "no es json", "[1, 2]"])
def test_empty_or_invalid_payload_is_an_error(raw):
    with pytest.raises(ValueError):
        common.read_payload(io.StringIO(raw))


# --------------------------------------------------------------------------- rutas


def test_paths_are_normalized_to_posix_relative_to_the_root(tmp_path):
    root = str(tmp_path)
    assert common.relative_path(str(tmp_path / "mcp_server" / "a.py"), root) == "mcp_server/a.py"
    assert common.relative_path("mcp_server\\a.py", root) == "mcp_server/a.py"
    assert common.relative_path("./mcp_server/a.py", root) == "mcp_server/a.py"
    assert common.relative_path(str(tmp_path / "x" / ".." / "a.py"), root) == "a.py"


def test_a_path_outside_the_root_stays_absolute(tmp_path):
    outside = tmp_path.parent / "otro" / "a.py"
    assert common.relative_path(str(outside), str(tmp_path)).endswith("otro/a.py")
    assert "\\" not in common.relative_path(str(outside), str(tmp_path))


# --------------------------------------------------------------------------- producción


@pytest.mark.parametrize(
    "path",
    [
        "mcp_server/tools/registro.py",
        "due_diligence/coordinator.py",
        "chat/app.py",  # directorio de código nuevo: protegido por defecto
        "app.py",
        "src/pasarela/modelo.py",
        "MCP_SERVER/Tools/Registro.PY",  # mayúsculas
    ],
)
def test_production_code_is_every_py_outside_the_excluded_directories(path):
    assert common.is_production_path(path)


@pytest.mark.parametrize(
    "path",
    [
        "mcp_server/tests/test_registro.py",
        "due_diligence/tests/fakes.py",
        "scripts/verify_ecosystem.py",
        ".claude/hooks/common.py",
        ".specify/scripts/x.py",
        ".venv/lib/site.py",
        "docs/ECOSISTEMA.md",
        "specs/009-x/spec.md",
        "specs/009-x/contracts/api.py",
        "mcp_server/data/comercios.json",
        "README.md",
        "pyproject.toml",
        "mcp_server/CLAUDE.md",
    ],
)
def test_everything_else_is_not_production_code(path):
    assert not common.is_production_path(path)


# --------------------------------------------------------------------------- terminal


@pytest.mark.parametrize(
    "command, expected",
    [
        ("echo x > mcp_server/a.py", ["mcp_server/a.py"]),
        ("echo x >> mcp_server/a.py", ["mcp_server/a.py"]),
        ("echo x >mcp_server/a.py", ["mcp_server/a.py"]),
        ('echo x > "mcp_server/a b.py"', ["mcp_server/a b.py"]),
        ("cat plantilla | tee chat/app.py", ["chat/app.py"]),
        ("cat x | tee -a mcp_server/a.py", ["mcp_server/a.py"]),
        ("Set-Content -Path mcp_server/a.py -Value x", ["mcp_server/a.py"]),
        ("'x' | Out-File mcp_server/a.py", ["mcp_server/a.py"]),
        ("sed -i s/a/b/ mcp_server/a.py", ["mcp_server/a.py"]),
        ("cp tmp/x.py mcp_server/a.py", ["mcp_server/a.py"]),
        ("mv tmp/x.py due_diligence/a.py", ["due_diligence/a.py"]),
        ("cp mcp_server/a.py /tmp/copia.py", ["/tmp/copia.py"]),  # solo cuenta el destino
        ("python -c \"open('mcp_server/a.py','w').write('x')\"", ["mcp_server/a.py"]),
    ],
)
def test_terminal_commands_that_write_report_their_targets(command, expected):
    assert common.bash_write_targets(command) == expected


@pytest.mark.parametrize(
    "command",
    [
        "cat mcp_server/a.py",
        "ls mcp_server",
        "python -m uv run pytest -q",
        "git status",
        "git log --oneline",
        "echo hola",
        "python -c \"print(open('mcp_server/a.py').read())\"",  # lectura
    ],
)
def test_terminal_commands_that_do_not_write_report_nothing(command):
    assert common.bash_write_targets(command) == []


# --------------------------------------------------------------------------- feature activa


def _specs(tmp_path, *names):
    for name in names:
        (tmp_path / "specs" / name).mkdir(parents=True)


def test_feature_comes_from_the_numeric_branch_prefix(tmp_path):
    _specs(tmp_path, "009-ecosistema-claude-code", "002-coordinador")
    found = common.active_feature(str(tmp_path), branch="009-ecosistema-claude-code")
    assert found == tmp_path / "specs" / "009-ecosistema-claude-code"


def test_branch_number_matches_the_folder_even_if_the_suffix_differs(tmp_path):
    _specs(tmp_path, "009-ecosistema-claude-code")
    assert common.active_feature(str(tmp_path), branch="009-otro-nombre") == (
        tmp_path / "specs" / "009-ecosistema-claude-code"
    )


def test_branch_without_ticket_and_without_pointer_has_no_feature(tmp_path):
    _specs(tmp_path, "009-x")
    assert common.active_feature(str(tmp_path), branch="main") is None


def test_pointer_is_the_fallback_when_the_branch_has_no_number(tmp_path):
    _specs(tmp_path, "009-x")
    (tmp_path / ".specify").mkdir()
    (tmp_path / ".specify" / "feature.json").write_text(
        json.dumps({"feature_directory": "specs/009-x"}), encoding="utf-8"
    )
    assert common.active_feature(str(tmp_path), branch="main") == tmp_path / "specs" / "009-x"


def test_the_branch_wins_over_a_stale_pointer(tmp_path):
    _specs(tmp_path, "009-x", "002-y")
    (tmp_path / ".specify").mkdir()
    (tmp_path / ".specify" / "feature.json").write_text(
        json.dumps({"feature_directory": "specs/009-x"}), encoding="utf-8"
    )
    assert common.active_feature(str(tmp_path), branch="002-y") == tmp_path / "specs" / "002-y"


def test_a_branch_number_without_a_folder_has_no_feature(tmp_path):
    _specs(tmp_path, "009-x")
    assert common.active_feature(str(tmp_path), branch="005-sin-carpeta") is None


def test_missing_artifacts_lists_what_is_absent(tmp_path):
    feature = tmp_path / "specs" / "009-x"
    feature.mkdir(parents=True)
    assert common.missing_artifacts(feature) == ["spec.md", "plan.md", "tasks.md"]
    (feature / "spec.md").write_text("x", encoding="utf-8")
    (feature / "tasks.md").write_text("x", encoding="utf-8")
    assert common.missing_artifacts(feature) == ["plan.md"]


def test_current_branch_reads_the_git_branch(tmp_path):
    subprocess.run(["git", "init", "-q", "-b", "009-prueba"], cwd=tmp_path, check=True)
    assert common.current_branch(str(tmp_path)) == "009-prueba"


def test_current_branch_outside_a_repository_is_none(tmp_path):
    assert common.current_branch(str(tmp_path)) is None


# --------------------------------------------------------------------------- bloqueo


def test_block_exits_with_code_2_and_writes_the_reason_to_stderr(capsys):
    with pytest.raises(SystemExit) as exc:
        common.block("motivo claro")
    assert exc.value.code == 2
    assert "motivo claro" in capsys.readouterr().err


def test_fail_closed_turns_an_unexpected_error_into_a_block(capsys):
    @common.fail_closed("mi_hook")
    def hook():
        raise RuntimeError("boom")

    with pytest.raises(SystemExit) as exc:
        hook()
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "El hook mi_hook falló y deniega por seguridad" in err and "boom" in err


def test_fail_closed_lets_a_deliberate_block_and_a_normal_return_through(capsys):
    @common.fail_closed("mi_hook")
    def blocks():
        common.block("no")

    @common.fail_closed("mi_hook")
    def allows():
        return 0

    with pytest.raises(SystemExit) as exc:
        blocks()
    assert exc.value.code == 2
    assert allows() == 0
    assert capsys.readouterr().err.count("no") >= 1
