"""Hook de datos reales del plugin: se ejecuta el script real como subproceso (autocontenido).

Los valores con forma de tarjeta, NIT o documento se generan aquí en tiempo de ejecución: ninguno
se escribe literal en un archivo del repositorio.
"""

import json
import random
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "real_data_guard.py"


def run_hook(stdin):
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=stdin if isinstance(stdin, str) else json.dumps(stdin),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    return proc.returncode, proc.stdout, proc.stderr


def payload(tool, **tool_input):
    return {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input}


def _check_digit(partial):
    total = 0
    for index, char in enumerate(reversed(partial)):
        digit = int(char)
        if index % 2 == 0:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return str((10 - total % 10) % 10)


def make_card(length=16, grouped=False, valid=True, seed=7):
    rng = random.Random(f"{seed}-{length}")
    body = str(rng.randint(1, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(length - 2))
    check = _check_digit(body)
    if not valid:
        check = str((int(check) + 1) % 10)
    number = body + check
    if grouped:
        return " ".join(number[i : i + 4] for i in range(0, len(number), 4))
    return number


def make_nit(dotted=True, seed=11):
    rng = random.Random(seed)
    digits = "".join(str(rng.randint(0, 9)) for _ in range(9))
    dv = str(rng.randint(0, 9))
    if dotted:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:]}-{dv}"
    return f"{digits}-{dv}"


def make_document(label="cédula", digits=8, seed=13):
    rng = random.Random(seed)
    number = str(rng.randint(1, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(digits - 1))
    return f"{label} {number}"


# --------------------------------------------------------------------------- bloqueos


@pytest.mark.parametrize("tool, key", [("Write", "content"), ("Edit", "new_string")])
def test_a_card_number_in_written_content_is_blocked_and_masked(tool, key):
    card = make_card()
    code, _, err = run_hook(payload(tool, **{key: f"tarjeta de prueba {card}"}))
    assert code == 2
    assert "tarjeta" in err and card not in err
    assert err.count("*") >= 12 and card[-2:] in err  # solo quedan visibles los dos últimos dígitos


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
def test_a_shell_command_that_carries_a_real_looking_value_is_blocked(tool):
    code, _, err = run_hook(payload(tool, command=f"echo {make_card(grouped=True)} > datos.txt"))
    assert code == 2 and "tarjeta" in err


@pytest.mark.parametrize("length", [13, 15, 16, 19])
def test_cards_of_every_valid_length_are_blocked(length):
    code, _, err = run_hook(payload("Write", content=make_card(length=length)))
    assert code == 2 and "tarjeta" in err


@pytest.mark.parametrize("dotted", [True, False])
def test_a_nit_is_blocked(dotted):
    code, _, err = run_hook(payload("Write", content=f"NIT {make_nit(dotted=dotted)}"))
    assert code == 2 and "NIT" in err


@pytest.mark.parametrize("label", ["cédula", "cc", "documento", "identificación"])
def test_a_labelled_identity_document_is_blocked(label):
    code, _, err = run_hook(payload("Write", content=make_document(label=label)))
    assert code == 2 and "documento" in err


# --------------------------------------------------------------------------- permitidos


@pytest.mark.parametrize(
    "content",
    [
        "El comercio CO-TV-0001 (FICT-0007) no tiene hallazgos.",
        "texto corriente sin números",
        "versión 3.12.1 del 2026-10-16",
        "hash 9b74c9897bac770ffc029102a200c5de",
    ],
)
def test_fictional_identifiers_and_ordinary_text_are_allowed(content):
    code, _, err = run_hook(payload("Write", content=content))
    assert code == 0, err


def test_a_sixteen_digit_number_that_fails_luhn_is_allowed():
    code, _, err = run_hook(payload("Write", content=make_card(valid=False)))
    assert code == 0, err


@pytest.mark.parametrize("tool", ["Read", "Grep", "Glob", "WebFetch"])
def test_tools_that_do_not_write_are_ignored(tool):
    code, _, err = run_hook(payload(tool, content=make_card(), command=make_card()))
    assert code == 0, err


# --------------------------------------------------------------------------- falla cerrado


@pytest.mark.parametrize(
    "stdin",
    ["", "no es json", "[]", json.dumps({"tool_name": "Write", "tool_input": "texto"})],
)
def test_invalid_input_fails_closed_with_a_clear_message(stdin):
    code, _, err = run_hook(stdin)
    assert code == 2 and "real_data_guard" in err
