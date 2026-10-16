---
description: "Tareas del coordinador y subagentes de due diligence"
---

# Tasks: Coordinador y subagentes de due diligence

**Input**: `specs/002-coordinador-subagentes/` (plan.md, spec.md, research.md, data-model.md, contracts/coordinator.md, quickstart.md)

**Prerequisites**: plan.md, spec.md; servidor MCP del ticket #1 fusionado; análisis `/speckit-analyze` aplicado.

**Tests**: Incluidos (constitución VI). **Regla de proceso**: en cada historia primero se escriben las pruebas, se ejecutan y se comprueba que fallan por la razón esperada, y solo entonces se implementa. Ninguna prueba llama al modelo real: usan el cliente falso de `due_diligence/tests/fakes.py` o llaman a los hooks directamente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencia pendiente)
- **[Story]**: US1 informe y conversación multi-turno · US2 aislamiento · US3 paralelo y dependencia · US4 ciclo por razón de parada

## Phase 1: Setup

- [x] T001 Añadir la dependencia `claude-agent-sdk>=0.2.140` a `pyproject.toml`, añadir `due_diligence` a `testpaths` de pytest y ejecutar `python -m uv sync`
- [x] T002 [P] Crear `due_diligence/__init__.py` y `due_diligence/tests/__init__.py`
- [x] T003 [P] Añadir `ANTHROPIC_API_KEY=` (sin valor) a `.env.example`; comprobar que `.gitignore` ya ignora `.env` y `.env.*`

## Phase 2: Foundational (bloquea todas las historias)

- [x] T004 Inspeccionar el SDK instalado (`inspect.signature` y `dataclasses.fields`) y anotar en `specs/002-coordinador-subagentes/research.md` (D11) los hechos confirmados: firmas de `ClaudeSDKClient.query` y `receive_response`, campos de `ClaudeAgentOptions` (`tools`, `allowed_tools`, `cwd`, `setting_sources`, `hooks`, `mcp_servers`, `agents`), campos de `AgentDefinition`, `HookMatcher`, y los campos de `AssistantMessage`, `UserMessage`, `ResultMessage`, `ToolUseBlock`, `ToolResultBlock`; si algo difiere de `contracts/coordinator.md`, corregir primero el contrato
- [x] T005 Definir en `due_diligence/events.py` los tipos de dominio de `data-model.md`: enumeración `FrontName` (`registro_mercantil`, `listas_restrictivas`, `noticias`, `riesgo_categoria`); `FrontResult` con `frente`, `contenido`, `metadatos` (`{fuente, fecha}`, obligatorios) y `estado` ∈ `completo` | `no_estructurado` | `no_completado`; eventos con `timestamp` UTC ISO 8601: `SubagentStarted(frente, tool_use_id, encargo)`, `SubagentFinished(frente, result)`, `CoordinatorText(text)`, `RunFinished(subtype, stop_reason, terminal_reason)`
- [x] T006 [P] Crear `due_diligence/tests/fakes.py`: constructores de mensajes del SDK (`AssistantMessage` con `TextBlock`/`ToolUseBlock`, `UserMessage` con `ToolResultBlock`, `ResultMessage`) y `FakeClient` con `query(text)` (registra los textos recibidos) y `receive_response()` (devuelve el siguiente turno de una lista de turnos preparados, terminando en `ResultMessage`), y `fake_client_factory` que cuenta cuántos clientes se crean
- [x] T007 Crear `due_diligence/agents.py` con `FRONT_TOOLS` (cada frente → su única herramienta `mcp__pasarela-fuentes__...`, ver tabla de `data-model.md`) y `build_agents()` que devuelve las cuatro `AgentDefinition` con `description` y `tools`; el `prompt` de cada una se completa en T015
- [x] T008 Crear `due_diligence/options.py` con `build_options()`: `agents=build_agents()`, `tools=["Agent"]`, `allowed_tools=["Agent"]`, `cwd` = raíz del repo, `mcp_servers={"pasarela-fuentes": {type: "stdio", command: sys.executable, args: ["-m","mcp_server"], env: PYTHONPATH = raíz del repo + PASARELA_FAULTS y PASARELA_RUNTIME_DIR si existen}}` (sin `cwd` en la config stdio), `setting_sources=[]`; sin `max_turns`; el hook de aislamiento se registra en T017. Sus pruebas (T011) y las de agentes (T014) se escriben **antes** de T007 y T008 y se ejecutan para verlas fallar

