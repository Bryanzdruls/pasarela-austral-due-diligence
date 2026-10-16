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
Esperado: todo en verde. Cubren: herramientas por frente (SC-002), encargos sin conversación (SC-003), ciclo por `ResultMessage` y no por texto (SC-005), orden de eventos con los tres frentes independientes antes de cualquier resultado y listas después del registro (SC-004), solicitud sin comercio sin consultas (SC-006), y el hook de aislamiento.

## 2. Verificación con modelo real (manual)
Con `ANTHROPIC_API_KEY` definida:
```bash
python -m uv run python -m due_diligence "Necesito el due diligence de Tienda Verde SAS, identificador CO-TV-0001. Quieren procesar ventas en línea de suplementos dietarios y estiman unos $80.000.000 mensuales. ¿Lo podemos habilitar esta semana?"
```
Esperado en el flujo de eventos impreso:
1. Tres `SubagentStarted` seguidos (registro_mercantil, noticias, riesgo_categoria) antes de cualquier `SubagentFinished`.
2. `SubagentStarted(listas_restrictivas)` solo después de `SubagentFinished(registro_mercantil)`.
3. Texto final con una sección por frente, "Datos aportados por el analista" y una recomendación.
4. `RunFinished` con `subtype=success`.

Con `PASARELA_FAULTS=noticias` el frente de noticias falla; el tratamiento completo de esa falla es el ticket #4.

## 3. Aislamiento (inspección)
Revisar `due_diligence/agents.py`: cada `AgentDefinition` tiene una sola herramienta. `due_diligence/tests/test_guards.py` demuestra que el hook niega cualquier otra.

Contrato en [contracts/coordinator.md](contracts/coordinator.md); datos en [data-model.md](data-model.md).
