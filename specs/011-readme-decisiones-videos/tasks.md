---
description: "Tareas del README, DECISIONES.md, guion de video y zip de entrega"
---

# Tasks: README, DECISIONES.md, guion de video y zip de entrega

**Input**: `specs/011-readme-decisiones-videos/` (plan.md, spec.md, research.md, data-model.md, contracts/cli.md, contracts/documentos.md, quickstart.md)

**Prerequisites**: plan.md y spec.md; constitución v1.1.1; tickets #1 a #10 fusionados (también el #7, PR #23).

**Tests**: obligatorios (constitución VI). **Regla de proceso**: en cada historia primero se escriben las pruebas, se ejecutan y se comprueba que fallan por la razón esperada; después se implementa. Una prueba que solo mira un código de salida no prueba nada: comprueba también el mensaje o el efecto. Los valores con forma de credencial se **construyen en tiempo de ejecución**, nunca literales.

**Aprendido en #9**: la verificación por mutación de un comprobador es parte del trabajo, no un extra; y un comprobador cuyo detalle repite el valor que busca es peor que no tenerlo.

**Correcciones de `/speckit-analyze`** (aprobadas por la persona): I1 (`--final` también ejecuta `verify_docs`: fase 6), C1 (el contenido del zip se compara con el último commit: T004 y T007), C2 (revisión cruzada de DECISIONES.md: T016), I2 (plan), U1 (T014), A1 (T031), T1 (T003 partida en tres) y T2 (un commit por historia).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencia pendiente)
- **[Story]**: US1 el evaluador corre el sistema (README) · US2 el evaluador entiende las decisiones (DECISIONES.md) · US3 verificación del zip · US4 guion del video

## Phase 1: Setup

- [x] T001 Ejecutar `python -m uv run pytest -q`, `python -m uv run ruff check .`, `python -m uv run ruff format --check .` y `python scripts/verify_ecosystem.py` en la rama y anotar la línea base (1.528 pruebas en verde en `main`) en `specs/011-readme-decisiones-videos/verification.md`
- [x] T002 Añadir a `.gitignore` las líneas `dist/` y `*.zip` (el archivo de entrega nunca debe versionarse ni colarse en sí mismo)

## Phase 2: Foundational

Ninguna: los dos comprobadores son independientes entre sí y reutilizan `Check` de `scripts/verify_ecosystem.py`; no hay prerrequisito compartido que bloquee las historias.

## Phase 3: User Story 3 - Verificar el zip antes de entregarlo (Priority: P1) 🎯 MVP

**Goal**: `python scripts/verify_delivery.py` construye y verifica el zip de entrega y dice sin ambigüedad si cumple las reglas del enunciado.

**Independent Test**: un zip sintético con cada condición prohibida falla con su causa; el repositorio real pasa.

