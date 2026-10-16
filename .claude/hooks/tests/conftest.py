"""Hace importables los scripts de los hooks (`.claude/hooks`) desde sus pruebas.

El directorio `.claude` no es un nombre de paquete válido, así que las pruebas importan los
módulos hermanos (`common`, `helpers`) añadiendo esta carpeta a `sys.path`.
"""

import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))