**Checkpoint**: tipos, cliente falso y configuración base listos.

## Phase 3: User Story 1 — Informe sintetizado y conversación multi-turno (P1) 🎯 MVP

**Goal**: solicitud del analista → coordinador delega en los cuatro frentes → informe con recomendación; los seguimientos se responden desde el contexto de la sesión.

**Independent Test**: con un cliente falso, una sesión emite eventos y cada turno termina en `RunFinished`; dos turnos reutilizan el mismo cliente; el prompt del coordinador contiene las instrucciones de FR-001 a FR-013.

- [x] T009 [US1] Tests en `due_diligence/tests/test_prompts.py` (deben fallar antes de T010): el prompt del coordinador menciona los cuatro frentes; pide el comercio o su identificador si falta y no investigar (FR-010); pide aclarar cuál investigar si la solicitud menciona más de un comercio; exige una sección por frente, una sección "Datos aportados por el analista" y una recomendación (FR-009, FR-011); indica pasar a cada subagente solo el encargo mínimo y no datos de un comercio anterior (FR-004, FR-012); indica responder un seguimiento desde lo ya investigado sin relanzar subagentes (FR-013); indica lanzar registro, noticias y riesgo en un mismo turno y listas solo después, con el identificador y el representante del registro (FR-006, FR-007)
- [x] T010 [US1] Crear `due_diligence/prompts.py` con `COORDINATOR_PROMPT` (español) que haga pasar T009
- [x] T011 [US1] Tests en `due_diligence/tests/test_coordinator.py` y `due_diligence/tests/test_options.py` (deben fallar antes de T012): `ask` emite `CoordinatorText` y termina con un único `RunFinished`; dos `ask` sobre la misma sesión usan el mismo cliente (la fábrica se invoca una vez, `query` se llama dos veces) (FR-013); el cliente se abre en `__aenter__` y se cierra en `__aexit__`; `build_options()` tiene `tools == ["Agent"]`, `allowed_tools == ["Agent"]`, `setting_sources == []` y no define `max_turns`; el servidor MCP configurado se puede importar lanzando `sys.executable -c "import mcp_server"` con el `env` de la configuración (PYTHONPATH), aunque el directorio actual del proceso sea otro (D13); `build_options().cwd` es la raíz del repo y la configuración stdio no contiene la clave `cwd`
- [x] T012 [US1] Implementar `due_diligence/coordinator.py`: `DueDiligenceSession(options=None, client_factory=ClaudeSDKClient)` con `__aenter__`, `__aexit__` y `ask(text)`, que hace `client.query(text)`, recorre `client.receive_response()`, traduce con `events.py` y emite eventos de dominio
- [x] T013 [US1] Crear `due_diligence/__main__.py`: `python -m due_diligence` abre una sesión interactiva (lee mensajes del analista por stdin hasta `salir`, imprime los eventos legibles con su `encargo` y `timestamp`); si falta `ANTHROPIC_API_KEY` en el entorno termina con un mensaje claro sin intentar llamar al modelo. Es el soporte del quickstart y de la verificación manual (T025)

## Phase 4: User Story 2 — Cada subagente ve solo lo suyo (P1)

**Goal**: herramientas y contexto mínimos por frente; resultados con contenido y metadatos separados; encargo inspeccionable.

**Independent Test**: cada `AgentDefinition` tiene exactamente una herramienta; el hook niega cualquier otra (también en el coordinador); `SubagentStarted` expone el encargo; una respuesta mal formada se marca `no_estructurado`.