- [x] T003 [US3] Escribir en `scripts/tests/test_verify_delivery.py` las pruebas de **contenido y credenciales** (fallan antes de T007), con un repositorio git temporal sintético y zips armados con `zipfile`; cada prueba comprueba el nombre de la comprobación que falla **y** su detalle: (a) un árbol completo pasa todas las comprobaciones; (b) sin `.git/HEAD` o sin `.git/objects/` falla `CHECK_HISTORY`; (c) un miembro bajo `.venv/`, `venv/`, `node_modules/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `site-packages/` o un `.pyc` falla `CHECK_DEPENDENCIES` y el detalle nombra el miembro; (d) con el límite de tamaño bajado por parámetro, un zip mayor falla `CHECK_SIZE` con el tamaño y el desglose (`.git` y resto), y el límite por defecto es exactamente 50.000.000 bytes; (e) un `.env`, `.env.local`, `.env.production`, `x.pem`, `x.key`, `credentials.json`, `credentials-prod.json` o `id_rsa` falla `CHECK_SECRET_FILES`; `.env.example` con solo nombres pasa y con un valor falla; (f) un archivo de texto con una clave de Anthropic, un token de GitHub o un marcador de clave privada, **construidos en tiempo de ejecución** por partes, falla `CHECK_CREDENTIALS` y el detalle nombra el archivo pero no contiene el valor (se comprueba que la cadena construida no aparece en `detail`); un archivo binario o ilegible no rompe la comprobación; (g) una credencial confirmada en un commit y borrada en el siguiente falla `CHECK_HISTORY_CREDENTIALS` aunque el árbol actual esté limpio, y el detalle no repite el valor
- [x] T004 [US3] Añadir en `scripts/tests/test_verify_delivery.py` las pruebas de **coincidencia y empaquetado** (fallan antes de T007): (h) un archivo de más o de menos respecto de `git ls-tree -r HEAD` falla `CHECK_TREE` nombrándolo, y **un archivo versionado con cambios sin confirmar (mismo nombre, contenido distinto) también falla** nombrándolo; la diferencia solo de saltos de línea (`\r\n` frente a `\n`) no falla; (j) `--build` en el repositorio sintético: incluye `.git`, incluye los archivos versionados con una carpeta raíz con el nombre del repositorio y **no** incluye un `.venv/`, una caché ni un archivo de entorno local sin versionar que se hayan colocado a propósito, y escribe fuera del repositorio por defecto
- [x] T005 [US3] Añadir en `scripts/tests/test_verify_delivery.py` las pruebas de la **interfaz de línea de órdenes y del enlace** (fallan antes de T007): (i) con `--final`, un README con `PENDIENTE` o sin URL falla `CHECK_VIDEO` y con una URL `https://` y sin `PENDIENTE` pasa; sin `--final` esa comprobación no existe; (k) la CLI da código `0` con un árbol completo y `1` si falla una comprobación; código `2` y mensaje de uso sin `--zip` ni `--build`, con una ruta de zip inexistente y sin `git`; `--json` produce un objeto válido con `ok`, `tamano_bytes`, `desglose` y `checks`; el zip puede tener o no una carpeta raíz común
- [x] T006 [US3] Ejecutar `python -m uv run pytest scripts/tests/test_verify_delivery.py -q` y comprobar que falla por la razón esperada (`ModuleNotFoundError: verify_delivery`), no por un error de la prueba; anotarlo en `verification.md`
- [x] T007 [US3] Implementar `scripts/verify_delivery.py` según `contracts/cli.md` y `data-model.md` (solo biblioteca estándar; `Check` importado de `verify_ecosystem`): constantes `CHECK_*`, `ALL_CHECKS`, `build_zip(root, out)` con `git ls-files -z` más todo `.git` bajo una carpeta raíz con el nombre del repositorio, extracción a un directorio temporal, las comprobaciones R1 a R8 (R7 compara nombres y **contenido** con `git show HEAD:<ruta>`, normalizando saltos de línea; R8 solo con `--final` y con una función propia que lee el enlace del README), patrones de credenciales armados por partes, `main(argv)` con `--zip`, `--build`, `--out`, `--root`, `--final`, `--json` y los códigos 0/1/2; ningún detalle repite un valor encontrado
- [x] T008 [US3] Ejecutar las pruebas de T003 a T005 hasta que pasen; si una prueba nueva falla porque estaba mal y el comprobador bien, corregir la prueba y explicarlo en el commit
- [x] T009 [US3] Ejecutar `python scripts/verify_delivery.py --build` sobre el repositorio real (informativo: aún falta el README), marcar T001 a T009 y hacer el commit de la historia con el escaneo estricto de secretos y el mensaje en un archivo

**Checkpoint**: `python scripts/verify_delivery.py --build` funciona sobre el repositorio real y cada condición prohibida tiene su prueba.

## Phase 4: User Stories 1 y 2 - README y DECISIONES.md (Priority: P1)

**Goal**: un evaluador clona, corre y entiende el proyecto en dos documentos cortos y comprobables.

