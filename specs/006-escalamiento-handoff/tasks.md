---
description: "Tareas del escalamiento con criterio y handoff a cumplimiento"
---

# Tasks: Escalamiento con criterio y handoff a cumplimiento

**Input**: `specs/006-escalamiento-handoff/` (plan.md, spec.md, research.md, data-model.md, contracts/escalamiento.md, quickstart.md)

**Prerequisites**: plan.md y spec.md; constitución v1.1.1; tickets #1 al #5, #9 y #10 fusionados.

**Tests**: incluidos y obligatorios (constitución VI). **Regla de proceso**: en cada historia primero se escriben las pruebas, se ejecutan y se comprueba que fallan por la razón esperada, y solo entonces se implementa. Las pruebas comprueban el motivo del rechazo y la regla, no solo que se rechace. Los valores de ejemplo son ficticios (`CO-XX-000N`, `PE-000N`, fuentes terminadas en `_ficticio`/`_ficticia`).

**Modelo de amenaza**: igual que en #3 a #5: los hooks protegen contra descuidos del modelo y de los subagentes, no contra un adversario que controle el servidor o el proceso. Una sola revisión de código en la fase final.

**Aprendido en #4 y #5 (se aplica desde el principio)**: normalizar todo lo que se compara (identificadores y claves en otra grafía); probar que el estado de un comercio no afecta a otro; probar el fallo cerrado de cada regla; las pruebas de extremo a extremo de los hooks son protección contra regresiones; reanclar las mutaciones existentes antes de añadir otras; una sola tarea edita `prompts.py`. Las pruebas de este ticket viven en `due_diligence/tests/test_rules_escalamiento.py` (archivo nuevo), con las ayudas de `test_rules.py`, `test_rules_cobertura.py` y `test_rules_procedencia.py`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencia pendiente)
- **[Story]**: US1 escalar con criterio · US2 resumen al oficial · US3 sin regresiones

## Phase 1: Setup

- [x] T001 Ejecutar `python -m pytest -q` en la rama y anotar la línea base (1.173 pruebas en verde en `main`) y que `ruff` está limpio, antes de tocar nada

## Phase 2: Foundational (bloquea las historias)

- [x] T002 Escribir en `due_diligence/tests/test_rules_escalamiento.py` las pruebas de la observación y de los motivos (deben fallar antes de T004): una respuesta de noticias con `menciones` no vacío marca `menciones` en los comercios de la solicitud y no en otros; con `menciones` vacío o con error no marca nada; una respuesta de noticias anterior a la identificación la adopta el primer comercio que se identifique y no se pierde con la solicitud siguiente; `escalation_grounds` devuelve `listas` ante una coincidencia del comercio y también del representante, `riesgo` ante cada una de las cuatro categorías (del registro, del catálogo y de la solicitud), `conflicto` ante una contradicción señalada, `noticias` ante menciones, varios a la vez, y nada para un riesgo bajo sin hallazgos; una cobertura incompleta no produce ningún motivo; para un comercio no identificado solo hay motivo si la solicitud declara alto riesgo; el identificador se busca sin distinguir mayúsculas ni espacios; los motivos de un comercio no aparecen en otro; `observe` y `escalation_grounds` nunca lanzan con entradas raras
- [x] T003 Ejecutar `python -m pytest -q due_diligence/tests/test_rules_escalamiento.py` y comprobar que las pruebas de T002 fallan por la razón esperada (`menciones` y `escalation_grounds` no existen)
- [x] T004 Implementar en `due_diligence/rules.py`: `CommerceCase.menciones`, `CaseBook._orphan_mentions`, su observación en `observe` y su adopción en `_adopt_orphans`, la estructura `Ground` y `CaseBook.escalation_grounds`; comprobar que T002 pasa y que `due_diligence` sigue en verde

## Phase 3: User Story 1 - Se escala cuando hay un motivo y no sin él (Priority: P1) 🎯 MVP

**Goal**: escalar, o recomendar escalar, solo con un motivo; un riesgo bajo sin hallazgos se habilita (C2).

**Independent Test**: cada motivo permite escalar; un riesgo bajo sin hallazgos, con y sin frentes sin cubrir, no; el informe con la recomendación `escalar_a_cumplimiento` igual.

