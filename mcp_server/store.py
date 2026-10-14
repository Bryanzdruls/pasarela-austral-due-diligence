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


def name_matches(query: str, name: str) -> bool:
    """Coincide si todas las palabras de la consulta (normalizadas) están completas en el nombre."""
    wanted = set(normalize(query).split())
    return bool(wanted) and wanted <= set(normalize(name).split())


def require_text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("el texto de la consulta no puede estar vacío")
    return value.strip()


def runtime_dir() -> Path:
    configured = os.environ.get("PASARELA_RUNTIME_DIR")
    return Path(configured) if configured else DEFAULT_RUNTIME_DIR


def save_record(prefix: str, record: dict[str, Any]) -> str:
    """Guarda un registro con id consecutivo; nunca pisa un archivo existente."""
    directory = runtime_dir()
    directory.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(rf"{re.escape(prefix)}-(\d+)\.json")
    used = [int(m.group(1)) for f in directory.iterdir() if (m := pattern.fullmatch(f.name))]
    number = max(used, default=0) + 1
    while True:
        record_id = f"{prefix}-{number:04d}"
        payload = json.dumps({"id": record_id, **record}, ensure_ascii=False, indent=2)
        try:
            with (directory / f"{record_id}.json").open("x", encoding="utf-8") as f:
                f.write(payload)
        except FileExistsError:
            number += 1
            continue
        return record_id