**Independent Test**: `python scripts/verify_docs.py` pasa sobre el repositorio real; los pasos del README se completan en menos de cinco minutos en una copia limpia.

- [x] T010 [US1] [US2] Escribir `scripts/tests/test_docs.py` (fallan antes de T012): con árboles sintéticos en un directorio temporal, un README y un DECISIONES.md válidos pasan todo; falla `CHECK_README` si falta el archivo o una sección obligatoria (qué es, requisitos, correr, pruebas, casos, enlaces, mapa, límites; sin distinguir mayúsculas); falla `CHECK_README_LINKS` sin la URL del GitHub Project; `CHECK_VIDEO_STATE` informa `pendiente` o `publicado` y falla si hay `PENDIENTE` y una URL a la vez o ninguna de las dos; falla `CHECK_PATHS` con una ruta citada que no existe (el detalle la nombra), y no falla con comandos con espacios, patrones con comodines ni rutas con fragmento `#`; falla `CHECK_DECISIONES_TABLE` con diez filas, con una fila repetida, con una celda vacía o con filas fuera del 1 al 11; falla `CHECK_DECISIONES_LENGTH` con más de 1000 palabras y **no cuenta** los bloques de código ni la sintaxis de Markdown (una tabla con exactamente 1000 palabras pasa y con 1001 falla); la interfaz de línea de órdenes da `0`/`1` y `--json` válido; y, contra el repositorio real, que `check_all(raíz)` no tenga ninguna falla (estas pruebas fallan hasta T014 y T015)
- [x] T011 [US1] [US2] Ejecutar las pruebas de T010 y comprobar que fallan por la razón esperada (`ModuleNotFoundError: verify_docs`; después, las del repositorio real porque no existen los documentos); anotarlo en `verification.md`
- [x] T012 [US1] [US2] Implementar `scripts/verify_docs.py` según `contracts/cli.md` y `contracts/documentos.md` (solo biblioteca estándar; `Check` importado de `verify_ecosystem`): constantes `CHECK_*`, `ALL_CHECKS`, `check_all(raíz)` y `main(argv)`; las rutas se extraen de los textos entre comillas invertidas con barra o con extensión conocida (`.md`, `.py`, `.json`, `.js`, `.html`, `.toml`), con fragmento `#` permitido y sin comillas ni comandos con espacios; el recuento de palabras ignora los bloques de código y la sintaxis de Markdown
- [x] T013 [US1] [US2] Ejecutar las pruebas sintéticas de T010 hasta que pasen
- [x] T014 [P] [US1] Escribir `README.md` en la raíz según `contracts/documentos.md`: qué es, requisitos, cómo correrlo (`python -m uv sync`, la clave como variable de entorno, `python -m uv run python -m due_diligence.web`, **`--puerto` si el puerto está ocupado y la diferencia entre PowerShell y Git Bash al definir la variable**), las pruebas (`python -m uv run pytest -q`, que no necesitan clave y que las de la página saltan sin Node), los siete casos (`docs/CASOS.md`, `docs/INTERFAZ.md`, `scripts/run_casos.py`), los enlaces (GitHub Project `https://github.com/users/Bryanzdruls/projects/4` y el video con `PENDIENTE`), el mapa de piezas y los límites conocidos (reglas 4 y 5 parciales en lo que muestra la interfaz, lo no verificado); todos los datos ficticios, ninguna clave
- [x] T015 [P] [US2] Escribir `DECISIONES.md` en la raíz según `contracts/documentos.md`: párrafo inicial, la tabla de las once necesidades con mecanismo, porqué y alternativa descartada, condensando `docs/ECOSISTEMA.md` y los `research.md` de los tickets #9 y #10 (cada fila cita al menos una ruta real), y la nota de límites en tres líneas como máximo; no más de 1000 palabras
- [x] T016 [US1] [US2] Ejecutar `python scripts/verify_docs.py` y `python -m uv run pytest scripts/tests/test_docs.py -q` hasta que todo pase sobre el repositorio real, corrigiendo los documentos y no relajando el comprobador; **hacer una revisión cruzada de DECISIONES.md contra `docs/ECOSISTEMA.md` y los `research.md` (cada fila contrastada con su fila de origen, sin contradicciones, sin decisiones inventadas) y registrar el resultado en `verification.md`**
- [x] T017 [US1] [US2] Marcar T010 a T017 y hacer el commit de la historia (escaneo estricto de secretos, mensaje en un archivo)

