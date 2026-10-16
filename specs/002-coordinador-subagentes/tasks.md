---
description: "Tareas del coordinador y subagentes de due diligence"
---

# Tasks: Coordinador y subagentes de due diligence

**Input**: `specs/002-coordinador-subagentes/` (plan.md, spec.md, research.md, data-model.md, contracts/coordinator.md, quickstart.md)

**Prerequisites**: plan.md, spec.md; servidor MCP del ticket #1 fusionado.

**Tests**: Incluidos (constitución VI). Orden en cada historia: pruebas primero, ver que fallan, luego implementar. Ninguna prueba llama al modelo real: usan la `query` falsa de `due_diligence/tests/fakes.py` o llaman a los hooks directamente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencia pendiente)
- **[Story]**: US1 informe sintetizado · US2 aislamiento · US3 paralelismo y dependencia · US4 ciclo por razón de parada

## Phase 1: Setup

- [ ] T001 Añadir la dependencia `claude-agent-sdk>=0.2.140` a `pyproject.toml`, añadir `due_diligence` a `testpaths` de pytest y ejecutar `python -m uv sync`
- [ ] T002 [P] Crear `due_diligence/__init__.py` y `due_diligence/tests/__init__.py`
- [ ] T003 [P] Añadir `ANTHROPIC_API_KEY=` (sin valor) a `.env.example`; comprobar que `.gitignore` ya ignora `.env` y `.env.*`

## Phase 2: Foundational (bloquea todas las historias)

- [ ] T004 Definir en `due_diligence/events.py` los tipos de dominio de `data-model.md`: enumeración `FrontName` (`registro_mercantil`, `listas_restrictivas`, `noticias`, `riesgo_categoria`); `FrontResult` con `frente`, `contenido`, `metadatos` (`{fuente, fecha}`, obligatorios) y `estado` ∈ `completo` | `no_estructurado` | `no_completado`; eventos `SubagentStarted(frente, tool_use_id)`, `SubagentFinished(frente, result)`, `CoordinatorText(text)`, `RunFinished(subtype, stop_reason, terminal_reason)`
- [ ] T005 [P] Crear `due_diligence/tests/fakes.py`: constructores de mensajes del SDK (`AssistantMessage` con `TextBlock`/`ToolUseBlock`, `UserMessage` con `ToolResultBlock`, `ResultMessage`) y `fake_query(messages)` que devuelve un iterador asíncrono; inspeccionar antes las firmas reales de las dataclasses de `claude_agent_sdk`
- [ ] T006 Crear `due_diligence/agents.py` con `FRONT_TOOLS` (cada frente → su única herramienta `mcp__pasarela-fuentes__...`, ver tabla de `data-model.md`) y `build_agents()` que devuelve las cuatro `AgentDefinition` con `description` y `tools`; el `prompt` de cada una se completa en T014
- [ ] T007 Crear `due_diligence/options.py` con `build_options()`: `agents=build_agents()`, `allowed_tools=["Agent"]`, `mcp_servers={"pasarela-fuentes": {command: sys.executable, args: ["-m","mcp_server"], env con PASARELA_FAULTS y PASARELA_RUNTIME_DIR si existen}}`, `setting_sources=[]`; sin `max_turns`; el hook de aislamiento se añade en T016

**Checkpoint**: tipos, falsos y configuración base listos.

## Phase 3: User Story 1 — Informe sintetizado (P1) 🎯 MVP

**Goal**: solicitud del analista → coordinador delega en los cuatro frentes → informe con recomendación.

**Independent Test**: con una `query` falsa que reproduce una investigación completa, `run_due_diligence` emite eventos y termina con `RunFinished`; el prompt del coordinador contiene las instrucciones de FR-001 a FR-011.

