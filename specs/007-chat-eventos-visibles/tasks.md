---
description: "Tareas de la interfaz de chat con eventos visibles"
---

# Tasks: Interfaz de chat con eventos visibles

**Input**: `specs/007-chat-eventos-visibles/` (plan.md, spec.md, research.md, contracts/web.md, quickstart.md)

**Prerequisites**: plan.md y spec.md; constitución v1.1.1; tickets #1 a #6, #8, #9 y #10 fusionados.

**Tests**: incluidos y obligatorios (constitución VI). **Regla de proceso**: en cada historia primero se escriben las pruebas, se ejecutan y se comprueba que fallan por la razón esperada, y solo entonces se implementa. Las pruebas comprueban el efecto (el evento y su texto), no solo el código de estado. Ninguna llama al modelo. Datos ficticios.

**Modelo de amenaza**: la interfaz es local y muestra texto de un modelo y de fuentes: debe tratarlo siempre como texto y no ejecutarlo; no tiene autenticación (solo `127.0.0.1`). No protege contra un usuario con acceso a la máquina. Una sola revisión de código al final.

**Aprendido en #4 a #8**: reanclar las mutaciones existentes antes de añadir otras (aquí solo se toca `rule_hooks.py` y `options.py` con una llamada opcional); una sola tarea edita cada archivo compartido; las pruebas que pasan al escribirse se declaran.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencia pendiente)
- **[Story]**: US1 conversar y ver los turnos · US2 eventos visibles y entendibles · US3 arranque local y seguro

## Phase 1: Setup

- [x] T001 Ejecutar `python -m pytest -q` en la rama y anotar la línea base (1.344 pruebas en verde en `main`) y que `ruff` está limpio; declarar `starlette`, `uvicorn` y `sse-starlette` en `pyproject.toml` y `httpx` en el grupo `dev`, y regenerar `uv.lock` si `uv` está disponible (si no, anotarlo)

## Phase 2: Foundational — eventos y observaciones (bloquea las historias)

- [x] T002 Escribir pruebas (fallan antes de T004): en `due_diligence/tests/test_events.py`, los tres eventos nuevos (`CallBlocked`, `ReportRegistered`, `Escalated`) son inmutables, llevan marca de tiempo y forman parte de `DomainEvent`; en `due_diligence/tests/test_rule_hooks.py`, `make_pre_tool_use(book, on_decision=...)` llama a `on_decision(input_data, decision)` solo en los rechazos y con la regla y el motivo reales (regla 1 sin registro, `escalamiento`), no en las llamadas permitidas, un `on_decision` que lanza no cambia la decisión ni la hace permitir, y sin `on_decision` el comportamiento es idéntico; en `test_options.py`, `build_options(book, on_decision)` lo pasa al hook de reglas
- [x] T003 Ejecutar las pruebas de T002 y comprobar que fallan por la razón esperada
- [x] T004 Implementar los tres eventos en `due_diligence/events.py`, el parámetro opcional `on_decision` en `make_pre_tool_use` (`rule_hooks.py`) y en `build_options`/`_hooks` (`options.py`); renderizar los eventos nuevos en la consola (`__main__.py`, con su prueba en `test_main.py`); comprobar que T002 pasa y que `due_diligence` sigue en verde
- [x] T005 Escribir en `due_diligence/web/tests/test_observadores.py` las pruebas de los observadores (fallan antes de T006): el hook `PostToolUse` observador emite `ReportRegistered` solo cuando `registrar_informe` devuelve `ok: true` (con el `informe_id` del servidor, el comercio y la recomendación de la entrada) y `Escalated` cuando `escalar_a_cumplimiento` devuelve `ok: true` (con su `escalamiento_id` y la causa); una respuesta con error, ilegible o de otra herramienta no emite nada; el nombre completo de la herramienta (`mcp__pasarela-fuentes__...`) y el corto valen; un `emit` que falla no rompe el hook; `a_bloqueo(emit)` convierte la decisión rechazada en `CallBlocked` con el agente, la herramienta, la regla y el motivo
- [x] T006 Implementar `due_diligence/web/observadores.py` (`observador_post(emit)` y `observador_bloqueo(emit)`); comprobar que T005 pasa

## Phase 3: User Story 2 - Eventos visibles y entendibles (Priority: P1) 🎯 MVP

**Goal**: cada hecho del issue se convierte en una tarjeta en lenguaje llano.

**Independent Test**: la vista de cada evento tiene tipo, título, detalle y hora, sin términos internos, y el texto de muestra se escapa.

