# Quickstart: validar el ecosistema de Claude Code

## Prerrequisitos
- Python 3.12 y `uv` (`python -m uv ...` si `uv` no está en el PATH).
- `python -m uv sync`.

## 1. Pruebas automáticas (sin modelo)
```bash
python -m uv run pytest -q
python -m uv run ruff check .
```
Cubren los cuatro hooks (ejecutándolos como subproceso con JSON por stdin) y la verificación de mínimos.

## 2. Verificación de mínimos
```bash
python scripts/verify_ecosystem.py
```
Esperado: `OK` en cada mínimo del enunciado que corresponde a este ticket y código de salida 0. El plugin lo comprueba el ticket #10.

## 3. Cada hook a mano
Se ejecuta el script con un JSON por stdin y se mira el código de salida (`$LASTEXITCODE` en PowerShell):

| # | Escenario | Esperado |
|---|---|---|
| 1 | `Write` a `mcp_server/x.py` en una rama sin ticket | código 2 y mensaje de spec ausente |
| 2 | `Write` a `mcp_server/x.py` en una rama con spec, plan y tareas | código 0 |
| 3 | `Write` con un número con forma de tarjeta válido (construido en el momento) | código 2 |
| 4 | `Write` con `FICT-0001` y `CO-TV-0001` | código 0 |
| 5 | `Read` de `.env` | código 2 |
| 6 | `Read` de `.env.example` | código 0 |
| 7 | `Bash` con `cat .env` | código 2 |
| 8 | `PostToolUse` de un `.py` mal formateado | el archivo queda formateado; código 0 |
| 9 | `Bash` con `echo x > mcp_server/y.py` sin especificación | código 2 |
| 10 | `Bash` con `pytest -q` | código 0 |

Las pruebas automáticas de la sección 1 reproducen exactamente estos casos.

## 4. Dentro de Claude Code
Abrir el repositorio, aceptar la confianza de proyecto y comprobar con `/hooks` que aparecen los cuatro hooks y con `/memory` que se cargan `CLAUDE.md` y las reglas. Lanzar `/verificar-ecosistema` y `/revisar-cumplimiento <ticket>`.

Contrato en [contracts/hooks.md](contracts/hooks.md); decisiones en [research.md](research.md).
