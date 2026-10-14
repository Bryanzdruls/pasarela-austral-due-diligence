"""Carga de datos ficticios, normalización de texto y persistencia de registros."""

import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_RUNTIME_DIR = Path(__file__).parent.parent / "data" / "runtime"
_SUFFIXES = {"sas", "sa", "ltda"}


def load(name: str) -> list[dict[str, Any]]:
    with (DATA_DIR / f"{name}.json").open(encoding="utf-8") as f:
        return json.load(f)


def normalize(text: str) -> str:
    """Minúsculas, sin tildes ni puntuación y sin sufijo societario (SAS, S.A.S., ...)."""
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(c for c in decomposed if not unicodedata.combining(c)).lower()
    plain = plain.replace(".", "")
    tokens = re.sub(r"[^a-z0-9]+", " ", plain).split()
    if tokens and tokens[-1] in _SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def require_text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("el texto de la consulta no puede estar vacío")
    return value.strip()


def runtime_dir() -> Path:
    configured = os.environ.get("PASARELA_RUNTIME_DIR")
    return Path(configured) if configured else DEFAULT_RUNTIME_DIR


def save_record(prefix: str, record: dict[str, Any]) -> str:
    directory = runtime_dir()
    directory.mkdir(parents=True, exist_ok=True)
    next_number = len(list(directory.glob(f"{prefix}-*.json"))) + 1
    record_id = f"{prefix}-{next_number:04d}"
    payload = {"id": record_id, **record}
    (directory / f"{record_id}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return record_id