**Checkpoint**: README y DECISIONES.md existen, se comprueban solos y `pytest` los vigila.

## Phase 5: User Story 4 - Guion del video de funcionamiento (Priority: P2)

**Goal**: la persona graba el video de funcionamiento con un guion que cabe en cinco minutos y no expone secretos.

**Independent Test**: los tiempos suman cinco minutos como máximo, aparecen los siete casos con su identificador ficticio y el guion se ensaya una vez con el sistema real.

- [x] T018 [US4] Añadir a `scripts/tests/test_docs.py` las pruebas de `CHECK_GUION` (fallan antes de T020): un guion válido pasa; falla si los tiempos (`m:ss`) suman más de 5:00 (con exactamente 5:00 pasa y con 5:01 falla), si falta alguno de los casos 1 a 7, si a un caso le falta su identificador ficticio de `docs/CASOS.md`, o si falta el archivo; y, contra el repositorio real, que `docs/VIDEO.md` pase (fallará hasta T021)
- [x] T019 [US4] Ejecutar las pruebas nuevas de T018 y comprobar que fallan por la razón esperada
- [x] T020 [US4] Implementar `CHECK_GUION` en `scripts/verify_docs.py` (suma de tiempos de la tabla, siete casos, identificador de cada caso tomado de `docs/CASOS.md`) y comprobar que pasan las pruebas sintéticas de T018
- [x] T021 [US4] Escribir `docs/VIDEO.md` según `contracts/documentos.md`: lista previa de preparación (clave solo en el entorno, servidor en marcha, navegador limpio, conversación nueva por caso, nada de claves a la vista), la tabla de los siete casos con el mensaje de `docs/CASOS.md`, lo que debe verse y el tiempo de cada uno (introducción y cierre incluidos, total ≤ 5:00), "Qué no mostrar" y "Si el modelo varía"; ensayarlo una vez con el sistema real y ajustar los tiempos a lo medido
- [x] T022 [US4] Marcar T018 a T022 y hacer el commit de la historia (escaneo estricto de secretos, mensaje en un archivo)

**Checkpoint**: el guion está escrito, comprobado por máquina y ensayado.

## Phase 6: Verificación final única (FR-013, hallazgo I1)

**Goal**: una sola orden dice si se puede entregar: enlace del video real y todos los documentos en orden.

- [x] T023 [US3] Añadir en `scripts/tests/test_verify_delivery.py` las pruebas (fallan antes de T025): con `--final`, `verify_delivery` ejecuta además `verify_docs.check_all(raíz)`; si una comprobación de documentos falla (por ejemplo, una ruta citada inexistente), falla `CHECK_DOCS` y el detalle nombra cuál; sin `--final` no existe `CHECK_DOCS`; con todo en orden y el enlace publicado, el código de salida es `0`
- [x] T024 [US3] Ejecutar las pruebas nuevas de T023 y comprobar que fallan por la razón esperada
- [x] T025 [US3] Implementar `CHECK_DOCS` en `scripts/verify_delivery.py` (solo con `--final`, importando `verify_docs`); comprobar que pasan las pruebas de T023 y que las de T003 a T005 siguen pasando
- [ ] T026 [US3] Marcar T023 a T026 y hacer el commit de la historia (escaneo estricto de secretos, mensaje en un archivo)

