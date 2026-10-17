"""Ejecuta los siete casos con el modelo real: `python scripts/run_casos.py [--caso N]`.

Envuelve `due_diligence.casos_reales` (ver `docs/CASOS.md`). Sin `ANTHROPIC_API_KEY` termina con un
mensaje claro, sin llamar al modelo.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from due_diligence.casos_reales import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
