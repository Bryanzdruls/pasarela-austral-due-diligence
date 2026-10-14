# Quickstart: validar el servidor de fuentes

## Prerrequisitos
- Python 3.12 y `uv` instalados.
- Dependencias: `uv sync`.

## Ejecutar las pruebas
```bash
uv run pytest mcp_server
uv run ruff check . && uv run ruff format --check .
```
Resultado esperado: todas las pruebas pasan y ruff no reporta cambios.

## Arrancar el servidor (stdio)
```bash
uv run python -m mcp_server
```
El proceso espera mensajes MCP por stdio; lo lanza el coordinador (ticket #2) o el inspector de MCP.

## Escenarios de validación

| # | Escenario | Cómo | Resultado esperado |
|---|---|---|---|
| 1 | Caso del enunciado | `consultar_registro_mercantil("CO-TV-0001")` y `consultar_riesgo_categoria("suplementos dietarios")` | 1 coincidencia; riesgo `alto` |
| 2 | Bajo riesgo sin hallazgos | Libros del Faro (`CO-LB-0002`): listas y noticias | `match=false`; sin menciones; riesgo `bajo` |
| 3 | Representante en listas | Persona del representante de `CO-DA-0003` en listas | `match=true` con lista y fecha |
| 4 | Nombres casi idénticos | `consultar_registro_mercantil("Cafetería Aurora")` | 2 coincidencias, `ambiguous=true` |
| 5 | Falla de noticias | `PASARELA_FAULTS=noticias` y `buscar_noticias("Tienda Verde")` | `ok=false`, `retryable=true`; otras fuentes responden |
| 6 | Fechas distintas | `consultar_registro_mercantil("CO-FH-0006")` | dos fuentes con fechas distintas y `conflicts` |
| 7 | Handoff incompleto | `escalar_a_cumplimiento` sin `causa` | `invalid_input` con `campos_faltantes` |

(El caso "listas sin identificación unívoca → bloqueado" lo demuestra el ticket #3, porque lo impone un hook del coordinador, no este servidor.)

Contrato completo en [contracts/tools.md](contracts/tools.md); datos en [data-model.md](data-model.md).