## Phase 7: Polish & Cross-Cutting

- [x] T027 Medir SC-001 de verdad: clonar el repositorio (de la rama, con los documentos ya confirmados) a un directorio temporal, seguir los pasos del README tal cual (instalar, `pytest`, arrancar la interfaz y comprobar que responde) y registrar en `verification.md` el tiempo de cada paso y el total; si supera cinco minutos, acortar los pasos y declarar lo que se recortó
- [x] T028 Verificación por mutación de ambos comprobadores (un guion en el directorio temporal de la sesión, no versionado): romper a propósito cada comprobación de `verify_delivery.py` (no detectar el historial, no mirar `.venv`, subir el límite de tamaño, dejar pasar `.env.local`, no escanear el contenido, no escanear el historial, no comparar nombres, no comparar contenido, repetir el valor en el detalle, no ejecutar `verify_docs` con `--final`) y de `verify_docs.py` (no contar filas, contar el código como palabras, no comprobar rutas, aceptar `PENDIENTE` y URL a la vez, sumar mal los tiempos) y comprobar que alguna prueba falla; corregir lo que sobreviva
- [x] T029 Actualizar `docs/TRAZABILIDAD.md`: D2 y D3 a Hecho con su evidencia, D5 (zip) y D6 (video) con lo hecho y lo que queda en manos de la persona (grabar y publicar el video, subir el zip, invitar a los evaluadores, el video de defensa), la nota del ticket #11 y el resumen recalculado
- [x] T030 Ejecutar `python -m uv run pytest -q`, `python -m uv run ruff check .`, `python -m uv run ruff format --check .`, `python scripts/verify_ecosystem.py`, `python scripts/verify_docs.py` y `python scripts/verify_delivery.py --build` sobre el repositorio real; todo en verde y el zip real verificado
- [x] T031 Marcar las tareas y escribir en `specs/011-readme-decisiones-videos/verification.md` el recuento final, la medición de la copia limpia, las mutaciones y lo no verificado, **declarando que "dos páginas" se midió como 1000 palabras (un sustituto, sin generar un PDF)**
- [ ] T032 Una sola ronda de `/abrir-pr 11` (`code-reviewer` y `compliance-reviewer`) con el modelo de amenaza escrito (el comprobador del zip debe fallar cerrado: ante la duda, rechaza); corregir solo lo bloqueante o importante con entrada reproducible, declarar lo demás como pendiente y abrir el PR con `Closes #11` tras la confirmación de la persona

## Dependencies & Execution Order

- Phase 1 → US3 (T003 a T005 → T006 → T007 → T008 → T009) → US1/US2 (T010 → T011 → T012 → T013 → T014 y T015 en paralelo → T016 → T017) → US4 (T018 → T019 → T020 → T021 → T022) → Fase 6 (T023 → T024 → T025 → T026) → Polish.
- T003 a T005 editan el mismo archivo de pruebas: en orden, sin `[P]`. T018 y T020 editan archivos que ya crearon T010 y T012. La Fase 6 va después de US1/US2 porque `--final` importa `verify_docs`.
- T027 exige los documentos ya confirmados (la copia limpia sale de `git clone`); T028 exige ambos comprobadores terminados; T029 a T032 son el cierre.
- El video y el zip final los entrega la persona: el ticket no puede grabarlos ni subirlos.

## Implementation Strategy

- **MVP**: US3 es lo más grave (una credencial o un archivo de entorno en el zip invalida la entrega) y lo primero que se hace; US1 y US2 dan los dos documentos obligatorios; US4 allana la grabación; la Fase 6 reúne todo en una sola orden de verificación final.
- **Orden**: pruebas → verlas fallar → implementar → pasar → commit de la historia. Una sola revisión independiente al final.
- **Riesgo declarado**: SC-001 solo se demuestra con una medición real (T027); si falla, se acortan los pasos antes de dar el ticket por cerrado.