- [x] T014 [US2] Tests en `due_diligence/tests/test_agents.py` (deben fallar antes de T015): hay exactamente cuatro agentes con los nombres de `FrontName`; cada uno tiene en `tools` exactamente la herramienta de `FRONT_TOOLS` y ninguna más (SC-002); `description` no vacía; el `prompt` exige responder con JSON `{contenido, metadatos:{fuente, fecha}}` (FR-005); el de listas indica usar identificadores; el de registro dice no elegir entre coincidencias; el de noticias dice que una mención no es coincidencia en listas
- [x] T015 [US2] Completar los `prompt` de los cuatro subagentes en `due_diligence/prompts.py` y usarlos en `due_diligence/agents.py`
- [x] T016 [P] [US2] Tests en `due_diligence/tests/test_guards.py` llamando al hook directamente (deben fallar antes de T017): dentro de cada subagente se permite su herramienta y se niega cualquier otra de `mcp__pasarela-fuentes__*` y cualquier herramienta integrada (Bash, Write, Read); en el coordinador (sin `agent_type`) se permite `Agent` y `Task` y se niega todo lo demás, incluidas herramientas de fuentes y `Bash`; un `agent_type` desconocido se niega (falla cerrado); el motivo de la denegación es legible
- [x] T017 [US2] Implementar `due_diligence/guards.py` con `tool_guard(input_data, tool_use_id, context)` según `contracts/coordinator.md` y registrarlo como hook `PreToolUse` en `due_diligence/options.py`
- [x] T018 [P] [US2] Tests en `due_diligence/tests/test_events.py` (deben fallar antes de T019): respuesta de subagente con JSON válido → `FrontResult(estado="completo")` con contenido y metadatos separados; JSON inválido o sin `metadatos.fuente`/`fecha` → `estado="no_estructurado"` (nunca "completo"); `SubagentStarted.encargo` es exactamente el `prompt` de la llamada `Agent` (SC-003); los mensajes con `parent_tool_use_id` (de subagentes) no generan `CoordinatorText`; el nombre de herramienta `Task` se trata igual que `Agent`
- [x] T019 [US2] Implementar en `due_diligence/events.py` la traducción de mensajes del SDK a eventos de dominio y el parseo a `FrontResult`: `ToolUseBlock` con `name` en (`Agent`, `Task`) → `SubagentStarted` (frente desde `input["subagent_type"]`, `encargo` desde `input["prompt"]`); `ToolResultBlock` emparejado por `tool_use_id` → `SubagentFinished`; texto del coordinador → `CoordinatorText`; `ResultMessage` → `RunFinished`; cada evento con `timestamp`

## Phase 5: User Story 3 — Paralelo y dependencia (P2)

