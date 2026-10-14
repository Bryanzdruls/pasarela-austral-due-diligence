import json

import pytest

from mcp_server import store


def test_normalize_ignores_case_accents_punctuation_and_suffix():
    assert store.normalize("Cafetería Aurora S.A.S.") == "cafeteria aurora"
    assert store.normalize("  CAFETERIA   aurora SAS ") == "cafeteria aurora"
    assert store.normalize("Tienda Verde SAS") == "tienda verde"


def test_require_text_rejects_blank():
    with pytest.raises(ValueError):
        store.require_text("   ")
    with pytest.raises(ValueError):
        store.require_text(None)
    assert store.require_text(" hola ") == "hola"


def test_save_record_writes_json_with_sequential_ids(tmp_path, monkeypatch):
    monkeypatch.setenv("PASARELA_RUNTIME_DIR", str(tmp_path))
    first = store.save_record("INF", {"a": 1})
    second = store.save_record("INF", {"a": 2})
    assert (first, second) == ("INF-0001", "INF-0002")
    saved = json.loads((tmp_path / "INF-0001.json").read_text(encoding="utf-8"))
    assert saved["id"] == "INF-0001" and saved["a"] == 1
    assert store.save_record("ESC", {}) == "ESC-0001"