- [x] T007 [US2] Escribir en `due_diligence/web/tests/test_vista.py` las pruebas (fallan antes de T008): mensaje del analista y respuesta del coordinador (`analista`, `coordinador`); delegación (`delegacion`: "Delegó en el registro mercantil" con el encargo); resultado de un frente completo, fallido (con si es reintentable y lo obtenido) y sin estructura (`resultado`); bloqueo con la regla traducida a palabras para cada regla (`1`, `2`, `3`, `ambiguedad`, `cobertura`, `cobertura_habilitar`, `procedencia`, `conflicto`, `escalamiento`, `handoff_hallazgos`, `handoff_causa`, `reintento`, `vocabulario`, `identificacion`, `aislamiento`) y el motivo literal en el detalle (`bloqueo`); informe con número, comercio y recomendación (`informe`); escalamiento con número, comercio y causa (`escalamiento`); fin del turno con su razón y error (`fin`, `error`); ningún título ni detalle usa solo el nombre de una herramienta o un identificador de hook; todas llevan hora; una regla desconocida se muestra con un texto genérico y no falla; el contenido con `<script>` queda como texto en el dato (la página lo inserta con `textContent`, ver T015)
- [x] T008 [US2] Implementar `due_diligence/web/vista.py` (`a_vista(evento, n)` y la tabla de reglas en palabras); comprobar que T007 pasa

## Phase 4: User Story 1 - Conversar y ver los turnos (Priority: P1)

**Goal**: una conversación con turnos en orden, contexto entre turnos, un turno a la vez e historial reproducible.

**Independent Test**: con el cliente falso, dos turnos producen el flujo completo de eventos en orden con la misma sesión.

- [x] T009 [US1] Escribir en `due_diligence/web/tests/test_conversacion.py` las pruebas con el cliente falso (fallan antes de T010): un turno publica el mensaje del analista, la delegación y su resultado, el texto del coordinador y el `fin`, con `n` consecutivo; dos turnos reutilizan la misma sesión (el cliente falso se abre una vez); un segundo mensaje con el turno en curso se rechaza con `TurnoEnCurso`; un suscriptor tardío recibe el historial completo y después los eventos en vivo; dos suscriptores ven lo mismo; una excepción de la sesión publica un `error` legible y la conversación sigue utilizable (un turno nuevo funciona); los observadores publican en orden los bloqueos, el informe y el escalamiento entre los eventos del turno; el texto vacío o de más de 4000 caracteres se rechaza; `cerrar()` cierra la sesión
- [x] T010 [US1] Implementar `due_diligence/web/conversacion.py` (`Conversacion`, `TurnoEnCurso`, la cola por suscriptor, el historial y el turno único) usando `DueDiligenceSession` con las opciones de `build_options(book, on_decision)` y los observadores; comprobar que T009 pasa
- [x] T011 [US1] Escribir en `due_diligence/web/tests/test_app.py` las pruebas de la aplicación con `TestClient` y el cliente falso (fallan antes de T012): `GET /api/estado` responde sin modelo; `POST /api/conversaciones` crea (201) y devuelve un id; `POST .../mensajes` responde 202 y arranca el turno, 409 con un turno en curso, 422 con texto vacío o largo, 404 con una conversación inexistente o un id mal formado; `GET .../eventos?hasta_fin=1` entrega el historial y cierra en el `fin`, en formato SSE con `data:` JSON del contrato; una recarga (segunda conexión) recibe el mismo historial; `GET /` devuelve la página con el tipo de contenido HTML; las rutas desconocidas dan 404; la aplicación no expone el cuerpo de una excepción interna
- [x] T012 [US1] Implementar `due_diligence/web/app.py` (`crear_app(fabrica_sesion=None)`: rutas del contrato, validación, SSE con `sse-starlette`, cierre de las conversaciones al apagar); comprobar que T011 pasa

## Phase 5: User Story 3 - Arranque simple, local y seguro (Priority: P2)

- [x] T013 [US3] Escribir en `due_diligence/web/tests/test_arranque.py` las pruebas (fallan antes de T014): `python -m due_diligence.web` escucha por defecto solo en `127.0.0.1` (la función de arranque pasa ese host a `uvicorn`, con una prueba que sustituye `uvicorn.run`), indica la dirección en la salida, rechaza `--host` que no sea local salvo con una bandera explícita, y sin `ANTHROPIC_API_KEY` avisa pero arranca (el error se muestra al enviar un mensaje)
- [x] T014 [US3] Implementar `due_diligence/web/__main__.py` (argumentos `--puerto` y `--host`, aviso de la clave, `uvicorn.run(crear_app(), host, port)`); comprobar que T013 pasa
- [x] T015 [US3] Escribir `due_diligence/web/static/index.html` (conversación, tarjetas por tipo con icono y etiqueta, indicador de trabajo, formulario, `EventSource` al flujo de eventos, reconexión que recupera el historial, todo el texto con `textContent`) y una prueba en `test_pagina.py` que comprueba que la página no usa `innerHTML` ni `eval`, usa `textContent`, abre un `EventSource` a la ruta del contrato y define los nueve tipos de evento del contrato

## Phase 6: Documentación, verificación y cierre