- [x] T005 [US1] Escribir en `test_rules_escalamiento.py` las pruebas de la regla `escalamiento` (fallan antes de T007): con cada motivo `check_escalar` y `check_informe(escalar_a_cumplimiento)` no se rechazan por esta regla (con un resumen completo para no confundir); un riesgo bajo sin hallazgos se rechaza con la regla `escalamiento`, un motivo que dice que no hay hallazgo y que corresponde habilitar o no habilitar, tanto con la herramienta como con la recomendación del informe; un riesgo bajo con un frente fallido (cobertura incompleta) también se rechaza, aunque declare el frente sin cubrir; un comercio sin identificar con alto riesgo declarado en la solicitud se permite y sin él se rechaza; `habilitar` y `no_habilitar` de un riesgo bajo sin hallazgos se siguen aceptando; el identificador en otra grafía (`co-xx-0001`, con espacios) se resuelve al comercio; el motivo de un comercio no permite escalar a otro; la regla va después de `ambiguedad` y antes de `cobertura` (orden de `contracts/escalamiento.md`); falla cerrado ante un estado corrupto del comercio
- [x] T006 [US1] Ejecutar las pruebas de T005 y ejecutar también `python -m pytest -q due_diligence`: listar las pruebas de #4 y #5 que escalaban o recomendaban escalar sin motivo y dejan de pasar (se ajustan en T007)
- [x] T007 [US1] Implementar en `rules.py` `_check_escalamiento` y su uso en `check_informe` (solo con la recomendación `escalar_a_cumplimiento`) y en `check_escalar`, justo después de `_check_ambiguedad`, con el motivo de `contracts/escalamiento.md`; ajustar las pruebas de #4 y #5 listadas en T006 sembrando un motivo (una coincidencia en listas), anotando cada ajuste aquí; comprobar que T005 pasa y que `due_diligence` sigue en verde
- [x] T008 [US1] Escribir en `test_rule_hooks.py` las pruebas de extremo a extremo (protección contra regresiones: pasarán al escribirlas porque `PreToolUse` ya llama a `check_escalar` y `check_informe`): un riesgo bajo observado con la forma real, escalar → denegado con la regla `escalamiento` y también el informe con `escalar_a_cumplimiento`; con una coincidencia en listas observada → permitido; la traza con la regla `escalamiento`; el hook `Stop` sin cambios

## Phase 4: User Story 2 - El resumen al oficial se basta solo (Priority: P1)

**Goal**: el escalamiento lleva el hallazgo, con fuente, de cada frente que motiva, una causa que nombra cada motivo y las contradicciones declaradas.

**Independent Test**: para cada motivo, el resumen completo se acepta; sin el hallazgo del frente, con una causa que no nombra el motivo o con una contradicción sin declarar, se rechaza con el motivo.

- [x] T009 [US2] Escribir en `test_rules_escalamiento.py` las pruebas de `handoff_hallazgos`, `handoff_causa` y `conflictos` (fallan antes de T012): con una coincidencia en listas, el resumen con el frente `listas` (con fuente y fecha) y una causa que dice `lista` se acepta; sin el frente `listas` se rechaza con `handoff_hallazgos` nombrando el frente; el frente en otra grafía (`listas restrictivas`) vale; con alto riesgo del registro vale el frente `riesgo` o `registro`, y con alto riesgo solo declarado por el analista no se exige frente; con menciones se exige `noticias`; una causa sin palabra clave de un motivo se rechaza con `handoff_causa` nombrando el motivo y las palabras que valen; con dos motivos la causa debe nombrar ambos y se rechaza si nombra uno; la causa se compara sin tildes ni mayúsculas (`Contradicción`, `COINCIDENCIA EN LISTAS`); una causa que no es texto (`None`, lista, número) se rechaza; con una contradicción, `conflictos` completo se acepta y sin él o incompleto se rechaza con la regla `conflicto`; un resumen con `accion_recomendada` o `cobertura` ausentes lo rechaza el servidor (el hook no lo oculta); el orden es ambigüedad → escalamiento → cobertura → procedencia → conflicto → hallazgos → causa; un resumen completo con varios motivos y un frente sin cubrir declarado se acepta; falla cerrado ante un estado corrupto
- [x] T010 [US2] Ejecutar las pruebas de T009 y comprobar que fallan por la razón esperada
- [x] T011 [US2] Añadir `conflictos` (opcional) a `escalar_a_cumplimiento` en `mcp_server/tools/informes.py`, guardado en el registro, y actualizar su descripción (qué contiene el resumen y que el oficial no ve la conversación) con su prueba en `mcp_server/tools/tests/test_informes.py` y `mcp_server/tests/test_server.py`; comprobar que `mcp_server` sigue en verde
- [x] T012 [US2] Implementar en `rules.py` `_check_handoff` (hallazgos del frente que motiva y causa con una palabra clave de cada motivo, con comparación normalizada) y el uso de `_check_conflictos` en `check_escalar`, en el orden de `contracts/escalamiento.md`, con los motivos de rechazo; comprobar que T009 pasa y que `due_diligence` sigue en verde
- [x] T013 [US2] Escribir en `test_rule_hooks.py` las pruebas de extremo a extremo (protección contra regresiones): coincidencia en listas observada con la forma real; escalar sin el frente de listas → denegado con `handoff_hallazgos`; con una causa que no nombra el motivo → `handoff_causa`; con el resumen completo → permitido; la traza con las reglas nuevas; dos comercios con motivos distintos no se mezclan

