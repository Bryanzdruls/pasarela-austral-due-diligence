# Implementation Plan: Interfaz de chat con eventos visibles

**Branch**: `007-chat-eventos-visibles` | **Date**: 2026-10-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-chat-eventos-visibles/spec.md`

## Summary

Una aplicación web mínima sobre el coordinador existente; no cambia el comportamiento del sistema (FR-011).

- **Eventos nuevos** (`due_diligence/events.py`): `CallBlocked`, `ReportRegistered` y `Escalated`, junto a los de #2 (delegación, resultado de frente, texto, fin).
- **Observaciones del sistema**: lo que no viaja en el flujo de mensajes del SDK se recoge del propio sistema. Los bloqueos, con una llamada opcional `on_decision` en `make_pre_tool_use`/`build_options` que recibe la **misma decisión** del hook de reglas (con su regla y motivo); los registros, con un hook `PostToolUse` observador que lee el sobre del servidor y solo anuncia lo que el servidor confirmó (`ok: true`).
- **Vista** (`due_diligence/web/vista.py`): una función pura que convierte cada evento en una tarjeta en lenguaje llano (tipo, título, detalle, hora). Es lo que la prueba "se entiende sin conocer el código" comprueba.
- **Conversación** (`web/conversacion.py`): una sesión con su historial de eventos, suscriptores y un turno a la vez; reutiliza `DueDiligenceSession`.
- **Aplicación** (`web/app.py`, Starlette + `sse-starlette`): `GET /` (página), `POST /api/conversaciones`, `POST /api/conversaciones/{id}/mensajes`, `GET /api/conversaciones/{id}/eventos` (SSE con reconstrucción del historial) y `GET /api/estado`.
- **Página** (`web/static/index.html`): HTML y JavaScript sin dependencias; el texto se inserta con `textContent`.
- **Arranque** (`python -m due_diligence.web`): `uvicorn` solo en `127.0.0.1`.

Decisiones y alternativas en [research.md](research.md); contrato en [contracts/web.md](contracts/web.md).

## Technical Context

**Language/Version**: Python 3.12 (y JavaScript sin librerías en la página).

**Primary Dependencies**: `starlette`, `uvicorn` y `sse-starlette` (ya instaladas con `mcp`; se declaran en `pyproject.toml` porque la interfaz depende de ellas) y `httpx` (solo pruebas, `dev`).

**Storage**: historial en memoria por proceso; nada persistente.

**Testing**: `pytest` con el cliente falso del SDK y el `TestClient` de Starlette. Ninguna prueba llama al modelo. La verificación con el modelo real (los siete casos en la interfaz) queda documentada en `verification.md`.

**Target Platform**: Windows y Linux, navegador moderno.

**Project Type**: aplicación web local sobre un paquete Python.

**Constraints**: solo `127.0.0.1`; texto siempre escapado; un turno a la vez; sin cambiar reglas ni hooks salvo la llamada opcional `on_decision`.

**Scale/Scope**: 1 módulo de eventos ampliado, 4 módulos nuevos, 1 página, 1 comando, pruebas, documento.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Cómo se cumple |
|---|---|---|
| I. Reglas de negocio garantizadas | Cumple | La interfaz no decide nada: muestra lo que deciden los hooks |
| II. Datos ficticios | Cumple | Solo datos del servidor ficticio |
| III. Hooks vs instrucciones | Cumple | Los bloqueos se muestran desde la decisión del hook, no desde el texto del modelo |
| IV. Spec primero | Cumple | Spec, plan y tareas antes del código |
| V. Agentes con herramientas mínimas | Cumple | La interfaz no añade herramientas ni cambia el reparto |
| VI. Pruebas junto al código | Cumple | `due_diligence/web/tests/` y `due_diligence/tests/`; sin modelo |
| VII. Trazabilidad en GitHub | Cumple | Ticket movido por el flujo del #10 |
| VIII. Ecosistema primero | Cumple | #9 y #10 fusionados |

Sin violaciones. Re-evaluación tras el diseño: sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/007-chat-eventos-visibles/
├── plan.md
├── research.md
├── quickstart.md
├── contracts/web.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
due_diligence/
├── events.py                # cambia: CallBlocked, ReportRegistered, Escalated
├── rule_hooks.py            # cambia: make_pre_tool_use(book, on_decision=None)
├── options.py               # cambia: build_options(book, on_decision=None)
├── __main__.py              # cambia: la consola también renderiza los eventos nuevos
└── web/
    ├── __init__.py
    ├── __main__.py          # python -m due_diligence.web
    ├── vista.py             # evento -> tarjeta en lenguaje llano
    ├── observadores.py      # recoge bloqueos, informes y escalamientos del sistema
    ├── conversacion.py      # sesión, historial, suscriptores y turno único
    ├── app.py               # Starlette + SSE
    ├── static/index.html    # la página
    └── tests/               # pruebas de la interfaz (sin modelo)
```

**Structure Decision**: la lógica de la interfaz vive en su propio subpaquete, apoyada en `DueDiligenceSession`; los únicos cambios al sistema son los eventos nuevos y la llamada opcional `on_decision`.

## Complexity Tracking

Sin violaciones que justificar.
