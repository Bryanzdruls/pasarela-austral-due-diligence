"""Catálogo del repositorio y paridad del hook del plugin con el hook del proyecto."""

import importlib.util
import json
import random
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN_HOOK = ROOT / "plugins" / "pasarela-revision" / "hooks" / "real_data_guard.py"
HOOKS_DIR = ROOT / ".claude" / "hooks"
PROJECT_HOOK = HOOKS_DIR / "real_data_guard.py"


# --------------------------------------------------------------------------- catálogo


def test_the_catalog_lists_the_plugin_with_a_relative_source_that_exists():
    assert CATALOG.is_file(), "falta .claude-plugin/marketplace.json"
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    assert catalog["name"] == "pasarela-austral"
    assert catalog["owner"]["name"]
    entries = {entry["name"]: entry for entry in catalog["plugins"]}
    entry = entries["pasarela-revision"]
    assert entry["source"] == "./plugins/pasarela-revision"
    assert (ROOT / entry["source"] / ".claude-plugin" / "plugin.json").is_file()
    assert len(entry["description"]) > 20


def test_the_catalog_has_no_personal_data():
    text = CATALOG.read_text(encoding="utf-8")
    assert "@" not in text and "C:\\" not in text


# --------------------------------------------------------------------------- paridad


def _digits(rng, n):
    return "".join(str(rng.randint(0, 9)) for _ in range(n))


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


def sample_texts():
    """30 textos generados: sensibles y no sensibles, de todas las formas que reconoce el hook."""
    rng = random.Random(2026)
    texts = []
    for length in (13, 15, 16, 19, 16, 16):
        body = str(rng.randint(1, 9)) + _digits(rng, length - 2)
        number = body + _check_digit(body)
        texts.append(f"pago {number}")
        texts.append(f"pago {' '.join(number[i : i + 4] for i in range(0, len(number), 4))}")
    for _ in range(5):
        nine = _digits(rng, 9)
        texts.append(f"NIT {nine[:3]}.{nine[3:6]}.{nine[6:]}-{rng.randint(0, 9)}")
        texts.append(f"NIT {nine}-{rng.randint(0, 9)}")
    for label in ("cédula", "cc", "documento", "identificación"):
        texts.append(f"{label} {rng.randint(1, 9)}{_digits(rng, 7)}")
    texts += [
        "CO-TV-0001 y FICT-0007",
        "texto corriente",
        "hash 9b74c9897bac770ffc029102a200c5de",
        f"número inválido {_digits(rng, 16)}0",
    ]
    return texts


def _load_project_hook():
    sys.path.insert(0, str(HOOKS_DIR))
    try:
        spec = importlib.util.spec_from_file_location("project_real_data_guard", PROJECT_HOOK)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(HOOKS_DIR))


def _plugin_run(text):
    stdin = json.dumps({"tool_name": "Write", "tool_input": {"content": text}})
    proc = subprocess.run(
        [sys.executable, str(PLUGIN_HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    return proc.returncode, proc.stderr


def test_the_plugin_hook_decides_like_the_project_hook_on_generated_inputs():
    assert PLUGIN_HOOK.is_file(), "falta el hook del plugin"
    project = _load_project_hook()
    texts = sample_texts()
    assert len(texts) >= 30
    for text in texts:
        expected = bool(project.find_sensitive(text))
        code, err = _plugin_run(text)
        assert (code == 2) == expected, (text, code)
        if expected:
            first = project.find_sensitive(text)[0]
            assert project.mask(first[1]) in err, text  # enmascara igual que el del proyecto
            assert first[1] not in err or len(first[1]) <= 2


@pytest.mark.parametrize("pattern", [r"^import common", r"^from common"])
def test_the_plugin_hook_does_not_import_the_project_helpers(pattern):
    assert PLUGIN_HOOK.is_file()
    assert not re.search(pattern, PLUGIN_HOOK.read_text(encoding="utf-8"), re.M)
