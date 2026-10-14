# Implementation Plan: Servidor de fuentes ficticias de la pasarela

**Branch**: `001-servidor-mcp-datos-ficticios` | **Date**: 2026-10-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-servidor-mcp-datos-ficticios/spec.md`

## Summary

Servidor MCP propio (paquete `mcp_server/`) que expone seis herramientas sobre datos ficticios en archivos JSON. Cada herramienta devuelve un sobre `{ok:true, content, metadata:{source, fetched_at}}` o un error estructurado `{ok:false, source, error_code, retryable, partial}`. Las fallas se inyectan con la variable de entorno `PASARELA_FAULTS`. El servidor solo informa: ninguna regla de decisión vive aquí (ticket #3).

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: `mcp` (SDK oficial, `FastMCP`), `pydantic` (validación de entradas, ya incluida por `mcp`)

**Storage**: Archivos JSON de solo lectura en `mcp_server/data/`; informes y escalamientos escritos como un JSON por registro en `PASARELA_RUNTIME_DIR` (por defecto `data/runtime/`, ignorado por git)

**Testing**: pytest, con los tests junto al código (`mcp_server/**/tests/`); `ruff` para formato y lint; gestor `uv`

**Target Platform**: Proceso local por stdio, lanzado por el Agent SDK (Windows/Linux/macOS)

**Project Type**: Librería/servicio local (servidor MCP por stdio)

**Performance Goals**: N/A — datos en memoria cargados al arrancar; respuesta de cada herramienta imperceptible

**Constraints**: Sin red, sin base de datos, sin credenciales; todos los datos con prefijo ficticio; respuestas deterministas

**Scale/Scope**: ~6 comercios, ~8 personas, ~6 noticias, ~4 entradas en listas, 5 categorías

## Constitution Check

*GATE: pasa antes de la investigación y se reevaluó tras el diseño.*

| Principio | Cumple | Cómo |
|---|---|---|
| I. Reglas de negocio garantizadas | Sí | Este servidor no decide (FR-013); las reglas 1-3 las aplican hooks del SDK en el ticket #3. Las reglas 4 y 5 se apoyan aquí en metadatos de fuente y errores estructurados |
| II. Datos solo ficticios | Sí | Identificadores `CO-XX-000N`, documentos `FICT-000N`, nombres inventados; sin credenciales; prueba automática que escanea `data/` |
| III. Hooks vs instrucciones | Sí | Las descripciones de herramientas orientan; nada obligatorio depende de ellas |
| IV. Spec primero | Sí | spec.md → plan.md → tasks.md antes de código |
| V. Agentes con contexto explícito y errores estructurados | Sí | Sobre contenido/metadatos y error `{retryable, partial}` |
| VI. Pruebas junto al código | Sí | `mcp_server/**/tests/` |
| VII. Trazabilidad | Sí | Issue #1, rama y PR que lo cierra |

Sin violaciones; no se requiere seguimiento de complejidad.

## Project Structure

### Documentation (this feature)

```text
specs/001-servidor-mcp-datos-ficticios/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── tools.md
├── checklists/requirements.md
└── tasks.md             # lo genera /speckit-tasks
```

### Source Code (repository root)

```text
pyproject.toml
mcp_server/
├── __init__.py
├── server.py            # FastMCP: registra las 6 herramientas; entrada `python -m mcp_server`
├── __main__.py
├── envelope.py          # ok(...) y error(...): sobre y error estructurado
├── faults.py            # lee PASARELA_FAULTS; guard por fuente
├── store.py             # carga JSON, búsqueda normalizada, escritura de runtime
├── tools/
│   ├── registro.py      # consultar_registro_mercantil
│   ├── listas.py        # consultar_listas_restrictivas
│   ├── noticias.py      # buscar_noticias
│   ├── riesgo.py        # consultar_riesgo_categoria
│   ├── informes.py      # registrar_informe, escalar_a_cumplimiento
│   └── tests/
├── data/
│   ├── comercios.json
│   ├── personas.json
│   ├── listas_restrictivas.json
│   ├── noticias.json
│   └── categorias.json
└── tests/               # sobre, fallas, datos ficticios, descripciones
data/runtime/            # ignorado por git
```

**Structure Decision**: Un solo paquete `mcp_server/` en la raíz. Cada herramienta en su módulo para mantener el contrato visible y testeable por separado; el sobre y las fallas se comparten desde `envelope.py` y `faults.py`. El coordinador y los subagentes (ticket #2) vivirán en otro paquete y solo consumirán el servidor por stdio.

## Complexity Tracking

Sin violaciones que justificar.
