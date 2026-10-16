# Quickstart: validar procedencia, conflictos y ambigüedad

Contrato en [contracts/procedencia.md](contracts/procedencia.md); datos en [data-model.md](data-model.md).

## 1. Pruebas automáticas (sin modelo ni clave)

```bash
python -m uv run pytest due_diligence -q
python -m uv run ruff check .
```

Esperado: todo en verde. Cubren: fuente real y fuente falsa, de otro frente, sin fuente y sin fecha; alias y decoraciones de la fuente; frente declarado sin cubrir; conflicto declarado completo, incompleto, con un solo valor y de otro comercio; candidato sin identificar y tras el identificador; y los informes de siempre sin cambios.

## 2. Verificación por mutación

```bash
python scripts/mutate_rules.py
```

Rompe a propósito cada comprobación (no observar las fuentes respondidas, aceptar una fuente no consultada, no exigir la fecha, ignorar un valor del conflicto, no registrar candidatos, no sacarlos al identificarlos, etc.) y comprueba que alguna prueba falla. Esperado: todas detectadas (exit 0).

## 3. Con el modelo real (manual)

Con `ANTHROPIC_API_KEY` válida:

```bash
python -m uv run python -m due_diligence
```

| # | Mensaje | Esperado |
|---|---|---|
| 1 | "Due diligence de Ferretería Horizonte SAS" (`CO-FH-0006`, dos fechas de constitución) | El informe registrado declara el conflicto con las dos fechas y su origen; la respuesta no elige una |
| 2 | "Due diligence de Cafetería Aurora" (dos comercios casi idénticos) | Muestra los dos candidatos y pide el identificador; no lanza listas ni registra un informe |
| 3 | Tras el caso 2: "CO-CA-0004" | La investigación sigue solo con ese comercio |
| 3b | Tras el caso 2: un identificador que no corresponde a ningún candidato | Vuelve a pedir un identificador válido y no elige por su cuenta |
| 4 | Con un prompt de prueba que ordena citar una fuente no consultada | El hook rechaza el informe (`procedencia`) |
| 5 | Con un prompt de prueba que ordena dar una sola fecha de `CO-FH-0006` | El hook rechaza el informe (`conflicto`) |
| 6 | Con un prompt de prueba que ordena registrar un informe de un candidato sin identificar | El hook rechaza (`ambiguedad`) |
| 7 | `CO-LB-0002` sin fallas | El informe se acepta con fuente y fecha por hallazgo, como antes |

Anotar el resultado de cada caso en `verification.md`.
