# Quickstart: validar el coordinador y los subagentes

## Prerrequisitos
- Python 3.12 y `uv` (`python -m uv ...` si `uv` no está en el PATH).
- `python -m uv sync`.
- Para la verificación con modelo real: `ANTHROPIC_API_KEY` definida como variable de entorno del proceso (no en el repositorio).

## 1. Pruebas automáticas (sin modelo ni API key)
```bash
python -m uv run pytest due_diligence mcp_server -q
python -m uv run ruff check .
```
Esperado: todo en verde. Cubren: herramientas por frente (SC-002), encargos expuestos y sin conversación (SC-003), orden de eventos con marcas de tiempo (SC-004), ciclo por `ResultMessage` y no por texto (SC-005), el hook de aislamiento, el coordinador restringido a `Agent`, la sesión multi-turno que reutiliza el mismo cliente (FR-013) y las instrucciones del prompt.

## 2. Matriz de verificación con modelo real (manual)
Con `ANTHROPIC_API_KEY` definida, abrir la conversación interactiva:
```bash
python -m uv run python -m due_diligence
```
Escribir cada mensaje; `salir` termina. Ejecutar y **anotar el resultado de cada caso**:

| # | Mensaje | Esperado |
|---|---|---|
| 1 | "Necesito el due diligence de Tienda Verde SAS, identificador CO-TV-0001. Quieren procesar ventas en línea de suplementos dietarios y estiman unos $80.000.000 mensuales. ¿Lo podemos habilitar esta semana?" | Tres `SubagentStarted` (registro, noticias, riesgo) antes de cualquier `SubagentFinished`; `listas_restrictivas` solo después de terminar el registro; informe con una sección por frente, "Datos aportados por el analista" y recomendación; `RunFinished` con `success` (SC-001, SC-004) |
| 2 | "¿Y qué dijeron las noticias?" (seguimiento) | Respuesta sin ningún `SubagentStarted` nuevo (SC-007) |
| 3 | "Ahora necesito el due diligence de Libros del Faro SAS, CO-LB-0002" | Investigación nueva; los `encargo` mostrados no contienen datos de Tienda Verde (SC-007, SC-003) |
| 4 | (conversación nueva) "Necesito un due diligence" | Pide el comercio o su identificador; ningún `SubagentStarted` (SC-006) |
| 5 | (conversación nueva) "Due diligence de Cafetería Aurora" | Comercio ambiguo: no inventa un comercio; el manejo completo de la ambigüedad es el ticket #5 |

Con `PASARELA_FAULTS=noticias` el frente de noticias falla; el tratamiento completo de esa falla es el ticket #4.

## 3. Aislamiento (inspección)
Revisar `due_diligence/agents.py`: cada `AgentDefinition` tiene una sola herramienta. `due_diligence/tests/test_guards.py` demuestra que el hook niega cualquier otra, y `test_coordinator.py` que el coordinador solo tiene `Agent`.

Contrato en [contracts/coordinator.md](contracts/coordinator.md); datos en [data-model.md](data-model.md).
