import os
import subprocess
import sys
from pathlib import Path

import format_after_edit
import pytest
from helpers import payload, run_hook

SCRIPT = "format_after_edit.py"
MAL_FORMATEADO = "x=1\nif x :\n  print( x )\n"
BIEN_FORMATEADO = "x = 1\nif x:\n    print(x)\n"


def post(tool, cwd, ruta):
    data = payload(tool, cwd, file_path=ruta)
    data["hook_event_name"] = "PostToolUse"
    return data


@pytest.fixture
def env_with_ruff():
    """PATH con el directorio del intérprete de las pruebas, donde está `ruff`."""
    return {"PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"]}


# --------------------------------------------------------------------------- de punta a punta


@pytest.mark.parametrize("herramienta", ["Edit", "Write"])
def test_a_badly_formatted_python_file_is_formatted_after_the_edit(
    tmp_path, env_with_ruff, herramienta
):
    archivo = tmp_path / "codigo.py"
    archivo.write_text(MAL_FORMATEADO, encoding="utf-8")
    code, _, err = run_hook(
        SCRIPT, post(herramienta, tmp_path, str(archivo)), tmp_path, env_with_ruff
    )
    assert code == 0, err
    assert archivo.read_text(encoding="utf-8") == BIEN_FORMATEADO


def test_an_already_formatted_file_is_left_as_it_is(tmp_path, env_with_ruff):
    archivo = tmp_path / "codigo.py"
    archivo.write_text(BIEN_FORMATEADO, encoding="utf-8")
    code, _, _ = run_hook(SCRIPT, post("Edit", tmp_path, str(archivo)), tmp_path, env_with_ruff)
    assert code == 0 and archivo.read_text(encoding="utf-8") == BIEN_FORMATEADO


@pytest.mark.parametrize(
    "nombre", ["nota.md", "datos.json", "texto.txt", "config.toml", "sin_extension"]
)
def test_files_that_are_not_python_are_never_modified(tmp_path, env_with_ruff, nombre):
    archivo = tmp_path / nombre
    archivo.write_text(MAL_FORMATEADO, encoding="utf-8")
    code, _, _ = run_hook(SCRIPT, post("Edit", tmp_path, str(archivo)), tmp_path, env_with_ruff)
    assert code == 0 and archivo.read_text(encoding="utf-8") == MAL_FORMATEADO


def test_a_relative_path_is_resolved_against_the_working_directory(tmp_path, env_with_ruff):
    (tmp_path / "pkg").mkdir()
    archivo = tmp_path / "pkg" / "codigo.py"
    archivo.write_text(MAL_FORMATEADO, encoding="utf-8")
    code, _, _ = run_hook(SCRIPT, post("Edit", tmp_path, "pkg/codigo.py"), tmp_path, env_with_ruff)
    assert code == 0 and archivo.read_text(encoding="utf-8") == BIEN_FORMATEADO


def test_windows_backslashes_are_accepted(tmp_path, env_with_ruff):
    (tmp_path / "pkg").mkdir()
    archivo = tmp_path / "pkg" / "codigo.py"
    archivo.write_text(MAL_FORMATEADO, encoding="utf-8")
    ruta = str(archivo).replace("/", "\\")
    code, _, _ = run_hook(SCRIPT, post("Edit", tmp_path, ruta), tmp_path, env_with_ruff)
    assert code == 0 and archivo.read_text(encoding="utf-8") == BIEN_FORMATEADO


def test_a_missing_file_is_ignored_without_noise(tmp_path, env_with_ruff):
    code, out, err = run_hook(
        SCRIPT, post("Edit", tmp_path, str(tmp_path / "no_existe.py")), tmp_path, env_with_ruff
    )
    assert code == 0 and not out and not err


def test_a_file_that_cannot_be_formatted_never_blocks_and_warns(tmp_path, env_with_ruff):
    archivo = tmp_path / "roto.py"
    archivo.write_text("def f(:\n  pass\n", encoding="utf-8")  # error de sintaxis
    code, _, err = run_hook(SCRIPT, post("Edit", tmp_path, str(archivo)), tmp_path, env_with_ruff)
    assert code == 0
    assert "formato" in err.lower() and "roto.py" in err
    assert archivo.read_text(encoding="utf-8") == "def f(:\n  pass\n"  # no se pierde la edición


def test_invalid_input_never_blocks_a_post_edit_hook(tmp_path):
    code, _, err = run_hook(SCRIPT, "no es json", tmp_path)
    assert code == 0 and "aviso" in err.lower()


# --------------------------------------------------------------------------- orden de formateadores


def test_the_formatter_search_order():
    solo_ruff = format_after_edit.candidates(lambda nombre: nombre == "ruff")
    assert solo_ruff[0] == ["ruff", "format"]
    solo_uv = format_after_edit.candidates(lambda nombre: nombre == "uv")
    assert solo_uv[0] == ["uv", "run", "ruff", "format"]
    ninguno = format_after_edit.candidates(lambda nombre: None)
    assert ninguno == [[sys.executable, "-m", "uv", "run", "ruff", "format"]]
    ambos = format_after_edit.candidates(lambda nombre: nombre)
    assert [c[0] for c in ambos][:2] == ["ruff", "uv"]


def _completed(code, err=""):
    return subprocess.CompletedProcess([], code, stdout="", stderr=err)


def test_a_formatter_that_works_returns_no_warning(tmp_path):
    archivo = tmp_path / "a.py"
    archivo.write_text("x = 1\n", encoding="utf-8")
    llamadas = []

    def run(cmd, **kwargs):
        llamadas.append(cmd)
        return _completed(0)

    assert format_after_edit.format_file(str(archivo), str(tmp_path), lambda n: n, run) is None
    assert llamadas == [["ruff", "format", str(archivo)]]


def test_if_the_first_formatter_is_missing_the_next_one_is_tried(tmp_path):
    archivo = tmp_path / "a.py"
    archivo.write_text("x = 1\n", encoding="utf-8")
    llamadas = []

    def run(cmd, **kwargs):
        llamadas.append(cmd[0])
        if cmd[0] == "ruff":
            raise FileNotFoundError("ruff")
        return _completed(0)

    assert format_after_edit.format_file(str(archivo), str(tmp_path), lambda n: n, run) is None
    assert llamadas == ["ruff", "uv"]


def test_no_formatter_available_gives_a_clear_warning_instead_of_an_error(tmp_path):
    archivo = tmp_path / "a.py"
    archivo.write_text("x = 1\n", encoding="utf-8")

    def run(cmd, **kwargs):
        raise FileNotFoundError(cmd[0])

    aviso = format_after_edit.format_file(str(archivo), str(tmp_path), lambda n: None, run)
    assert aviso and "no hay un formateador" in aviso.lower()


def test_a_formatter_that_fails_reports_its_message(tmp_path):
    archivo = tmp_path / "a.py"
    archivo.write_text("x = 1\n", encoding="utf-8")

    def run(cmd, **kwargs):
        return _completed(2, "error: no se pudo analizar")

    aviso = format_after_edit.format_file(str(archivo), str(tmp_path), lambda n: n, run)
    assert aviso and "no se pudo analizar" in aviso and "a.py" in aviso
