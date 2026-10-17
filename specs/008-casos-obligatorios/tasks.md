---
description: "Tareas de los casos de prueba obligatorios automatizados"
---

# Tasks: Casos de prueba obligatorios automatizados

**Input**: `specs/008-casos-obligatorios/` (plan.md, spec.md, research.md, contracts/casos.md, quickstart.md)

**Prerequisites**: plan.md y spec.md; constitución v1.1.1; tickets #1 a #6, #9 y #10 fusionados.

**Tests**: son el producto del ticket. **Regla de proceso**: el arnés (T002 a T004) se escribe con pruebas primero y se ven fallar. Los siete casos pasan al escribirlos (el comportamiento ya existe, #1 a #6): su valor se comprueba con mutaciones de sistema (T016), que deben hacerlos fallar. Las pruebas comprueban la regla y el motivo, no solo el resultado. Datos ficticios de `mcp_server/data/`; sin literales con forma de tarjeta, NIT o documento.

**Modelo de amenaza**: es el de #3 a #6; este ticket no añade garantías, las demuestra. Una sola revisión de código al final.

**Aprendido en #4 a #6**: reanclar las mutaciones existentes antes de añadir otras; una sola tarea edita cada archivo compartido; las pruebas de extremo a extremo que pasan al escribirse no cuentan como "vistas fallar" y se declara.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencia pendiente)
- **[Story]**: US1 los siete casos sin modelo · US2 ejecución con el modelo real · US3 documentación y mutaciones

## Phase 1: Setup

- [x] T001 Ejecutar `python -m pytest -q` en la rama y anotar la línea base (1.267 pruebas en verde en `main`) y que `ruff` está limpio, antes de tocar nada

## Phase 2: Foundational — el arnés (bloquea las historias)

- [x] T002 Escribir `due_diligence/tests/test_escenario.py` con las pruebas del arnés (deben fallar antes de T004): una llamada permitida se ejecuta con la función real del servidor y devuelve el sobre (`respuesta`) con `permitida` verdadera y sin regla; una rechazada por la regla 1 (listas sin registro previo) no se ejecuta, devuelve `permitida` falsa, la regla `1` y el motivo, y la respuesta es `None`; los hooks son los de `build_options` (si se desconecta el de reglas del `CaseBook`, la misma llamada se permite: se comprueba con un arnés construido sin él); el aislamiento por rol de producción rechaza a un subagente que llama a la herramienta de otro frente; `PostToolUse` recibe el sobre como texto JSON y alimenta el `CaseBook` (tras un registro unívoco, la consulta de listas de ese comercio se permite); `solicitud` ejecuta `UserPromptSubmit`; `parada` devuelve `{}` o el bloqueo del `Stop`; `registros("INF")` y `registros("ESC")` leen los archivos guardados en el directorio temporal; `faults` activa la inyección (`PASARELA_FAULTS=noticias` hace que noticias devuelva el error estructurado); el directorio temporal es distinto por prueba y `PASARELA_FAULTS` no se filtra a otras pruebas
- [x] T003 Ejecutar `python -m pytest -q due_diligence/tests/test_escenario.py` y comprobar que falla por la razón esperada (`escenario.py` no existe)
- [x] T004 Implementar `due_diligence/tests/escenario.py` (clase `Escenario`, `Resultado` y la tabla herramienta → función real y agente por defecto, según `contracts/casos.md`); comprobar que T002 pasa

## Phase 3: User Story 1 - Los siete casos sin modelo (Priority: P1) 🎯 MVP

**Goal**: cada caso del enunciado, de extremo a extremo y sin modelo, con su resultado exigido.

**Independent Test**: `pytest due_diligence/tests/test_casos_obligatorios.py` en verde sin clave.

- [x] T005 [US1] Escribir en `test_casos_obligatorios.py` el caso 1 (Tienda Verde SAS, `CO-TV-0001`): investigar por nombre con los cuatro frentes; `habilitar` rechazado por la regla `3`; la parada exige escalar una vez antes de escalar; el informe `escalar_a_cumplimiento` y el escalamiento con el resumen completo se aceptan y quedan registrados (`ESC-0001` con `causa` que nombra el riesgo y los hallazgos con fuente y fecha); tras escalar la parada deja cerrar
- [x] T006 [US1] Caso 2 (bajo riesgo sin hallazgos, `CO-LB-0002`): los cuatro frentes; escalar y recomendar escalar rechazados por la regla `escalamiento`; `habilitar` aceptado y registrado (`INF-0001` con `recomendacion` `habilitar`, fuente y fecha por hallazgo); la parada deja cerrar sin escalar
- [x] T007 [US1] Caso 3 (representante con coincidencia, `CO-DA-0003`): la consulta de listas de la persona `PE-0003` devuelve coincidencia; `habilitar` rechazado por la regla `2`; la parada exige escalar; el escalamiento con el hallazgo de `listas` y una causa que nombra la coincidencia se acepta y queda registrado; un escalamiento sin el hallazgo de listas se rechaza (`handoff_hallazgos`)
- [x] T008 [US1] Caso 4 (nombres casi idénticos): el registro devuelve `CO-CA-0004` y `CO-CA-0005` con `ambiguous`; la consulta de listas de cualquiera se rechaza (regla `1`); el informe y el escalamiento a nombre de cualquiera se rechazan (`ambiguedad`); tras consultar el registro por `CO-CA-0004` se identifica solo a él, sus listas se permiten y el informe se acepta, y `CO-CA-0005` sigue rechazado
- [x] T009 [US1] Caso 5 (listas sin identificación unívoca), en sus dos formas: sin ningún registro previo, la consulta de listas de `CO-TV-0001` se rechaza con la regla `1` y no llega al servidor; tras un resultado ambiguo del registro, la de cualquiera de los candidatos se rechaza; y la consulta de listas de una persona que no es representante de un comercio identificado se rechaza; tras un registro unívoco se permite
- [x] T010 [US1] Caso 6 (falla de noticias, `CO-LB-0002`, `PASARELA_FAULTS=noticias`): noticias devuelve el error estructurado reintentable; un reintento se permite y el tercer intento se rechaza (`reintento`); el informe que no declara `noticias` sin cubrir se rechaza (`cobertura`); el informe que la declara, con los hallazgos de los otros tres frentes, se acepta y queda registrado con la cobertura; con `noticias:no_reintentable` el reintento se rechaza; no se escala
- [x] T011 [US1] Caso 7 (fechas distintas, `CO-FH-0006`): el registro devuelve las dos fechas con su origen y `conflicts`; el informe con una sola fecha se rechaza (`conflicto`); el que declara ambas con su origen se acepta y queda registrado con `conflictos`; el mismo caso sin conflicto (otro comercio) no exige conflictos
- [x] T012 [US1] Ejecutar `python -m pytest -q due_diligence` y comprobar que los siete casos pasan, que las pruebas anteriores siguen en verde y que todo tarda menos de un minuto; anotar que los casos pasaron al escribirlos (D5)

## Phase 4: User Story 2 - Ejecución con el modelo real (Priority: P2)

- [x] T013 [US2] Escribir `due_diligence/tests/test_casos_reales.py` con las pruebas de las comprobaciones (fallan antes de T014), usando registros de llamadas grabados a mano, sin modelo: para cada uno de los siete casos, un registro que cumple devuelve lista vacía y uno que viola cada invariante devuelve el motivo (p. ej. caso 1 con un informe `habilitar` ejecutado, caso 2 con un escalamiento ejecutado, caso 4 con listas ejecutadas tras el resultado ambiguo, caso 6 sin la declaración de `noticias`, caso 7 con una sola fecha); `Registro` se construye desde la traza de reglas y los archivos guardados; los textos de la respuesta no influyen; un caso sin llamadas falla con el motivo "no hubo investigación"
- [x] T014 [US2] Implementar `due_diligence/casos_reales.py` (`Caso`, `Registro`, los siete casos con su mensaje y `faults`, las comprobaciones y la ejecución con `DueDiligenceSession` y hooks de observación añadidos a los de producción) y `scripts/run_casos.py` (una línea por caso, `--caso N`, `--salida DIR`, sin clave mensaje claro y código 2, `--usar-sesion-claude`); comprobar que T013 pasa y que sin clave no se llama al modelo (prueba con el entorno vacío)

## Phase 5: User Story 3 - Documentación y mutaciones (Priority: P2)

- [x] T015 [US3] Escribir `docs/CASOS.md`: una tabla con los siete casos (mensaje de ejemplo, datos, resultado exigido, prueba y comando para repetirlo con el modelo), cómo ejecutar las dos modalidades y qué se simula en la de pytest; comprobar con una prueba en `scripts/tests/` que cada caso del documento nombra una prueba existente
- [x] T016 [US3] Reanclar las 85 mutaciones existentes de `scripts/mutate_rules.py` si algún ancla cambió y añadir las mutaciones de sistema: desconectar el hook de reglas (`PreToolUse`) de `options.py`, desconectar el hook de parada, no observar los resultados (`PostToolUse`) y ignorar la inyección de fallas del servidor; cada una debe hacer fallar al menos un caso; ejecutar `python scripts/mutate_rules.py` y anotar el resultado

## Phase 6: Verificación y cierre

- [x] T017 Ejecutar con el modelo real `scripts/run_casos.py` (los siete casos, una corrida) y registrar en `specs/008-casos-obligatorios/verification.md` el resultado de cada caso, el motivo de los que fallen y cómo se repitieron; guardar la salida y los registros como evidencia
- [x] T018 [P] Actualizar `docs/TRAZABILIDAD.md` (C1 a C7 con la evidencia: la prueba sin modelo y la ejecución real; recontar el resumen) y `due_diligence/CLAUDE.md` (cómo ejecutar los casos), con `python scripts/verify_ecosystem.py` en verde
- [x] T019 Ejecutar `python -m pytest -q`, `ruff check .`, `ruff format --check .` y `python scripts/verify_ecosystem.py`; marcar las tareas; escribir el modelo de amenaza, la nota de revisión, los límites declarados y el recuento final en `verification.md`
- [x] T020 Una revisión de código independiente (`/abrir-pr 8`, `code-reviewer` y `compliance-reviewer`) con el modelo de amenaza escrito y pidiendo una entrada reproducible por hallazgo; corregir solo lo bloqueante o importante con entrada reproducible y registrar lo demás; abrir el PR con `Closes #8` tras confirmación de la persona

## Dependencies & Execution Order

- Phase 1 → Phase 2 (bloquea) → US1 → US2 → US3 → Phase 6. T005 a T011 editan el mismo archivo: se hacen en orden.
- T018 es paralela a lo demás (archivos distintos).

## Implementation Strategy

- **MVP**: Phase 2 + US1 (los siete casos sin modelo): es el criterio del issue ("pruebas que pasan los 7 casos").
- **Orden**: Phase 1 → 2 → US1 → US2 → US3 → Phase 6. Una sola revisión y una sola pasada de mutación al final.
