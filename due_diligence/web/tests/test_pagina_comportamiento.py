"""La lógica real de la página, ejecutada con un navegador simulado (necesita Node).

El defecto que motivó estas pruebas: al recargar, la página vieja veía cerrarse su flujo de
eventos, creía que la conversación había desaparecido, borraba la guardada y creaba una nueva; el
historial se perdía en cada recarga (FR-007).
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

HARNES = Path(__file__).with_name("harness_pagina.js")
VIEJO = "a" * 32
NUEVO = "b" * 32

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="se necesita Node")


def correr(escenario):
    proc = subprocess.run(
        ["node", str(HARNES), escenario],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_the_harness_runs_the_real_page_script_and_connects_to_the_saved_conversation():
    salida = correr("cargar")
    assert salida["flujosAlCargar"] == [f"/api/conversaciones/{VIEJO}/eventos"]
    assert salida["cidAlCargar"] == VIEJO
    assert salida["creacionesAlCargar"] == 0  # reutiliza la conversación, no crea otra


def test_a_page_without_a_saved_conversation_creates_one_and_remembers_it():
    salida = correr("sin_guardada")
    assert salida["creacionesAlCargar"] == 1
    assert salida["cidAlFinal"] == NUEVO
    assert salida["flujosAlFinal"] == [f"/api/conversaciones/{NUEVO}/eventos"]


def test_unloading_the_page_does_not_forget_the_conversation():
    """Reproduce el defecto: el cierre del flujo al descargar la página no es un 404."""
    salida = correr("descarga")
    assert salida["cidAlFinal"] == VIEJO, "la recarga borró la conversación guardada"
    assert salida["creacionesAlFinal"] == 0, "la recarga creó una conversación nueva"


def test_a_page_restored_from_the_back_forward_cache_reconnects_to_its_conversation():
    salida = correr("restaurada")
    assert salida["cidAlFinal"] == VIEJO and salida["creacionesAlFinal"] == 0
    assert salida["flujosAlFinal"] == [f"/api/conversaciones/{VIEJO}/eventos"] * 2


def test_a_conversation_the_server_no_longer_knows_gets_a_new_one():
    """El camino legítimo se conserva: tras un 404 (el servidor se reinició) se empieza otra."""
    salida = correr("desconocida")
    assert salida["creacionesAlFinal"] == 1
    assert salida["cidAlFinal"] == NUEVO
    assert salida["flujosAlFinal"][-1] == f"/api/conversaciones/{NUEVO}/eventos"
