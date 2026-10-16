"""La entrada de los hooks se lee como UTF-8 aunque la codificación local no lo sea (Windows)."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1]
PLUGIN_HOOK = HOOKS.parents[1] / "plugins" / "pasarela-revision" / "hooks" / "real_data_guard.py"
SCRIPTS = [HOOKS / "real_data_guard.py", PLUGIN_HOOK]


def run_raw(script, text):
    """Ejecuta el hook enviando JSON en UTF-8 crudo, sin forzar la codificación del subproceso."""
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    env["PYTHONUTF8"] = "0"  # codificación local: es lo que ocurre cuando lo lanza Claude Code
    body = json.dumps(
        {"tool_name": "Write", "tool_input": {"content": text}, "cwd": str(HOOKS)},
        ensure_ascii=False,
    ).encode("utf-8")
    proc = subprocess.run(
        [sys.executable, str(script)], input=body, capture_output=True, env=env, timeout=60
    )
    return proc.returncode, proc.stderr.decode("utf-8", errors="replace")


@pytest.mark.parametrize("script", SCRIPTS, ids=["proyecto", "plugin"])
def test_an_accented_document_label_is_still_blocked(script):
    code, err = run_raw(script, "Cédula 12345678")
    assert code == 2 and "documento" in err


@pytest.mark.parametrize("script", SCRIPTS, ids=["proyecto", "plugin"])
@pytest.mark.parametrize("text", ["Á Í Ú acentuadas y ñ en texto corriente", "comercio CO-TV-0001"])
def test_accented_ordinary_text_is_not_blocked(script, text):
    code, err = run_raw(script, text)
    assert code == 0, err
