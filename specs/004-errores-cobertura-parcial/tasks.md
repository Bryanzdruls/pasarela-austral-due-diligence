---
description: "Tareas de errores estructurados y cobertura parcial"
---

# Tasks: Errores estructurados y cobertura parcial

**Input**: `specs/004-errores-cobertura-parcial/` (plan.md, spec.md, research.md, data-model.md, contracts/cobertura.md, quickstart.md)

**Prerequisites**: plan.md y spec.md; constitución v1.1.1; tickets #1, #2, #3, #9 y #10 fusionados.

**Nota de implementación**: las pruebas de las tareas T003, T014, T017 y T018 viven en `due_diligence/tests/test_rules_cobertura.py` (archivo nuevo, para no alargar `test_rules.py`); los ajustes de pruebas del #3 están listados en `verification.md`.

**Tests**: incluidos y obligatorios (constitución VI). **Regla de proceso**: en cada historia primero se escriben las pruebas, se ejecutan y se comprueba que fallan por la razón esperada, y solo entonces se implementa. Las pruebas comprueban el motivo del bloqueo y la regla, no solo que se bloquee. Los valores de ejemplo son ficticios (`CO-XX-000N`, `PE-000N`).

**Modelo de amenaza**: igual que en el #3: los hooks protegen contra descuidos del modelo y de los subagentes, no contra un adversario. Una sola revisión de código en la fase final.

**Forma real de la entrada**: `tool_response` de una herramienta MCP llega como **texto** con el sobre JSON del servidor (`{"ok":true,...}` o `{"ok":false,"error_code":...,"retryable":...,"partial":{}}`). Las pruebas usan esa forma.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencia pendiente)
- **[Story]**: US1 error estructurado de un frente · US2 reintentos · US3 informe parcial y habilitar

## Phase 1: Setup

- [x] T001 Ejecutar `python -m pytest -q` en la rama y anotar la línea base (890 pruebas en verde en `main`) y que `ruff` está limpio, antes de tocar nada
- [x] T002 Corregir `docs/TRAZABILIDAD.md` heredado de `main`: R1, R2, R3, B5 y C5 pasan de "En rama" a "Hecho (en `main`, PR #17)"; E7 pasa a "Hecho" con la evidencia real (handshake por stdio con `python -m uv run python -m mcp_server`, 6 herramientas; requiere `uv`; falta la prueba desde una sesión nueva de Claude Code); recontar el resumen por estado; `python scripts/verify_ecosystem.py` en verde

## Phase 2: Foundational (bloquea las historias)

Estado de cobertura en el `CaseBook` (data-model.md): lo alimentan las cuatro fuentes y lo leen las tres historias.

- [x] T003 Escribir en `due_diligence/tests/test_rules.py` las pruebas del estado de cobertura (deben fallar antes de T005), con sobres de la forma real: un error `source_unavailable` de cada una de las cuatro fuentes se registra como fallo del frente y el sujeto (`registro`/`noticias`: `consulta`; `riesgo`: `categoria`; `listas`: `tipo` + `referencia`); un éxito posterior del **mismo sujeto** lo borra y uno de otro sujeto no; la consulta de listas del representante caída deja el frente de listas sin cubrir aunque la del comercio haya ido bien; `invalid_input` cuenta como fallo; una respuesta ininterpretable cuenta como fallo con `retryable` falso; un fallo de listas del comercio o de la persona se asocia al comercio; un fallo de noticias o riesgo se asocia a los comercios de la solicitud en curso; el sujeto se normaliza ("Comercio X" y "comercio x" son el mismo sujeto); un fallo de noticias o riesgo anterior a la identificación queda huérfano y el comercio lo adopta al ser identificado por el registro (D3); un fallo del registro sin comercio identificado queda como huérfano y se limpia con `start_request`; el fallo de un comercio **persiste** entre solicitudes y no aparece en otro comercio; `failed_fronts(comercio)` devuelve los fallos del comercio más los huérfanos; `observe` nunca lanza
- [x] T004 Ejecutar `python -m pytest -q due_diligence/tests/test_rules.py` y comprobar que las pruebas de T003 fallan por la razón esperada (los atributos y métodos de cobertura no existen)
- [x] T005 Implementar en `due_diligence/rules.py`: constantes de frente (`registro`, `listas`, `noticias`, `riesgo`) y el mapa herramienta → frente y sujeto; `FrontFailure(frente, sujeto, error_code, retryable, obtenido)`; `CommerceCase.fallos`; `CaseBook.orphan_failures` y `attempts`; en `observe` el registro de fallos y éxitos de las cuatro fuentes (el error de `RIESGO` ya se observa: conservar su comportamiento), `failed_fronts` y la limpieza en `start_request` (intentos y huérfanos; los fallos del comercio se conservan); comprobar que T003 pasa y que las pruebas del #3 siguen en verde
- [x] T006 [P] Escribir en `due_diligence/tests/test_rules.py` una prueba de que los nombres de frente del módulo de reglas y los de `FrontName` de `events.py` se corresponden mediante sus alias (D10), y hacerla pasar con el mapa de alias en `rules.py`