- [ ] T008 [US1] Tests en `due_diligence/tests/test_prompts.py`: el prompt del coordinador menciona los cuatro frentes; pide el comercio o su identificador si falta y no investigar (FR-010); exige una sección por frente, una sección "Datos aportados por el analista" y una recomendación (FR-009, FR-011); indica iniciar cada investigación sin datos de comercios anteriores (FR-012); indica pasar a cada subagente solo el encargo mínimo (FR-004)
- [ ] T009 [US1] Crear `due_diligence/prompts.py` con `COORDINATOR_PROMPT` (español) cumpliendo T008, y que indique lanzar `registro_mercantil`, `noticias` y `riesgo_categoria` en un mismo turno y `listas_restrictivas` solo después con el identificador y el representante del registro
- [ ] T010 [US1] Tests en `due_diligence/tests/test_coordinator.py`: con `fake_query` de una investigación completa se emiten `CoordinatorText` y, al final y solo una vez, `RunFinished`; `build_options()` no define `max_turns`, tiene `allowed_tools == ["Agent"]` y `setting_sources == []`
- [ ] T011 [US1] Implementar `due_diligence/coordinator.py`: `run_due_diligence(request, query_fn=claude_agent_sdk.query, options=None)` que consume los mensajes con `async for`, los traduce con `events.py` y emite eventos de dominio; termina al agotarse el flujo tras `ResultMessage`
- [ ] T012 [US1] Crear `due_diligence/__main__.py`: `python -m due_diligence "<solicitud>"` ejecuta `run_due_diligence` e imprime los eventos legibles; si falta `ANTHROPIC_API_KEY` en el entorno, termina con un mensaje claro sin intentar llamar al modelo

## Phase 4: User Story 2 — Cada subagente ve solo lo suyo (P1)

**Goal**: herramientas y contexto mínimos por frente; resultados con contenido y metadatos separados.

**Independent Test**: cada `AgentDefinition` tiene exactamente una herramienta; el hook niega cualquier otra; una respuesta de subagente mal formada se marca `no_estructurado`.

- [ ] T013 [US2] Tests en `due_diligence/tests/test_agents.py`: hay exactamente cuatro agentes con los nombres de `FrontName`; cada uno tiene en `tools` exactamente la herramienta de `FRONT_TOOLS` y ninguna más (SC-002); `description` no vacía; el `prompt` exige responder con JSON `{contenido, metadatos:{fuente, fecha}}` (FR-005) y el de listas indica usar identificadores
- [ ] T014 [US2] Completar los `prompt` de los cuatro subagentes en `due_diligence/prompts.py` (registro: devolver todas las coincidencias sin elegir; noticias: una mención no es coincidencia en listas; riesgo: informar `sin_clasificar` sin asumir; listas: verificar comercio y representante por identificador) y usarlos en `due_diligence/agents.py`
- [ ] T015 [P] [US2] Tests en `due_diligence/tests/test_guards.py` llamando al hook directamente: dentro de cada subagente se permite su herramienta y se niega cualquier otra de `mcp__pasarela-fuentes__*`; sin `agent_type` (coordinador) se permite `Agent`/`Task` y se niega cualquier herramienta de fuentes; el motivo de la denegación es legible; una herramienta sin relación (p. ej. de otro servidor) no se toca
- [ ] T016 [US2] Implementar `due_diligence/guards.py` con `tool_guard(input_data, tool_use_id, context)` según `contracts/coordinator.md` y registrarlo como hook `PreToolUse` en `due_diligence/options.py`
- [ ] T017 [P] [US2] Tests en `due_diligence/tests/test_events.py`: una respuesta de subagente con JSON válido → `FrontResult(estado="completo")` con contenido y metadatos separados; JSON inválido o sin `metadatos.fuente`/`fecha` → `estado="no_estructurado"` (nunca "completo")
- [ ] T018 [US2] Implementar en `due_diligence/events.py` la traducción de mensajes del SDK a eventos de dominio y el parseo a `FrontResult`: detectar bloques `ToolUseBlock` con `name` en (`Agent`, `Task`) → `SubagentStarted` (frente desde `input["subagent_type"]`), emparejar el `ToolResultBlock` por `tool_use_id` → `SubagentFinished`, texto del coordinador → `CoordinatorText` (ignorar mensajes con `parent_tool_use_id`), `ResultMessage` → `RunFinished`

## Phase 5: User Story 3 — Paralelo y dependencia (P2)

**Goal**: registro, noticias y riesgo arrancan juntos; listas después del registro.

**Independent Test**: con un flujo falso donde los tres `Agent` llegan en un mismo `AssistantMessage`, los tres `SubagentStarted` salen antes de cualquier `SubagentFinished`; `listas_restrictivas` arranca después de `SubagentFinished(registro_mercantil)`.

