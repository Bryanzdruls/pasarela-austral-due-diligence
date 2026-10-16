---
description: "Tareas de procedencia, conflictos entre fuentes y ambigüedad"
---

# Tasks: Procedencia, conflictos entre fuentes y ambigüedad

**Input**: `specs/005-procedencia-conflictos-ambiguedad/` (plan.md, spec.md, research.md, data-model.md, contracts/procedencia.md, quickstart.md)

**Prerequisites**: plan.md y spec.md; constitución v1.1.1; tickets #1, #2, #3, #4, #9 y #10 fusionados.

**Tests**: incluidos y obligatorios (constitución VI). **Regla de proceso**: en cada historia primero se escriben las pruebas, se ejecutan y se comprueba que fallan por la razón esperada, y solo entonces se implementa. Las pruebas comprueban el motivo del bloqueo y la regla, no solo que se bloquee. Los valores de ejemplo son ficticios (`CO-XX-000N`, `PE-000N`, fuentes terminadas en `_ficticio`/`_ficticia`).

**Modelo de amenaza**: igual que en el #3 y el #4: los hooks protegen contra descuidos del modelo y de los subagentes, no contra un adversario que controle el servidor o el proceso. Una sola revisión de código en la fase final.

**Forma real de la entrada**: `tool_response` de una herramienta MCP llega como **texto** con el sobre JSON (`{"ok":true,"content":{..},"metadata":{"source":..,"fetched_at":..}}`). Las pruebas usan esa forma. Las pruebas de este ticket viven en `due_diligence/tests/test_rules_procedencia.py` (archivo nuevo), con las ayudas de `test_rules.py` y `test_rules_cobertura.py`.

**Aprendido en el #4 (se aplica desde el principio)**: normalizar todo sujeto de comparación; probar que un éxito o un dato de un comercio no afecta a otro; probar el fallo cerrado de cada regla nueva; que cada mutación se reancle antes de añadir otras; y que `prompts.py` se edite en una sola tarea.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencia pendiente)
- **[Story]**: US1 procedencia de cada afirmación · US2 contradicciones entre fuentes · US3 nombres parecidos

## Phase 1: Setup

- [x] T001 Ejecutar `python -m pytest -q` en la rama y anotar la línea base (1.021 pruebas en verde en `main`) y que `ruff` está limpio, antes de tocar nada

## Phase 2: Foundational (bloquea las historias)

Lo que el `CaseBook` observa de las respuestas del servidor (data-model.md); lo leen las tres historias.

- [x] T002 Escribir en `due_diligence/tests/test_rules_procedencia.py` las pruebas de la observación (deben fallar antes de T004), con sobres de la forma real: cada respuesta `ok: true` de las cuatro fuentes guarda en `responded[frente]` su `metadata.source` normalizado y su `fetched_at`; una respuesta con error o ilegible no guarda nada; el registro guarda además el `source` de cada entrada de `fuentes_registro` de las coincidencias; `responded` persiste entre solicitudes y comercios; un registro unívoco con `conflicts: ["fecha_constitucion"]` y dos entradas de `fuentes_registro` con fechas distintas deja en `CommerceCase.conflictos` el dato con los dos pares (valor, fuente); sin `conflicts`, o con la misma fecha en las dos fuentes, no hay contradicción; un registro posterior vuelve a calcular las contradicciones (el último manda); un registro ambiguo (`ambiguous: true`, dos coincidencias) deja ambos `id` en `candidates` y no identifica a ninguno; un registro unívoco posterior de un candidato lo saca de `candidates` y lo deja identificado; `candidates` y `conflictos` persisten entre solicitudes; el conflicto de un comercio no aparece en otro; `observe` nunca lanza con entradas raras (`None`, listas, `matches` sin `id`, `fuentes_registro` mal formado)
- [x] T003 Ejecutar `python -m pytest -q due_diligence/tests/test_rules_procedencia.py` y comprobar que las pruebas de T002 fallan por la razón esperada (`responded`, `candidates` y `conflictos` no existen)
- [x] T004 Implementar en `due_diligence/rules.py`: `CaseBook.responded` y `CaseBook.candidates`, `CommerceCase.conflictos`, y en `observe` su alimentación desde las cuatro fuentes y desde el registro (`_observe_responded`, ampliación de `_observe_registro` para las contradicciones y los candidatos); comprobar que T002 pasa y que `due_diligence` sigue en verde

## Phase 3: User Story 2 - Los datos contradictorios se muestran juntos, con su origen (Priority: P1) 🎯 MVP

