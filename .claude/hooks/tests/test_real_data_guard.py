import re
import subprocess

import pytest
import real_data_guard
from helpers import luhn_valid, make_card, make_documento, make_nit, make_repo, payload, run_hook

SCRIPT = "real_data_guard.py"


def write(repo, texto, ruta="docs/nota.md"):
    return payload("Write", repo, file_path=str(repo / ruta), content=texto)


def edit(repo, texto, ruta="docs/nota.md"):
    return payload("Edit", repo, file_path=str(repo / ruta), old_string="x", new_string=texto)


def bash(repo, comando):
    return payload("Bash", repo, command=comando)


@pytest.fixture
def repo(tmp_path):
    return make_repo(tmp_path, "009-feature", ("spec.md", "plan.md", "tasks.md"))


# ------------------------------------------------------------------ el generador es fiable


@pytest.mark.parametrize("longitud", [13, 16, 19])
def test_the_generated_cards_have_a_valid_check_digit(longitud):
    assert luhn_valid(make_card(longitud))
    assert not luhn_valid(make_card(longitud, valida=False))


# ------------------------------------------------------------------ tarjetas


@pytest.mark.parametrize("longitud", [13, 16, 19])
@pytest.mark.parametrize("agrupada", [False, True])
def test_a_valid_card_number_is_blocked(repo, longitud, agrupada):
    tarjeta = make_card(longitud, agrupada)
    code, _, err = run_hook(SCRIPT, write(repo, f"pago con {tarjeta} ok"), repo)
    assert code == 2
    assert "tarjeta" in err


@pytest.mark.parametrize("longitud", [13, 16, 19])
@pytest.mark.parametrize("agrupada", [False, True])
def test_the_same_shapes_without_a_valid_check_digit_are_allowed(repo, longitud, agrupada):
    numero = make_card(longitud, agrupada, valida=False)
    code, _, err = run_hook(SCRIPT, write(repo, f"código {numero}"), repo)
    assert code == 0, err


def test_amex_style_grouping_is_blocked(repo):
    plano = make_card(15)
    amex = f"{plano[:4]} {plano[4:10]} {plano[10:]}"
    assert run_hook(SCRIPT, write(repo, amex), repo)[0] == 2


# ------------------------------------------------------------------ NIT y documentos


@pytest.mark.parametrize("con_puntos", [True, False])
def test_a_nit_is_blocked(repo, con_puntos):
    code, _, err = run_hook(SCRIPT, write(repo, f"empresa {make_nit(con_puntos)}"), repo)
    assert code == 2 and "NIT" in err


@pytest.mark.parametrize(
    "etiqueta", ["cédula", "cedula", "CC", "NIT", "documento", "identificación"]
)
@pytest.mark.parametrize("digitos", [6, 8, 10])
def test_a_labeled_document_number_is_blocked(repo, etiqueta, digitos):
    code, _, err = run_hook(SCRIPT, write(repo, make_documento(etiqueta, digitos)), repo)
    assert code == 2 and "documento" in err


def test_an_unlabeled_number_of_the_same_length_is_allowed(repo):
    assert run_hook(SCRIPT, write(repo, "ref " + "7" * 9 + " fin"), repo)[0] == 0


def test_a_label_with_too_few_digits_is_allowed(repo):
    assert run_hook(SCRIPT, write(repo, "documento 2026 y cédula 123"), repo)[0] == 0


# ------------------------------------------------------------------ lo que NO se bloquea


@pytest.mark.parametrize(
    "texto",
    [
        "FICT-0001",
        "NIT: FICT-1001",
        "documento FICT-0003",
        "CO-TV-0001 y CO-FH-0006",
        "2026-10-16T17:21:45.123456+00:00",
        "2026-10-14 2026-10-15",
        "sha256:" + "ab12" * 16,
        "versión 1.1.1 del 2026-10-16",
        "def f(x):\n    return x + 1\n",
    ],
)
def test_fictitious_identifiers_and_ordinary_text_are_allowed(repo, texto):
    code, _, err = run_hook(SCRIPT, write(repo, texto), repo)
    assert code == 0, err


