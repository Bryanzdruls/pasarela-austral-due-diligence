---
description: "Tareas de los hooks del SDK para las reglas de negocio 1 a 3"
---

# Tasks: Hooks del SDK para las reglas de negocio 1 a 3

**Input**: `specs/003-hooks-reglas-negocio/` (plan.md, spec.md, research.md, data-model.md, contracts/rules.md, quickstart.md)

**Prerequisites**: plan.md y spec.md; constitución v1.1.1; tickets #1, #2, #9 y #10 fusionados.

**Tests**: incluidos y obligatorios (constitución VI). **Regla de proceso**: en cada historia primero se escriben las pruebas, se ejecutan y se comprueba que fallan por la razón esperada, y solo entonces se implementa. Las pruebas comprueban el motivo del bloqueo y la regla, no solo que se bloquee. Los valores de ejemplo son ficticios (`CO-XX-000N`, `PE-000N`).

**Modelo de amenaza**: los hooks protegen contra descuidos del modelo y de los subagentes, no contra un adversario. Una sola revisión de código en la fase final.

**Forma real de la entrada** (medida con el modelo): `tool_response` de una herramienta MCP llega como **texto** con el sobre JSON `{"ok":..,"content":{..},"metadata":{..}}`; `UserPromptSubmit` entrega `prompt`. Las pruebas usan esa forma.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencia pendiente)
- **[Story]**: US1 regla 1 · US2 regla 2 · US3 regla 3 · US4 vocabulario, aislamiento y cableado

## Phase 1: Setup

- [x] T001 Ejecutar `python -m pytest -q due_diligence` en la rama y anotar la línea base (94 pruebas en verde) y que `ruff` está limpio, antes de tocar nada

## Phase 2: Foundational (bloquea las historias)

- [x] T002 Escribir `due_diligence/tests/test_rules.py` con las pruebas de las piezas base (deben fallar antes de T004): `is_high_risk` para las cuatro categorías con mayúsculas, tildes y matices ("Venta en línea de Suplementos Dietarios", "criptoactivos", "casa de apuestas", "venta de medicamentos") y falso para riesgo bajo ("librería", "cafetería") y texto vacío; `RECOMMENDATIONS` tiene exactamente `habilitar`, `no_habilitar` y `escalar_a_cumplimiento`; `parse_envelope` acepta texto JSON, diccionario y lista de bloques `[{"type":"text","text":"{...}"}]` y devuelve `None` ante texto que no es JSON, un valor que no es objeto o un sobre sin `ok`
- [x] T003 Ejecutar `python -m pytest -q due_diligence/tests/test_rules.py` y comprobar que falla por la razón esperada (`rules.py` no existe)
- [x] T004 Crear `due_diligence/rules.py` con `HIGH_RISK_ROOTS = ("apuesta", "cripto", "suplemento", "medicament")`, `RECOMMENDATIONS`, el normalizador (minúsculas, sin tildes), `is_high_risk`, `Decision(allowed, rule, reason)` y `parse_envelope`; comprobar que T002 pasa

## Phase 3: User Story 1 - Regla 1: listas solo con el comercio identificado (Priority: P1) 🎯 MVP

**Goal**: la consulta a listas se bloquea salvo que el registro haya identificado de forma unívoca al comercio (o a su representante legal) en la conversación.

**Independent Test**: sin registro, con registro ambiguo, vacío, con error o ininterpretable, y con otro identificador, la consulta se bloquea; tras un registro unívoco, se permite para el comercio y para su representante.