**Goal**: el informe de un comercio con una contradicción señalada por el servidor la declara con todos los valores y su origen (regla 4, caso C7).

**Independent Test**: con un comercio cuyo registro devolvió dos fechas de dos fuentes, el informe que las declara se acepta; el que da una sola fecha, no declara nada o omite un valor o su origen se rechaza nombrando el dato; sin contradicciones todo se acepta como antes.

- [x] T005 [US2] Escribir en `test_rules_procedencia.py` las pruebas de `conflicto` (fallan antes de T007): el informe sin `conflictos` o con la lista vacía se rechaza con la regla `conflicto`, nombrando el dato (`fecha_constitucion`) y los valores que faltan; con una sola fecha se rechaza; con el dato y los dos pares (valor, fuente) se acepta; con un par que omite la fuente o con la fuente de otro valor se rechaza; con valores de más se acepta; `dato` con espacios, tildes o mayúsculas (`Fecha de Constitución`) vale; `conflictos` de otra forma (texto, diccionario, lista de textos, `valores` que no es lista) no declara nada; el conflicto de otro comercio no se exige; un comercio sin contradicciones se acepta con `conflictos` vacío; el conflicto persiste: en una solicitud posterior se sigue exigiendo; el informe de un comercio no identificado no exige conflictos; falla cerrado: con el estado de contradicciones corrupto (excepción al leerlo) el hook deniega
- [x] T006 [US2] Ejecutar las pruebas de T005 y comprobar que fallan por la razón esperada
- [x] T007 [US2] Implementar en `rules.py` `_check_conflictos` (comparación normalizada de `dato`, `valor` y `fuente`, que contiene el nombre de la fuente) y su uso en `check_informe` después de `cobertura`, con el motivo de `contracts/procedencia.md` (qué dato, qué valores faltan, ejemplo de la forma); comprobar que T005 pasa y que el resto de `due_diligence` sigue en verde
- [x] T008 [US2] Escribir en `test_rule_hooks.py` las pruebas de extremo a extremo con la forma real (**protección contra regresiones**: pasarán al ejecutarlas porque `PreToolUse` ya llama a `check_informe`; no cuentan como "vistas fallar"): registro de `CO-XX-0001` con dos fechas observado por `PostToolUse`; `registrar_informe` con una sola fecha → denegado por `PreToolUse` nombrando el dato; con las dos → permitido; dos comercios, uno con conflicto, no se mezclan; la denegación queda en la traza con la regla `conflicto`
- [x] T009 [US2] Ajustar lo mínimo en `rule_hooks.py` si T008 lo exige; comprobar que `test_rule_hooks.py` pasa

## Phase 4: User Story 3 - Varios comercios con nombre parecido: se pide el identificador (Priority: P1)

**Goal**: mientras un candidato de un resultado ambiguo no esté identificado, no se registra ni se escala un informe a su nombre (caso C4).

**Independent Test**: con dos comercios de nombre casi idéntico, el informe o el escalamiento a nombre de cualquiera se rechaza; tras el identificador del analista, el comercio queda identificado y el informe se acepta; un nombre sin ambigüedad no cambia nada.