## Phase 3: User Story 1 - Un frente que falla se reporta con lo obtenido y si es reintentable (Priority: P1) 🎯 MVP

**Goal**: el error estructurado de una fuente llega intacto al coordinador, al chat y al `CaseBook`, y nada ilegible se da por cubierto.

**Independent Test**: provocar la falla de cada fuente (reintentable y no) y comprobar que el subagente la reporta con el frente, lo obtenido y `reintentable`, que `events.py` la distingue de un resultado ilegible y que el `CaseBook` la tiene como fallo.

- [x] T007 [US1] Escribir en `due_diligence/tests/test_events.py` las pruebas (deben fallar antes de T009): una respuesta `{"estado":"error","frente":...,"reintentable":true,"obtenido":{},"metadatos":{...}}` produce un `FrontResult` con estado `fallido`, el motivo y `reintentable` en el contenido y los metadatos separados; sin `reintentable` se toma falso; con `frente` distinto del que se delegó se trata como `no_estructurado`; una respuesta sin forma sigue siendo `no_estructurado`; la forma del #2 (`contenido` + `metadatos`) no cambia; un `fallido` no cuenta como `completo` en `dependency_violations` (listas no arranca tras un registro `fallido`)
- [x] T008 [US1] Ejecutar `test_events.py` y comprobar que T007 falla por la razón esperada (el estado `fallido` no existe)
- [x] T009 [US1] Implementar en `due_diligence/events.py`: `FrontStatus.FALLIDO`, `_validated_error` y su uso en `parse_front_result` (valida frente, `reintentable` booleano y metadatos con la fuente propia del frente); comprobar que T007 pasa y que las pruebas de `events` previas siguen en verde
- [x] T010 [US1] Escribir en `due_diligence/tests/test_prompts.py` las pruebas (fallan antes de T011): cada prompt de subagente y el formato común describen la forma de error (`estado`, `frente`, `reintentable`, `obtenido`, `metadatos`) y dicen que no se inventan datos cuando la fuente falla; el prompt del coordinador dice reintentar una vez lo reintentable, no reintentar lo no reintentable y declarar el frente sin cubrir (sin contradecir el vocabulario y las reglas del #3)
- [x] T011 [US1] Actualizar `due_diligence/prompts.py` (`_RESPONSE_FORMAT` con la forma de error y la política del coordinador); comprobar que T010 pasa y que `test_prompts.py` previo sigue en verde
- [x] T012 [US1] (medición real no lograda: ninguna llamada falló sin sobre; la forma se tomó del tipo del SDK, ver `verification.md` §4) Medir con el SDK la forma real de la entrada de `PostToolUseFailure` provocando una llamada que falla sin sobre (p. ej. un servidor que se cierra) y anotarla en `research.md` (D9) y en `verification.md`; escribir en `due_diligence/tests/test_rule_hooks.py` las pruebas de `make_post_tool_use_failure` con esa forma (fallan antes de T013): la llamada fallida se registra como fallo no reintentable del frente y sujeto, nunca lanza y no bloquea
- [x] T013 [US1] Implementar `make_post_tool_use_failure` en `due_diligence/rule_hooks.py` y registrarlo en `_hooks(book)` de `due_diligence/options.py` (con su prueba en `test_options.py`); comprobar que T012 pasa

## Phase 4: User Story 2 - Reintentar lo reintentable una vez y declarar lo demás (Priority: P1)

**Goal**: ningún frente se reintenta más de una vez por solicitud ni se reintenta lo no reintentable, con el hook, no con el prompt.

**Independent Test**: con una falla reintentable que persiste, una que se recupera y una no reintentable, comprobar cuántas llamadas se permiten y el motivo del bloqueo.

- [x] T014 [US2] Escribir en `test_rules.py` y `test_rule_hooks.py` las pruebas de `check_fuente` (fallan antes de T016): tras un fallo reintentable se permite el reintento (segunda llamada); tras el segundo fallo seguido del mismo sujeto se deniega la tercera con la regla `reintento` y un motivo que manda declarar el frente sin cubrir; tras un fallo no reintentable se deniega la repetición; tras un éxito (reintento recuperado) se permite llamar de nuevo; otro sujeto del mismo frente no cuenta como reintento, pero reescribir el mismo sujeto con otras mayúsculas o tildes sí; el tope es por sujeto y solicitud: una `start_request` reinicia los contadores pero conserva el fallo del comercio; una llamada sin fallo previo siempre se permite; con entrada ininterpretable se permite la llamada (no hay fallo conocido que impida) pero la excepción del hook deniega (falla cerrado); `make_pre_tool_use` gobierna las cuatro herramientas de fuentes, deja intacto el comportamiento para las tres del #3 y devuelve el formato de denegación del SDK
- [x] T015 [US2] Ejecutar las pruebas de T014 y comprobar que fallan por la razón esperada
- [x] T016 [US2] Implementar `CaseBook.check_fuente` en `rules.py` y ampliar `_GOVERNED` de `rule_hooks.py` con las cuatro herramientas de fuentes → `check_fuente` (el hook pasa el nombre de la herramienta); comprobar que T014 pasa y que `test_guards.py` y `test_options.py` siguen en verde (la composición con el guard de aislamiento del #2 se mantiene)

## Phase 5: User Story 3 - Un informe parcial nunca se presenta como completo (Priority: P1)

**Goal**: `registrar_informe` y `escalar_a_cumplimiento` exigen declarar los frentes caídos, y `habilitar` exige registro y listas cubiertos.

**Independent Test**: provocar la falla de cada frente: el informe que no la declara se rechaza nombrando el frente; el que la declara se acepta; con registro o listas sin cubrir (o sin consultar) `habilitar` se rechaza; sin fallas el informe completo se acepta.

- [x] T017 [US3] Escribir en `test_rules.py` las pruebas de la declaración (fallan antes de T019): para cada frente caído un informe sin su `cobertura` o con `estado: cubierto` se rechaza con la regla `cobertura` y el frente nombrado en el motivo; con `estado: sin_cubrir` y `motivo` se acepta (con `no_habilitar` y `escalar_a_cumplimiento`); los alias `registro_mercantil`, `listas_restrictivas` y `riesgo_categoria` valen; `cobertura` con forma distinta (texto libre, lista, `estado` fuera del vocabulario) no declara nada; declarar de más se acepta; varios frentes caídos nombran todos los que faltan; un fallo huérfano de la solicitud obliga a declararlo; un frente que se recuperó con el reintento no obliga; el fallo de otro comercio no obliga; `escalar_a_cumplimiento` exige lo mismo (FR-009); sin fallos vigentes el informe de antes se acepta sin cambios; falla cerrado: si el estado de cobertura no se puede evaluar (excepción al leerlo), `habilitar` se deniega (FR-010)
- [x] T018 [US3] Escribir en `test_rules.py` las pruebas de `habilitar` (fallan antes de T019): sin listas consultadas se rechaza con `cobertura_habilitar`; solo consultado el comercio (representante sin consultar) se rechaza; listas del comercio y del representante correctas y sin coincidencia se permite; listas caídas se rechaza aunque se declare (`no_habilitar` y `escalar_a_cumplimiento` sí pasan); registro caído se rechaza; noticias o riesgo caídos y declarados no impiden `habilitar`; sin representante en el registro basta la consulta del comercio; el orden de las reglas es vocabulario → `cobertura` → identificación → regla 2 → regla 3 → `cobertura_habilitar` (una coincidencia en listas sigue dando la regla 2 y el alto riesgo la regla 3); ajustar las pruebas del #3 que daban por válido `habilitar` sin listas consultadas sembrando ambas consultas con la ayuda `with_listas`, anotando cada ajuste aquí
- [x] T019 [US3] Ejecutar las pruebas de T017 y T018 y comprobar que fallan por la razón esperada; implementar en `rules.py` la declaración (`_check_cobertura`, usada por `check_informe` y `check_escalar`) y `cobertura_habilitar` con los mensajes de `contracts/cobertura.md` (qué falta y qué hacer); comprobar que pasan y que el resto de `test_rules.py` y `test_rule_hooks.py` sigue en verde
- [x] T020 [US3] Escribir en `test_rule_hooks.py` las pruebas de extremo a extremo de los hooks con la forma real (fallan antes de T021 si hace falta cambiar algo): una llamada a `buscar_noticias` fallida observada por `PostToolUse` y luego `registrar_informe` sin declararla → denegado por `PreToolUse` con el frente nombrado; con la declaración → permitido; dos comercios con fallas distintas no se mezclan; el `Stop` sigue exigiendo escalar una sola vez
- [x] T021 [US3] Ajustar lo mínimo en `rule_hooks.py`/`options.py` si T020 lo exige; actualizar `due_diligence/prompts.py` para que el coordinador declare `cobertura` con la forma de `contracts/cobertura.md` y no use "completo" ni "sin hallazgos" para un frente sin cubrir (con prueba en `test_prompts.py`); comprobar que todo `due_diligence` pasa

## Phase 6: Polish y verificación

- [x] T022 Ampliar `scripts/mutate_rules.py` con las mutaciones de la cobertura (cada una detectada): no registrar los fallos de las fuentes; no borrar el fallo tras un éxito del mismo sujeto; que un éxito de otro sujeto borre el fallo; no limitar los reintentos; permitir repetir lo no reintentable; no limpiar los intentos al cambiar de solicitud; aceptar un informe que omite el frente caído; aceptar `estado: cubierto` de un frente caído; no exigir la declaración al escalar; permitir `habilitar` sin listas; permitir `habilitar` con solo la consulta del comercio; permitir `habilitar` con el registro caído; mezclar los fallos entre comercios; tratar la respuesta ilegible como cubierta; antes de añadirlas, comprobar que las 15 mutaciones existentes siguen aplicando (T005 y T019 cambian código donde anclan) y reanclar las que no; ejecutar `python scripts/mutate_rules.py` y anotar el resultado
- [x] T023 [P] Actualizar `due_diligence/CLAUDE.md` (regla 5 por hook, cobertura y reintentos) y `docs/TRAZABILIDAD.md` (R5, B7 y C6 con la evidencia; C6 completo cuando exista el caso automatizado del #8), manteniendo el recuento del resumen y `verify_ecosystem.py` en verde
- [x] T024 Verificación con el modelo real y fallas inyectadas según `quickstart.md` (los cinco casos), con una sola corrida cada uno y registrando en `specs/004-errores-cobertura-parcial/verification.md` qué hizo el modelo, los rechazos de los hooks (`PASARELA_HOOK_TRACE`) y la forma real medida en T012; declarar lo no verificado (p. ej. con qué credencial corrió)
- [x] T025 Ejecutar `python -m pytest -q`, `ruff check .`, `ruff format --check .` y `python scripts/verify_ecosystem.py`; marcar las tareas y escribir el modelo de amenaza y la nota de revisión en `verification.md`
- [ ] T026 Una revisión de código independiente (`/abrir-pr 4`) sobre el diff, con el modelo de amenaza escrito; corregir lo grave y registrar lo demás; abrir el PR con `Closes #4` tras confirmación de la persona

## Dependencies & Execution Order

- Phase 1 → Phase 2 (bloquea) → US1, US2 y US3.
- US1 y US2 dependen solo de la Phase 2 y son independientes entre sí; US3 depende de la Phase 2 (y del tope de la US2 solo para la prueba de extremo a extremo T020).
- Dentro de cada historia: pruebas → verlas fallar → implementar → verlas pasar.
- T006 y T023 son paralelas a lo demás (archivos distintos).
- T011 y T021 editan `prompts.py`: si se sigue el orden propuesto (US3 antes que US1), T021 va primero y T011 se apoya en él.

## Implementation Strategy

- **MVP**: Phase 2 + US3 deja la regla 5 garantizada (declaración y habilitar) aunque los reintentos aún los gobierne el prompt; es el criterio del issue. US1 y US2 completan el error estructurado y el tope.
- **Orden propuesto**: Phase 1 → 2 → US3 → US1 → US2 → Phase 6, para que lo grave quede cubierto primero si el tiempo aprieta.
- Una sola revisión de código y una sola pasada de mutación al final (sin bucles de revisión).