## Phase 5: User Story 3 - Lo que ya funcionaba sigue funcionando (Priority: P2)

- [x] T014 [US3] Comprobar con pruebas que un caso con coincidencia o alto riesgo sigue exigiendo escalar antes de cerrar (una vez), que `habilitar` sigue rechazado en esos casos y permitido para un riesgo bajo sin hallazgos con las listas y el registro cubiertos, y que las pruebas de las reglas 1 a 5 pasan sin otros ajustes que los de T007; ejecutar `python -m pytest -q due_diligence mcp_server`

## Phase 6: Prompts, mutaciones y verificación

- [x] T015 Escribir en `due_diligence/tests/test_prompts.py` las pruebas (fallan antes de T016): el prompt del coordinador dice cuándo se escala (coincidencia en listas, alto riesgo, contradicción, menciones) y cuándo no (riesgo bajo sin hallazgos; una cobertura incompleta no basta: `no_habilitar` declarando el frente); describe el resumen (`comercio_id`, `hallazgos` con `fuente` y `fecha` del frente que motiva, `cobertura`, `conflictos`, `causa` que nombra cada motivo y `accion_recomendada`) y recuerda que el oficial no tiene la conversación; mantiene lo que ya decía (vocabulario, cobertura, fuentes, hooks y reglas 4 y 5)
- [x] T016 Actualizar `due_diligence/prompts.py` (única tarea que lo edita); comprobar que T015 pasa y que `test_prompts.py` previo sigue en verde
- [x] T017 Ampliar `scripts/mutate_rules.py`: primero comprobar que las 61 mutaciones existentes siguen aplicando (T004, T007 y T012 cambian código donde anclan) y reanclar las que no; añadir las de este ticket, cada una detectada: no observar las menciones; las menciones de un comercio valen para otro; no adoptar las menciones huérfanas; ignorar el motivo `listas`; ignorar el motivo `riesgo`; ignorar el motivo `conflicto`; ignorar el motivo `noticias`; la cobertura incompleta cuenta como motivo; sin identificar vale cualquier comercio; la regla `escalamiento` no se aplica al informe; no se aplica a la herramienta; no se exige el hallazgo del frente; la causa no se comprueba; la causa distingue tildes o mayúsculas; el resumen no exige `conflictos`; el identificador distingue mayúsculas; ejecutar `python scripts/mutate_rules.py` y anotar el resultado
- [x] T018 [P] Actualizar `due_diligence/CLAUDE.md` y `docs/TRAZABILIDAD.md` (B10 y B11 con la evidencia; C1, C2 y C3 con su verificación con el modelo real y el estado que corresponda; R2 y R3 si procede; recontar el resumen), con `python scripts/verify_ecosystem.py` en verde
- [ ] T019 Verificación con el modelo real según `quickstart.md` (los seis casos, una corrida cada uno; los dos de rechazo con un prompt de sistema de prueba, como en #3 a #5) y registrar en `specs/006-escalamiento-handoff/verification.md` qué hizo el modelo, los rechazos de los hooks (`PASARELA_HOOK_TRACE`), los ajustes de pruebas de #4 y #5 y lo no verificado; guardar la evidencia como en #4 y #5
- [ ] T020 Ejecutar `python -m pytest -q`, `ruff check .`, `ruff format --check .` y `python scripts/verify_ecosystem.py`; marcar las tareas; escribir el modelo de amenaza, la nota de revisión, los límites declarados (palabras clave en la causa, menciones sin clasificar, la lectura literal de "sin hallazgos") y el recuento final en `verification.md`
- [ ] T021 Una revisión de código independiente (`/abrir-pr 6`, `code-reviewer` y `compliance-reviewer`) con el modelo de amenaza escrito y pidiendo una entrada reproducible por hallazgo; corregir solo lo bloqueante o importante con entrada reproducible y registrar lo demás; abrir el PR con `Closes #6` tras confirmación de la persona

## Dependencies & Execution Order

- Phase 1 → Phase 2 (bloquea) → US1 → US2 → US3 → Phase 6. Las dos historias editan `check_informe` y `check_escalar` en `rules.py`: se hacen en orden, no en paralelo.
- Dentro de cada historia: pruebas → verlas fallar → implementar → pruebas de extremo a extremo.
- T018 es paralela a lo demás. T016 es la única que edita `prompts.py`. T011 (servidor) debe ir antes de T012 (el hook exige `conflictos`).

## Implementation Strategy

- **MVP**: Phase 2 + US1 deja garantizado el criterio del comportamiento 10 (escalar con motivo, no escalar un riesgo bajo sin hallazgos: C2).
- **Orden**: Phase 1 → 2 → US1 → US2 → US3 → Phase 6. Una sola revisión de código y una sola pasada de mutación al final.