- [x] T010 [US3] Escribir en `test_rules_procedencia.py` las pruebas de `ambiguedad` (fallan antes de T012): con un registro ambiguo de `CO-XX-0004` y `CO-XX-0005`, `registrar_informe` y `escalar_a_cumplimiento` a nombre de cualquiera se rechazan con la regla `ambiguedad` y un motivo que manda pedir el identificador al analista nombrando los candidatos, con cualquier recomendación (`habilitar`, `no_habilitar`, `escalar_a_cumplimiento`); tras un registro unívoco por identificador de `CO-XX-0004`, su informe se acepta y el de `CO-XX-0005` sigue rechazado; el estado persiste en la solicitud siguiente; un comercio que no es candidato (p. ej. el registro caído, caso del #4) se sigue aceptando; un registro unívoco sin ambigüedad no genera candidatos; la regla va antes que `cobertura` y que las reglas 2 y 3 (orden de `contracts/procedencia.md`); una consulta ambigua con un solo `id` legible registra solo ese; falla cerrado ante `candidates` corrupto
- [x] T011 [US3] Ejecutar las pruebas de T010 y comprobar que fallan por la razón esperada
- [x] T012 [US3] Implementar en `rules.py` `_check_ambiguedad` y su uso al principio de `check_informe` (después del vocabulario) y de `check_escalar`, con el motivo de `contracts/procedencia.md`; comprobar que T010 pasa y que el resto de `due_diligence` sigue en verde
- [x] T013 [US3] Escribir en `test_rule_hooks.py` las pruebas de extremo a extremo (protección contra regresiones, como T008): registro ambiguo observado por `PostToolUse`, informe a nombre de un candidato denegado por `PreToolUse` y también el escalamiento; tras el registro por identificador, permitido; los cuatro tipos de recomendación; la traza con la regla `ambiguedad`; el `Stop` no cambia
- [x] T014 [US3] Ajustar lo mínimo en `rule_hooks.py` si T013 lo exige; comprobar que `test_rule_hooks.py` pasa

## Phase 5: User Story 1 - Cada afirmación lleva la fuente que de verdad respondió (Priority: P1)

**Goal**: cada hallazgo de un frente cita una fuente que respondió y su fecha; si no, el informe o el escalamiento no se registra.

**Independent Test**: informes que citan la fuente real se aceptan; los que citan una fuente no consultada, la de otro frente, ninguna o sin fecha se rechazan; los frentes declarados sin cubrir quedan exentos.

- [x] T015 [US1] Escribir en `test_rules_procedencia.py` las pruebas de `procedencia` (fallan antes de T017): hallazgo de registro que cita `registro_mercantil_ficticio` con `fecha` se acepta; con una fuente que no se consultó se rechaza con la regla `procedencia` nombrando el frente y la fuente que sí consta; con la fuente de otro frente (listas en noticias) se rechaza; sin `fuente` o sin fecha se rechaza; la fecha vale en `fecha`, `fecha_consulta` y `fetched_at`; la fuente con decoración (`registro_mercantil_ficticio (2026-10-16)`) y en mayúsculas o con tildes vale; una lista de fuentes vale si cada elemento respondió y no vale si uno no; una fuente de `fuentes_registro` (`camara_comercio_alterna_ficticia`) vale en el frente de registro; las alias de frente de los subagentes (`registro_mercantil`, `riesgo_categoria`) se comprueban igual; las claves que no son un frente (`datos_del_analista`) no se comprueban; un frente declarado `sin_cubrir` queda exento aunque tenga un hallazgo; un frente que falló y no se declaró se rechaza por `cobertura` (#4) antes que por `procedencia`; un hallazgo de un frente que nunca respondió ni falló se rechaza con el motivo "no hay respuesta de esa fuente"; `hallazgos` que no es un diccionario o con valores que no lo son se rechazan sin lanzar; `escalar_a_cumplimiento` exige lo mismo; un informe sin hallazgos de frente se acepta como antes; falla cerrado ante `responded` corrupto
- [x] T016 [US1] Ejecutar las pruebas de T015 y comprobar que fallan por la razón esperada; ejecutar también `python -m pytest -q due_diligence` y listar las pruebas del #3 y #4 que dejan de pasar por la regla nueva (se ajustan en T017)
- [x] T017 [US1] Implementar en `rules.py` `_check_procedencia` (D2 a D4) y su uso en `check_informe` y `check_escalar` después de `cobertura`; sembrar la respuesta de la fuente con una ayuda de prueba en las pruebas del #3 y el #4 que lo necesiten, anotando cada ajuste aquí; comprobar que T015 pasa y que todo `due_diligence` sigue en verde
- [x] T018 [US1] Escribir en `test_rule_hooks.py` las pruebas de extremo a extremo (protección contra regresiones, como T008): una respuesta de noticias observada por `PostToolUse` y un informe que cita noticias con su fecha → permitido; que cita una fuente no consultada → denegado nombrando el frente; el escalamiento igual; la traza con la regla `procedencia`
- [x] T019 [US1] Ajustar lo mínimo en `rule_hooks.py` si T018 lo exige; comprobar que `test_rule_hooks.py` pasa

## Phase 6: Prompts, servidor y verificación

- [x] T020 Escribir en `due_diligence/tests/test_prompts.py` las pruebas (fallan antes de T021): el prompt del coordinador describe `hallazgos` con `fuente` y `fecha` por frente y **lista los cuatro nombres exactos de fuente** (`registro_mercantil_ficticio`, `listas_restrictivas_ficticias`, `noticias_ficticias`, `catalogo_riesgo_ficticio`, los mismos que las constantes del servidor y `EXPECTED_SOURCES`, con una prueba de que coinciden) y la clave `fecha`; el formato de `conflictos` con `dato` y `valores` (valor y fuente) y dice mostrar todos los valores sin elegir uno ni presentar uno como el correcto; dice que ante varios comercios que coinciden muestra los candidatos con su identificador y lo que los distingue, pide el identificador y no lanza más frentes; que el informe de un comercio sin identificar no se registra; que las contradicciones entre frentes distintos (noticia frente al registro) también se muestran juntas; y mantiene lo que ya decía (vocabulario, cobertura, hooks y regla 5); el prompt del subagente de registro dice incluir todas las fechas con su origen
- [x] T021 Actualizar `due_diligence/prompts.py` (única tarea que lo edita) y `mcp_server/tools/informes.py` (descripción de `registrar_informe`: forma de `hallazgos` y `conflictos`) con su prueba en `mcp_server/tests/test_server.py`; comprobar que T020 pasa y que `mcp_server` sigue en verde
- [x] T022 Ampliar `scripts/mutate_rules.py`: primero comprobar que las 39 mutaciones existentes siguen aplicando (T004, T007, T012 y T017 cambian código donde anclan) y reanclar las que no; añadir las de este ticket, cada una detectada: no observar las fuentes respondidas; aceptar una fuente que no respondió; aceptar la fuente de otro frente; no exigir la fecha; no exigir la fuente de las claves de frente; no eximir el frente declarado sin cubrir; eximir todo frente de la comprobación; no registrar contradicciones; ignorar un valor del conflicto; ignorar la fuente de un valor; aceptar `conflictos` vacío; el conflicto de un comercio se exige en otro; `dato` sin normalizar; no registrar candidatos; no sacarlos al identificar al comercio; los candidatos no persisten entre solicitudes; `ambiguedad` solo para `habilitar`; `ambiguedad` solo en el informe y no en el escalamiento; escalar sin `procedencia`; ejecutar `python scripts/mutate_rules.py` y anotar el resultado
- [x] T023 [P] Actualizar `due_diligence/CLAUDE.md` (regla 4 por hook, procedencia, conflictos y candidatos) y `docs/TRAZABILIDAD.md` (R4, B8, B9, C4 y C7 con la evidencia y el estado "En rama" hasta la fusión; recontar el resumen), con `python scripts/verify_ecosystem.py` en verde
- [x] T024 Verificación con el modelo real según `quickstart.md` (los siete casos más el 3b, una corrida cada uno; registrar cuántas denegaciones de `procedencia` hubo antes de la primera aceptación y qué las causó; los cuatro de rechazo con un prompt de sistema de prueba que ordena violar la regla, como en el #3 y el #4) y registrar en `specs/005-procedencia-conflictos-ambiguedad/verification.md` qué hizo el modelo, los rechazos de los hooks (`PASARELA_HOOK_TRACE`), los ajustes de pruebas del #3 y el #4 y lo no verificado (incluido el caso 3b: un identificador que no corresponde a ningún candidato); guardar la evidencia como en el #4
- [x] T025 Ejecutar `python -m pytest -q`, `ruff check .`, `ruff format --check .` y `python scripts/verify_ecosystem.py`; marcar las tareas; escribir el modelo de amenaza, la nota de revisión y el recuento final en `verification.md`, con los límites declarados: la presentación al analista (FR-007 y FR-008) y la atención a los candidatos (FR-010) solo se orientan por prompt y se verifican con el modelo real; las fuentes respondidas son de toda la conversación y no por comercio (un comercio podría citar un origen que consultó otro); las contradicciones entre frentes no las señala el servidor; el escalamiento no lleva conflictos (#6)
- [ ] T026 Una revisión de código independiente (`/abrir-pr 5`, `code-reviewer` y `compliance-reviewer`) sobre el diff, con el modelo de amenaza escrito y pidiendo una entrada reproducible por hallazgo; corregir solo lo bloqueante o importante con entrada reproducible y registrar lo demás; abrir el PR con `Closes #5` tras confirmación de la persona

## Dependencies & Execution Order

- Phase 1 → Phase 2 (bloquea) → US2, US3 y US1 (independientes entre sí tras la Phase 2) → Phase 6.
- Dentro de cada historia: pruebas → verlas fallar → implementar → pruebas de extremo a extremo → verlas pasar.
- Las tres historias editan `rules.py` (`check_informe` y `check_escalar`): se hacen en el orden propuesto, no en paralelo.
- T023 es paralela a lo demás (archivos distintos). T021 es la única que edita `prompts.py`.

## Implementation Strategy

- **MVP**: Phase 2 + US2 deja la regla 4 (contradicciones con su origen, caso C7) garantizada; es lo que el enunciado nombra expresamente.
- **Orden propuesto**: Phase 1 → 2 → US2 → US3 → US1 → Phase 6. US1 va al final porque es la que más pruebas anteriores toca (D10).
- Una sola revisión de código y una sola pasada de mutación al final (sin bucles de revisión).
