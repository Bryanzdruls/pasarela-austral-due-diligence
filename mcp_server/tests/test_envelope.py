import pytest

from mcp_server.envelope import error, ok


def test_ok_separates_content_and_metadata():
    r = ok({"x": 1}, "registro_mercantil_ficticio")
    assert r["ok"] is True
    assert r["content"] == {"x": 1}
    assert r["metadata"]["source"] == "registro_mercantil_ficticio"
    assert r["metadata"]["fetched_at"]
    assert "source" not in r["content"]


def test_error_has_structured_fields():
    r = error("noticias_ficticias", "source_unavailable", retryable=True, partial={"a": 1})
    assert r == {
        "ok": False,
        "source": "noticias_ficticias",
        "error_code": "source_unavailable",
        "retryable": True,
        "partial": {"a": 1},
    }


def test_error_partial_defaults_to_empty():
    assert error("s", "invalid_input", retryable=False)["partial"] == {}


def test_error_rejects_unknown_code():
    with pytest.raises(ValueError):
        error("s", "boom", retryable=False)