- [x] T005 [US1] Ampliar `test_rules.py` con las pruebas de `CaseBook` para la regla 1 (deben fallar antes de T007), con respuestas con la forma real: sin ningún registro → `check_listas` bloquea con regla 1; registro con `match_count: 2` y `ambiguous: true` → bloquea; `match_count: 0` → bloquea; `ok: false` → bloquea; respuesta ininterpretable → bloquea; una coincidencia con `existe: false` → bloquea; una coincidencia con `existe: true` → permite `tipo: comercio` con su id y `tipo: persona` con el id de su representante; con otro identificador de comercio o una persona ajena → bloquea; `tipo` desconocido o `referencia` ausente → bloquea (falla cerrado); dos comercios identificados no mezclan sus representantes
- [x] T006 [US1] Ejecutar `test_rules.py` y comprobar que las pruebas de T005 fallan por la razón esperada
- [x] T007 [US1] Implementar en `rules.py` el `CaseBook` y `CommerceCase` (campos de `data-model.md`), `observe` para `consultar_registro_mercantil` (identificación unívoca: `ok`, `match_count == 1`, `ambiguous == false`, `existe == true`; nunca lanza) y `check_listas` con los mensajes de `contracts/rules.md`
- [x] T008 [US1] Ejecutar `test_rules.py` y comprobar que T005 pasa
- [x] T009 [US1] Escribir `due_diligence/tests/test_rule_hooks.py` con las pruebas del hook `PreToolUse` y `PostToolUse` para la regla 1 (deben fallar antes de T011), invocando las funciones con entradas con la forma real (`tool_name` con el prefijo `mcp__pasarela-fuentes__`, `tool_input`, `tool_response` como texto JSON, `agent_type`): el caso del enunciado (consulta a listas sin registro previo) devuelve la denegación del SDK con regla 1 en el motivo; tras un registro unívoco procesado por `PostToolUse`, la consulta devuelve `{}`; una excepción interna produce una denegación; herramientas que no son de reglas devuelven `{}`
- [x] T010 [US1] Ejecutar `test_rule_hooks.py` y comprobar que falla por la razón esperada (`rule_hooks.py` no existe)
- [x] T011 [US1] Crear `due_diligence/rule_hooks.py` con `make_pre_tool_use`, `make_post_tool_use` y `make_user_prompt_submit` según `contracts/rules.md` (denegación con la forma del guard del #2, falla cerrado, nunca lanza desde `PostToolUse`)
- [x] T012 [US1] Ejecutar `test_rule_hooks.py` y `test_rules.py` y comprobar que pasan

## Phase 4: User Story 2 - Regla 2: coincidencia en listas impide habilitar (Priority: P1)

**Goal**: tras una coincidencia en listas (del comercio o de su representante) no se puede registrar un informe que recomiende habilitar; escalar siempre se permite.

**Independent Test**: simular coincidencia del comercio y, por separado, del representante; `habilitar` se rechaza y `escalar_a_cumplimiento` se permite; sin coincidencia, esta regla no bloquea.

- [x] T013 [US2] Ampliar `test_rules.py` (deben fallar antes de T015): `observe` de un resultado de listas con `match: true` para el comercio → `check_informe` con `habilitar` bloquea con regla 2; coincidencia solo del representante → bloquea igual; `match: false` en ambos → regla 2 no bloquea; coincidencia de un comercio no afecta a otro; `escalar_a_cumplimiento` y `no_habilitar` se permiten con coincidencia; `check_escalar` siempre permite; un resultado de listas con `ok: false` **no** cuenta como "sin coincidencias" (no registra ausencia)
- [x] T014 [US2] Ejecutar `test_rules.py` y comprobar que las pruebas de T013 fallan por la razón esperada
- [x] T015 [US2] Implementar en `rules.py` el registro de resultados de listas en `observe` (coincidencia del comercio o del representante, por comercio) y `check_informe` para la regla 2 y `check_escalar`
- [x] T016 [US2] Ampliar `test_rule_hooks.py` con la regla 2 de extremo a extremo con entradas reales (listas con coincidencia → `registrar_informe` con `habilitar` denegado con regla 2; `escalar_a_cumplimiento` permitido); ejecutar y comprobar que pasan

## Phase 5: User Story 3 - Regla 3: alto riesgo nunca se habilita (Priority: P1)

**Goal**: la recomendación de habilitar se rechaza para las cuatro categorías de alto riesgo, venga la categoría del registro, de la solicitud o del catálogo, aunque el catálogo diga "sin clasificar".

**Independent Test**: para cada categoría, `habilitar` se rechaza por cada fuente; con riesgo bajo y sin alertas se permite; la evidencia de una solicitud no pasa a un comercio posterior.

- [x] T017 [US3] Ampliar `test_rules.py` (deben fallar antes de T019): por cada una de las cuatro categorías, `habilitar` se rechaza con regla 3 cuando la categoría viene (a) del registro del comercio, (b) del texto de la solicitud (`start_request`), (c) de una consulta al catálogo por su argumento `categoria` con resultado `sin_clasificar`, y (d) del catálogo con `riesgo: "alto"`; riesgo bajo sin otras alertas → permite; `start_request` limpia la evidencia de la solicitud anterior (un comercio de riesgo bajo investigado después de uno de alto riesgo se permite) pero la categoría del registro y lo ya determinado de un comercio se conservan; `escalar_a_cumplimiento` y `no_habilitar` siempre se permiten
- [x] T018 [US3] Ejecutar `test_rules.py` y comprobar que las pruebas de T017 fallan por la razón esperada
- [x] T019 [US3] Implementar en `rules.py` `start_request`, el registro de las consultas al catálogo en `observe` (argumento `categoria` y resultado), la categoría del registro y `check_informe` para la regla 3 con la persistencia por comercio (D6)
- [x] T020 [US3] Ampliar `test_rule_hooks.py` con la regla 3 de extremo a extremo (`UserPromptSubmit` con la categoría declarada, `PostToolUse` del catálogo, `PreToolUse` de `registrar_informe` denegado con regla 3); ejecutar y comprobar que pasan

## Phase 6: User Story 4 - Vocabulario, aislamiento y cableado (Priority: P2)

**Goal**: las reglas no se pueden esquivar con otra redacción ni con otra herramienta, y están cableadas en la sesión.

**Independent Test**: una recomendación fuera del vocabulario se rechaza; el coordinador puede usar `registrar_informe` y `escalar_a_cumplimiento` y los subagentes no; la sesión crea un `CaseBook` por conversación y los hooks se registran en las opciones.

- [x] T021 [US4] Ampliar `test_rules.py` y `test_guards.py` (deben fallar antes de T023): `registrar_informe` con `Habilitar`, `habilitar comercio`, vacío, ausente o no texto → rechazo de vocabulario con los valores permitidos en el motivo; `habilitar` para un comercio nunca identificado → rechazo (FR-010); el coordinador (sin `agent_type`) puede usar `registrar_informe` y `escalar_a_cumplimiento` y los cuatro subagentes **no**; el coordinador sigue sin poder usar las herramientas de fuentes
- [x] T021b [US4] Ampliar `test_rules.py`, `test_rule_hooks.py` y `test_guards.py` (deben fallar antes de T024) con la exigencia de escalar y el rastro: un comercio con coincidencia en listas, o de alto riesgo, y sin escalar aparece en `pending_escalations()` y el hook `Stop` devuelve `{"decision": "block", ...}` con el motivo; tras un `escalar_a_cumplimiento` con `ok: true` deja de aparecer; un `invalid_input` no cuenta como escalado; con `stop_hook_active` verdadero el hook no vuelve a bloquear; un comercio de riesgo bajo sin coincidencias no se bloquea al cerrar; el rastro `PASARELA_HOOK_TRACE` incluye la regla de cada denegación (FR-011)
- [x] T022 [US4] Ampliar `test_options.py`, `test_prompts.py` y `test_coordinator.py` (deben fallar antes de T023): `build_options` registra `PreToolUse` (guard y reglas), `PostToolUse`, `UserPromptSubmit` y `Stop` sobre un mismo `CaseBook` y permite las dos herramientas de salida; `build_options(book)` usa el `CaseBook` recibido; el prompt del coordinador contiene los tres valores del vocabulario, `registrar_informe` y `escalar_a_cumplimiento` y sigue diciendo que las reglas se imponen con hooks; dos `DueDiligenceSession` no comparten `CaseBook`; una conversación con dos comercios no mezcla sus identificaciones
- [x] T023 [US4] Ejecutar las pruebas de T021, T021b y T022 y comprobar que fallan por la razón esperada
- [x] T024 [US4] Implementar: vocabulario y FR-010 en `check_informe`; el estado `escalado` en `observe`, `pending_escalations` y el hook `Stop` (`make_stop`, D12); `guards.py` (el coordinador puede usar las dos herramientas de salida; el rastro incluye la regla); `options.py` (`build_options(book=None)`, hooks y `allowed_tools`); `coordinator.py` (un `CaseBook` por conversación al construir las opciones); `prompts.py` (vocabulario y herramientas de salida, conservando el texto de alcance)
- [x] T025 [US4] Ejecutar `python -m pytest -q due_diligence`, `ruff check` y `ruff format --check`; todo en verde, incluidas las pruebas antiguas (las que pasaban `options` explícitas siguen funcionando)

## Phase 7: Cierre y verificación

- [x] T026 Verificación por mutación (`D11`): romper a propósito cada regla (permitir listas sin identificar; ignorar la coincidencia del representante; ignorar la categoría del registro; ignorar la solicitud del analista; ignorar la lista propia cuando el catálogo dice "sin clasificar"; aceptar una recomendación fuera del vocabulario; no limpiar la evidencia al cambiar de solicitud) y comprobar que alguna prueba falla; restaurar el archivo tras cada una y confirmarlo con `git diff`
- [x] T027 Verificación con modelo real (inicio de sesión de Claude Code si la clave del API no es válida): ejecutar la matriz de `quickstart.md` y crear `specs/003-hooks-reglas-negocio/verification.md` con el resultado **de cada caso** (esperado, observado, aprobado o fallido), incluido el intento de consultar listas sin identificación; si algo difiere, ajustar y documentar en `research.md`; anotar lo que **no** se pudo comprobar
- [ ] T028 Actualizar `docs/TRAZABILIDAD.md`: filas R1, R2, R3, B5 y C5 con su estado y evidencia reales, la falta grave de la sección 8 y el resumen recalculado; y `docs/ECOSISTEMA.md` si cambia algo del ecosistema
- [ ] T029 Una **única** revisión de código (es el paso `code-reviewer` de `/abrir-pr`) con el modelo de amenaza escrito y entradas reproducibles, y la revisión de cumplimiento con `compliance-reviewer`; corregir solo los bloqueantes y declarar el resto
- [ ] T030 Ejecutar `/abrir-pr 3`: comentario de avance y ticket a `In review` por el MCP
- [ ] T031 Tras la fusión: ejecutar `/sincronizar-tickets` y comprobar que el #3 pasa a `Done`

## Dependencies & Execution Order

- Setup (T001) → Foundational (T002-T004) → historias → Cierre.
- US1, US2 y US3 son P1 y comparten `rules.py` y `test_rules.py`: se hacen en orden (US1 → US2 → US3) para no pisar los mismos archivos; cada una es verificable por separado con su prueba independiente.
- US4 depende de US1 a US3 (usa `check_informe` completo y el cableado de los hooks).
- T026 y T027 necesitan US4; T027 necesita la sesión con modelo; T028 después de T027; T029 antes de T030.

## Parallel Examples

- Las pruebas de T013 y T017 se pueden redactar a la vez (secciones distintas de `test_rules.py`), pero se ejecutan y se implementan en orden.
- Cierre: T026 (mutación) y T027 (modelo real) en paralelo.

## Implementation Strategy

- **MVP**: Setup + Foundational + US1 (T001-T012): la regla 1, que cierra el caso C5 del enunciado, queda impuesta por hook.
- Siguiente: US2 y US3 (reglas 2 y 3 sobre el informe registrado), US4 (vocabulario, aislamiento y cableado) y el cierre.
- Riesgos declarados: la forma de `tool_response` puede cambiar entre versiones del SDK (la medimos con la 0.2.168; si no se puede interpretar, falla cerrado); y el modelo debe registrar el informe con `registrar_informe` para que las reglas 2 y 3 actúen sobre él (el prompt lo exige).