- [ ] T019 [US3] Tests en `due_diligence/tests/test_events.py`: tres `ToolUseBlock` de `Agent` en un mismo mensaje → tres `SubagentStarted` consecutivos antes de cualquier `SubagentFinished` (SC-004); resultados llegando en orden distinto se emparejan por `tool_use_id`; el flujo falso que lanza listas antes de terminar el registro se detecta (función `dependency_violations(events)` devuelve el hallazgo)
- [ ] T020 [US3] Implementar en `due_diligence/events.py` el emparejamiento por `tool_use_id` de varias llamadas concurrentes y la función `dependency_violations(events)` que reporta si `listas_restrictivas` inició antes de que `registro_mercantil` terminara; añadir una prueba en `due_diligence/tests/test_coordinator.py` de que `run_due_diligence` emite los eventos en el orden esperado para el flujo falso completo

## Phase 6: User Story 4 — El ciclo termina por razón de parada (P2)

**Goal**: ni contador de iteraciones ni lectura de texto controlan el ciclo.

**Independent Test**: un flujo falso con el texto "terminado" en medio no corta el ciclo; el ciclo acaba solo en `ResultMessage`; `RunFinished` conserva `subtype`, `stop_reason` y `terminal_reason`.

- [ ] T021 [US4] Tests en `due_diligence/tests/test_coordinator.py`: un `AssistantMessage` con texto "listo, terminado" seguido de más mensajes y un `ResultMessage` → se procesan todos y `RunFinished` es el último (SC-005); un `ResultMessage` con `subtype="error_max_turns"` se refleja en `RunFinished.subtype` sin lanzar fuera; dos ejecuciones con distinta longitud de flujo terminan ambas sin tope de iteraciones; una prueba que lee el código fuente de `due_diligence/coordinator.py` y `due_diligence/options.py` y comprueba que no contienen `max_turns`
- [ ] T022 [US4] Ajustar `due_diligence/coordinator.py` si alguna prueba de T021 falla: la salida del ciclo depende solo del fin del flujo tras `ResultMessage`; nunca de `TextBlock`, nunca de un contador; registrar `stop_reason` en `RunFinished`

## Phase 7: Polish y cierre

- [ ] T023 Ejecutar `python -m uv run pytest due_diligence mcp_server -q` y `python -m uv run ruff check . && python -m uv run ruff format --check .`; todo en verde
- [ ] T024 Verificación manual con modelo real (requiere `ANTHROPIC_API_KEY`): ejecutar el comando del `quickstart.md` con la solicitud de Tienda Verde SAS; anotar si los tres `SubagentStarted` salen antes de cualquier `SubagentFinished`, si `listas_restrictivas` espera al registro y si cada subagente solo usó su herramienta; si algún comportamiento difiere, ajustar `due_diligence/prompts.py` o `due_diligence/guards.py` y documentarlo en `research.md`
- [ ] T025 Ejecutar `/abrir-pr 2`: revisión independiente con el subagente `code-reviewer`, corregir hallazgos, abrir el PR que cierra #2 y mover el ticket a In review por el MCP de GitHub
- [ ] T026 Comentar en el issue #2 lo especificado, lo decidido y lo pendiente (hooks de reglas de negocio → #3; fallas y cobertura parcial → #4; procedencia y ambigüedad → #5; escalamiento → #6)

## Dependencies & Execution Order

- Setup (T001-T003) → Foundational (T004-T007) → historias → Polish.
- US1 y US2 son P1; US2 completa los `prompt` de subagentes y el hook que `options.py` registra; US3 y US4 extienden `events.py` y `coordinator.py`, por eso van después de US1/US2.
- `events.py` lo tocan T004, T018 y T020: no en paralelo. `prompts.py` lo tocan T009 y T014: no en paralelo.
- T024 es la única tarea que necesita la API key y la red; el resto corre sin ella.

## Parallel Examples

- Fase 1: T002 y T003. Fase 2: T005 junto a T004.
- Fase 4: T015 y T017 pueden escribirse en paralelo con T013.

## Implementation Strategy

- **MVP**: Setup + Foundational + US1 (T001-T012): el coordinador existe, tiene su prompt y emite eventos.
- Siguiente: US2 (aislamiento y resultados verificables), luego US3 (paralelo y dependencia) y US4 (ciclo).
- Riesgo declarado: hasta el ticket #3 las reglas de negocio 1-3 no están garantizadas por hooks; no usar el sistema para decisiones reales.