**Goal**: registro, noticias y riesgo arrancan juntos; listas después del registro (orientación; garantía en #3).

**Independent Test**: con un turno falso donde los tres `Agent` llegan en un mismo `AssistantMessage`, los tres `SubagentStarted` salen antes de cualquier `SubagentFinished`; `listas_restrictivas` arranca después de `SubagentFinished(registro_mercantil)`.

- [x] T020 [US3] Tests en `due_diligence/tests/test_events.py` y `due_diligence/tests/test_coordinator.py` (deben fallar antes de T021): tres `ToolUseBlock` de `Agent` en un mismo mensaje → tres `SubagentStarted` consecutivos antes de cualquier `SubagentFinished` (SC-004), con `timestamp` no decreciente; resultados que llegan en otro orden se emparejan por `tool_use_id`; `dependency_violations(events)` devuelve el hallazgo cuando `listas_restrictivas` inicia antes de que `registro_mercantil` termine y devuelve vacío en la secuencia correcta; una sesión con el turno completo falso emite los eventos en el orden de `contracts/coordinator.md`; un turno de seguimiento falso (solo texto) no emite `SubagentStarted` (FR-013)
- [x] T021 [US3] Implementar en `due_diligence/events.py` el emparejamiento por `tool_use_id` de varias llamadas concurrentes y la función `dependency_violations(events)`

## Phase 6: User Story 4 — El ciclo termina por razón de parada (P2)

**Goal**: ni contador de iteraciones ni lectura de texto controlan el ciclo.

**Independent Test**: un turno falso con el texto "terminado" en medio no corta el turno; el turno acaba solo en `ResultMessage`; `RunFinished` conserva `subtype`, `stop_reason` y `terminal_reason`.

- [x] T022 [US4] Tests en `due_diligence/tests/test_coordinator.py` (deben fallar antes de T023, si alguno ya pasa por construcción, verificarlo con una mutación temporal y anotarlo): un `AssistantMessage` con texto "listo, terminado" seguido de más mensajes y un `ResultMessage` → se procesan todos y `RunFinished` es el último (SC-005); un `ResultMessage` con `subtype="error_max_turns"` se refleja en `RunFinished.subtype` sin lanzar fuera de `ask`; turnos de longitudes muy distintas terminan todos sin tope de iteraciones; el código fuente de `due_diligence/coordinator.py` y `due_diligence/options.py` no contiene `max_turns`
- [x] T023 [US4] Ajustar `due_diligence/coordinator.py` si alguna prueba de T022 falla: la salida del turno depende solo del fin de `receive_response()` tras `ResultMessage`; nunca de `TextBlock`, nunca de un contador; registrar `stop_reason` en `RunFinished`

## Phase 7: Cierre y verificación

- [x] T024 Ejecutar `python -m uv run pytest due_diligence mcp_server -q` y `python -m uv run ruff check . && python -m uv run ruff format --check .`; todo en verde
- [x] T025 Verificación con modelo real (requiere `ANTHROPIC_API_KEY`; incluye T035): ejecutar la matriz de 5 casos de `quickstart.md` y crear `specs/002-coordinador-subagentes/verification.md` con el resultado **de cada caso** (esperado, observado, aprobado/fallido) y las marcas de tiempo del caso 1; si algo difiere, ajustar `due_diligence/prompts.py` o `due_diligence/guards.py`, repetir y documentar en `research.md`
- [ ] T026 Ejecutar `/abrir-pr 2`: revisión independiente con el subagente `code-reviewer` real, corregir hallazgos, abrir el PR que cierra #2 y mover el ticket a In review por el MCP de GitHub
- [ ] T027 Comentar en el issue #2 lo especificado, lo decidido y lo pendiente (hooks de reglas de negocio → #3; fallas y cobertura parcial → #4; procedencia y ambigüedad → #5; escalamiento → #6); dejar anotado que FR-007 es orientación hasta fusionar el #3

## Phase 8: Correcciones de la revisión independiente (code-reviewer)

- [x] T028 [Bloqueante] Pasar `COORDINATOR_PROMPT` como `system_prompt` en `due_diligence/options.py`; prueba `test_the_coordinator_prompt_is_actually_used`
- [x] T029 Pre-aprobar las cuatro herramientas de frente en `allowed_tools` (`due_diligence/options.py`), con prueba de que no se pre-aprueba nada más; su efecto real se verifica en T025
- [x] T030 Cerrar todo turno con `RunFinished` (`error_stream_ended`, `error_exception`), contener solo `ResultError` tras un resultado, e interrumpir y drenar un turno abandonado (`due_diligence/coordinator.py`, `due_diligence/tests/fakes.py`)
- [x] T031 Validación estricta de resultados de frente y tolerancia a texto previo y bloques extra (`due_diligence/events.py`)
- [x] T032 Hook: denegar delegación en segundo plano y traza opcional `PASARELA_HOOK_TRACE` (`due_diligence/guards.py`)
- [x] T033 Verificadores de secuencia: dependencia exige registro completo; un reintento no viola el paralelismo (`due_diligence/events.py`)
- [x] T034 CLI: informar fallos del SDK sin traceback con código de salida 2 (`due_diligence/__main__.py`)
- [x] T035 En T025, ejecutar con `PASARELA_HOOK_TRACE` y anotar en `verification.md` el `agent_type` real que entrega el SDK y si los subagentes pudieron usar sus herramientas MCP

## Dependencies & Execution Order

- Setup (T001-T003) → Foundational (T004-T008) → historias → Cierre.
- T004 va primero en Foundational: si el SDK difiere del contrato, se corrige el contrato antes de escribir código.
- US1 y US2 son P1; US2 completa los `prompt` de subagentes y el hook que `options.py` registra; US3 y US4 extienden `events.py` y `coordinator.py`, por eso van después.
- `events.py` lo tocan T005, T019 y T021; `prompts.py` lo tocan T010 y T015; `options.py` lo tocan T008 y T017: no en paralelo.
- T025 es la única tarea que necesita la API key y la red; el resto corre sin ella.

## Parallel Examples

- Fase 1: T002 y T003. Fase 2: T006 junto a T005.
- Fase 4: T016 y T018 pueden escribirse en paralelo con T014.

## Implementation Strategy

- **MVP**: Setup + Foundational + US1 (T001-T013): el coordinador existe, tiene su prompt, la sesión multi-turno y emite eventos.
- Siguiente: US2 (aislamiento y resultados verificables), luego US3 (paralelo y dependencia) y US4 (ciclo).
- Riesgo declarado: hasta el ticket #3 las reglas de negocio 1-3 no están garantizadas por hooks; no usar el sistema para decisiones reales ni demostrarlo a terceros.
