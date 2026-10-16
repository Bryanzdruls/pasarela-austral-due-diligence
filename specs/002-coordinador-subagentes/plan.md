# Implementation Plan: Coordinador y subagentes de due diligence

**Branch**: `002-coordinador-subagentes` | **Date**: 2026-10-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-coordinador-subagentes/spec.md`

## Summary

Un coordinador construido con el Claude Agent SDK (Python) recibe la solicitud del analista y delega en cuatro subagentes definidos con `AgentDefinition`, cada uno restringido a la herramienta de su frente del servidor MCP del ticket #1. Los tres frentes independientes se lanzan en un mismo turno del coordinador (paralelo); el de listas se lanza después, porque necesita el identificador y el representante que devuelve el registro. El SDK ejecuta el ciclo agéntico internamente según la razón de parada del modelo; nuestro código solo consume los mensajes de cada turno hasta el resultado final y los traduce a eventos de dominio (para pruebas y para la interfaz del ticket #7). La conversación con el analista es **multi-turno**: una `DueDiligenceSession` envuelve un `ClaudeSDKClient` que conserva el contexto entre turnos, de modo que los seguimientos se responden con lo ya investigado.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: `claude-agent-sdk` (≥ 0.2.140; la última verificada es 0.2.166), `mcp_server` del ticket #1 como servidor MCP stdio

**Storage**: N/A (los informes los guarda el servidor MCP; este ticket no persiste nada)

**Testing**: pytest, con los tests junto al código (`due_diligence/**/tests/`). Sin llamar al modelo: se inyecta una fábrica de cliente falsa (con `query` y `receive_response`) que emite `AssistantMessage`/`ResultMessage`, y los hooks se prueban llamándolos directamente. Una verificación manual con modelo real queda en el quickstart (requiere `ANTHROPIC_API_KEY`)

**Target Platform**: Proceso local en Windows/Linux/macOS

**Project Type**: Librería de orquestación (paquete `due_diligence/`) consumida por la interfaz de chat (ticket #7)

**Performance Goals**: Los tres frentes independientes no se serializan (ver SC-004)

**Constraints**: Autenticación solo por `ANTHROPIC_API_KEY` en el entorno (nunca en el repositorio ni en `.env` versionado); el SDK no carga `.env` solo; sin `max_turns` como criterio de salida (FR-008)

**Scale/Scope**: 1 coordinador, 4 subagentes, 4 herramientas de consulta asignadas (las 2 de salida las usa el coordinador en los tickets #5/#6)

## Constitution Check

*GATE: pasa antes de la investigación y se reevaluó tras el diseño.*

| Principio | Cumple | Cómo |
|---|---|---|
| I. Reglas de negocio garantizadas | Parcial, con riesgo declarado | Las reglas 1-3 van en hooks en el ticket #3. Aquí solo se garantiza el aislamiento de herramientas (`tools` + hook `guards.py`). FR-007 (listas espera al registro y no corre sin comercio único) está redactado en la spec como **orientación**, no como garantía; la garantía es el hook del #3. El ticket #2 no se demuestra ante terceros hasta fusionar el #3 (spec, FR-007 y Assumptions) |
| II. Datos solo ficticios | Sí | Las fuentes son las del ticket #1; los ejemplos de pruebas usan `CO-TV-0001` y datos `FICT-*` |
| III. Hooks vs instrucciones | Sí | Aislamiento de herramientas: configuración (`tools`) + hook de respaldo; orientación del coordinador: prompt |
| IV. Spec primero | Sí | spec → plan → tasks antes de código |
| V. Agentes con contexto explícito y herramientas mínimas | Sí | Encargo explícito por subagente, `tools` por frente, resultado con contenido/metadatos separados, ciclo por razón de parada |
| VI. Pruebas junto al código | Sí | `due_diligence/**/tests/` |
| VII. Trazabilidad | Sí | Issue #2, rama y PR que lo cierra |

Sin violaciones; el riesgo del principio I está declarado y tiene dueño (#3).

## Project Structure

### Documentation (this feature)

```text
specs/002-coordinador-subagentes/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── coordinator.md
├── checklists/requirements.md
└── tasks.md             # lo genera /speckit-tasks
```

### Source Code (repository root)

```text
due_diligence/
├── __init__.py
├── agents.py            # AgentDefinition de los 4 subagentes: prompt, tools, modelo
├── prompts.py           # prompt del coordinador y de cada subagente (español)
├── options.py           # construye ClaudeAgentOptions: agents, mcp_servers, hooks, auth
├── guards.py            # hook PreToolUse: niega herramientas ajenas al subagente (por agent_type)
├── events.py            # traduce mensajes del SDK a eventos de dominio y a FrontResult
├── coordinator.py       # DueDiligenceSession: cliente multi-turno; ask(text) consume mensajes hasta ResultMessage
└── tests/
    ├── fakes.py         # cliente falso: query / receive_response con secuencias de AssistantMessage / ResultMessage
    ├── test_agents.py
    ├── test_guards.py
    ├── test_events.py
    └── test_coordinator.py
mcp_server/              # ticket #1, sin cambios
```

**Structure Decision**: Un paquete nuevo `due_diligence/` en la raíz, separado de `mcp_server/` para que las fuentes sigan siendo un servicio independiente que el coordinador consume solo por stdio. `options.py` concentra la configuración del SDK para que `coordinator.py` quede como un consumidor de mensajes sin decisiones. Los hooks de reglas de negocio del ticket #3 vivirán en `due_diligence/hooks.py` y se añadirán a `options.py`.

## Complexity Tracking

Sin violaciones que justificar.