# ------------------------------------------------------------------ herramientas


def test_edit_checks_the_new_string(repo):
    assert run_hook(SCRIPT, edit(repo, f"tarjeta {make_card()}"), repo)[0] == 2
    assert run_hook(SCRIPT, edit(repo, "texto normal"), repo)[0] == 0


def test_bash_checks_the_text_of_the_command(repo):
    assert run_hook(SCRIPT, bash(repo, f"echo {make_card()} > datos.txt"), repo)[0] == 2
    assert run_hook(SCRIPT, bash(repo, "python -m uv run pytest -q"), repo)[0] == 0


@pytest.mark.parametrize("herramienta", ["Read", "Grep", "Glob"])
def test_tools_that_do_not_write_are_ignored(repo, herramienta):
    data = payload(herramienta, repo, file_path=f"{make_card()}.txt", pattern=make_card())
    assert run_hook(SCRIPT, data, repo)[0] == 0


# ------------------------------------------------------------------ mensaje


def test_the_message_masks_the_detected_value(repo):
    tarjeta = make_card()
    _, _, err = run_hook(SCRIPT, write(repo, f"pago {tarjeta}"), repo)
    assert tarjeta not in err
    assert tarjeta[:-4] not in err
    assert "FICT-" in err  # dice qué usar en su lugar


def test_the_message_masks_documents_and_nits_too(repo):
    nit = make_nit()
    _, _, err = run_hook(SCRIPT, write(repo, f"empresa {nit}"), repo)
    assert nit not in err
    documento = make_documento("cédula", 9)
    _, _, err = run_hook(SCRIPT, write(repo, documento), repo)
    assert documento.split()[1] not in err


# ------------------------------------------------------------------ fallo seguro


def test_invalid_input_fails_closed(repo):
    code, _, err = run_hook(SCRIPT, "no es json", repo)
    assert code == 2 and "deniega por seguridad" in err


# ------------------------------------------------------------------ SC-003: el repositorio no se


def test_no_versioned_file_of_the_repository_is_blocked_when_rewritten(repo):
    raiz = real_data_guard.common.project_root({"cwd": "."})
    listing = subprocess.run(
        ["git", "ls-files"], cwd=raiz, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    checked = 0
    offenders = []
    for name in listing:
        try:
            with open(f"{raiz}/{name}", encoding="utf-8") as handle:
                text = handle.read()
        except (UnicodeDecodeError, OSError):
            continue  # binarios o archivos eliminados
        checked += 1
        for tipo, valor in real_data_guard.find_sensitive(text):
            offenders.append((name, tipo, re.sub(r"\d", "*", valor)))
    assert checked > 50
    assert offenders == []


# ------------------------------------------------------------------ cadenas hexadecimales (sumas


def test_a_valid_looking_digit_run_inside_a_hex_string_is_not_a_card(repo):
    # Las sumas de verificación y los hashes de los bloqueos de dependencias llevan tramos largos
    # de dígitos entre letras; un número real aparece aislado, no pegado a letras.
    hash_con_digitos = "a" + make_card(15) + "f" + make_card(14) + "c"
    code, _, err = run_hook(SCRIPT, write(repo, f'hash = "sha256:{hash_con_digitos}"'), repo)
    assert code == 0, err


def test_a_label_inside_a_path_is_not_a_document_label(repo):
    ruta = "files.pythonhosted.org/packages/f0/cc/" + "7" * 7 + "b4d9"
    assert run_hook(SCRIPT, write(repo, ruta), repo)[0] == 0


def test_an_isolated_card_between_punctuation_is_still_blocked(repo):
    tarjeta = make_card()
    for texto in (f"({tarjeta})", f'"{tarjeta}"', f"pago:{tarjeta}.", f"{tarjeta},otro"):
        assert run_hook(SCRIPT, write(repo, texto), repo)[0] == 2, texto
