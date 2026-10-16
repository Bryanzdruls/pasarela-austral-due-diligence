"""Ayudantes para probar los hooks ejecutando el script real como subproceso.

Los datos sensibles de las pruebas se generan aquí **en tiempo de ejecución**: ningún valor con
forma de tarjeta, NIT o documento se escribe literal en ningún archivo del repositorio.
"""

import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parents[1]


def run_hook(script, payload, cwd, env=None, timeout=60):
    """Ejecuta el hook con `payload` por stdin; devuelve (código, stdout, stderr)."""
    proc = subprocess.run(
        [sys.executable, str(HOOKS_DIR / script)],
        input=json.dumps(payload) if not isinstance(payload, str) else payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(cwd),
        env={**os.environ, "PYTHONIOENCODING": "utf-8", **(env or {})},
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def make_repo(tmp_path, branch, artefactos=(), carpeta=None):
    """Crea un repositorio git temporal con `branch` y, si hay ticket, su carpeta de specs.

    `artefactos` es el subconjunto de `spec.md`, `plan.md`, `tasks.md` que existirán.
    """
    _git(["init", "-q", "-b", branch], tmp_path)
    number = re.match(r"^(\d{3})-", branch)
    if number or carpeta:
        feature = tmp_path / "specs" / (carpeta or f"{number.group(1)}-feature")
        feature.mkdir(parents=True)
        for name in artefactos:
            (feature / name).write_text("# artefacto de prueba\n", encoding="utf-8")
    return tmp_path


def payload(tool, cwd, **tool_input):
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": tool_input,
        "cwd": str(cwd),
    }


# ----------------------------------------------------------------------- datos sensibles


def _luhn_check_digit(partial: str) -> str:
    total = 0
    for index, char in enumerate(reversed(partial)):
        digit = int(char)
        if index % 2 == 0:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return str((10 - total % 10) % 10)


def luhn_valid(number: str) -> bool:
    digits = re.sub(r"\D", "", number)
    return _luhn_check_digit(digits[:-1]) == digits[-1]


def make_card(longitud=16, agrupada=False, valida=True, semilla=7):
    """Número con forma de tarjeta de `longitud` dígitos, con Luhn válido o no."""
    rng = random.Random(f"{semilla}-{longitud}")
    body = str(rng.randint(1, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(longitud - 2))
    check = _luhn_check_digit(body)
    if not valida:
        check = str((int(check) + 1) % 10)
    number = body + check
    if agrupada:
        return " ".join(number[i : i + 4] for i in range(0, len(number), 4))
    return number


def make_nit(con_puntos=True, semilla=11):
    rng = random.Random(semilla)
    digits = "".join(str(rng.randint(0, 9)) for _ in range(9))
    dv = str(rng.randint(0, 9))
    if con_puntos:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:]}-{dv}"
    return f"{digits}-{dv}"


def make_documento(etiqueta="cédula", digitos=8, semilla=13):
    rng = random.Random(semilla)
    number = str(rng.randint(1, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(digitos - 1))
    return f"{etiqueta} {number}"