- [x] T016 [P] Escribir `docs/INTERFAZ.md` (cómo arrancarla, qué se ve, qué significa cada tipo de evento y cómo recorrer los siete casos en ella) y actualizar `due_diligence/CLAUDE.md` y `docs/TRAZABILIDAD.md` (B12 y la fila D6 en lo que dependa de la interfaz; recontar el resumen), con `python scripts/verify_ecosystem.py` en verde
- [x] T017 Verificación con el modelo real: arrancar la interfaz y recorrer los siete casos de `docs/CASOS.md` (se envía cada mensaje con la API de la propia interfaz, igual que lo haría el navegador, y se lee el flujo de eventos), registrando en `specs/007-chat-eventos-visibles/verification.md` el evento que aparece en cada caso y cuántos eventos de cada tipo; guardar el flujo como evidencia; si es posible, una descripción literal de lo que vería una persona; declarar lo no verificado (el aspecto visual en un navegador real, si no se pudo abrir)
- [x] T018 Ejecutar `python -m pytest -q`, `ruff check .`, `ruff format --check .`, `python scripts/verify_ecosystem.py` y `python scripts/mutate_rules.py`; marcar las tareas; escribir el modelo de amenaza, la nota de revisión, los límites declarados y el recuento final en `verification.md`
- [x] T019 Una revisión de código independiente (`/abrir-pr 7`, `code-reviewer` y `compliance-reviewer`) con el modelo de amenaza escrito y pidiendo una entrada reproducible por hallazgo; corregir solo lo bloqueante o importante con entrada reproducible y registrar lo demás; abrir el PR con `Closes #7` tras confirmación de la persona

## Phase 7: Mejoras tras la QA con el modelo real (FR-013 a FR-016)

**Origen**: una QA de la interfaz con el modelo real (casos 1 y 4 y un intento de saltarse la regla 1) halló que la respuesta del coordinador mostraba Markdown sin interpretar, que las tarjetas de resultado solo decían la fuente y la fecha, que el campo de mensaje flotaba a mitad de pantalla con la conversación vacía y que enviar vacío no avisaba. Pruebas primero, y se ven fallar.

- [x] T020 [P] Escribir `due_diligence/web/tests/test_markdown.py` (fallan antes de T021): `a_bloques(texto)` convierte títulos, párrafos, listas con viñeta y numeradas, tablas, separadores, negrita y código en bloques de datos; un texto sin formato da un solo párrafo; el marcado HTML, los enlaces y las imágenes se quedan como texto; una tabla mal formada no rompe; entrada vacía o enorme da una lista acotada
- [x] T021 Implementar `due_diligence/web/markdown.py` (analizador pequeño que produce bloques, nunca HTML); comprobar que T020 pasa
- [x] T022 [P] Escribir las pruebas de FR-013 y FR-014 en `test_vista.py` y `test_observadores.py` (fallan antes de T023): la tarjeta del coordinador lleva `extra.bloques`; el observador publica un `FrontFinding` por cada respuesta `ok: true` de las cuatro fuentes (registro con uno, con varios y con ninguno; listas con y sin coincidencia; noticias con y sin menciones; riesgo) y ninguno si el servidor falló o el sobre es ilegible; la vista del hallazgo no repite datos internos y observar nunca lanza
- [x] T023 Implementar `FrontFinding` en `due_diligence/events.py`, su resumen en `observadores.py` y su tarjeta (`hallazgo`) y los bloques del coordinador en `vista.py`; actualizar `contracts/web.md`; comprobar que T022 pasa
- [x] T024 Escribir en `test_pagina.py` las pruebas de FR-013 a FR-016 (fallan antes de T025): la página dibuja los bloques con `createElement`/`textContent` sin `innerHTML`, define el tipo `hallazgo`, ancla el formulario abajo y avisa al enviar vacío
- [x] T025 Implementar los cambios de `index.html`; comprobar que T024 pasa y que las pruebas de T015 siguen pasando
- [x] T026 Verificar en un navegador con el modelo real (casos 1 y 4), repetir la verificación por mutación sobre lo nuevo y registrar el resultado y lo no verificado en `verification.md`
- [x] T027 Ejecutar `python -m pytest -q`, `ruff check .`, `ruff format --check .` y `python scripts/verify_ecosystem.py`; actualizar `docs/INTERFAZ.md`
- [x] T028 Corregir la pérdida del historial al recargar (FR-007), hallada por el usuario: al descargarse la página, el navegador cierra el flujo de eventos y avisa con un error; la página lo tomaba por una conversación desaparecida, borraba la guardada y creaba otra. Prueba primero (`test_pagina_comportamiento.py`, que ejecuta el script real de la página con Node y un navegador simulado) y verla fallar por esa razón; la página cierra su propio flujo al descargarse (`pagehide`/`beforeunload`), ignora el error mientras se descarga y se reconecta si el navegador la restaura (`pageshow`); el 404 sigue empezando otra conversación

## Dependencies & Execution Order

- Phase 1 → Phase 2 (bloquea) → US2 → US1 → US3 → Phase 6. T002 a T004 editan archivos compartidos (`events.py`, `rule_hooks.py`, `options.py`, `__main__.py`): una sola vez y en orden. T016 es paralela a lo demás.

## Implementation Strategy

- **MVP**: Phase 2 + US2 + US1 dejan la conversación y los eventos visibles, que es el criterio del issue; la US3 completa el arranque y la seguridad.
- **Orden**: Phase 1 → 2 → US2 → US1 → US3 → Phase 6. Una sola revisión y una sola pasada de mutación al final.
