"""`docs/CASOS.md` describe los siete casos y cada prueba que cita existe de verdad."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = (ROOT / "docs" / "CASOS.md").read_text(encoding="utf-8")
PRUEBAS = (ROOT / "due_diligence" / "tests" / "test_casos_obligatorios.py").read_text(
    encoding="utf-8"
)


def test_the_document_lists_the_seven_cases_in_order():
    filas = re.findall(r"^\| ([1-7]) \| ", DOC, flags=re.MULTILINE)
    assert filas == ["1", "2", "3", "4", "5", "6", "7"]


def test_every_test_the_document_names_exists():
    citadas = re.findall(r"`(test_case_\d_[a-z0-9_]+)`", DOC)
    assert len(citadas) >= 7
    existentes = set(re.findall(r"^async def (test_case_\d_[a-z0-9_]+)\(", PRUEBAS, re.MULTILINE))
    assert set(citadas) <= existentes, set(citadas) - existentes


def test_every_case_test_is_named_in_the_document():
    existentes = set(re.findall(r"^async def (test_case_\d_[a-z0-9_]+)\(", PRUEBAS, re.MULTILINE))
    citadas = set(re.findall(r"`(test_case_\d_[a-z0-9_]+)`", DOC))
    assert existentes == citadas, existentes ^ citadas


def test_the_document_gives_both_commands():
    assert "pytest due_diligence/tests/test_casos_obligatorios.py" in DOC
    assert "scripts/run_casos.py" in DOC and "ANTHROPIC_API_KEY" in DOC
