---
description: "Tareas de la automatización del GitHub Project y el plugin reutilizable"
---

# Tasks: Automatización del GitHub Project y plugin reutilizable

**Input**: `specs/010-automatizacion-project-plugin/` (plan.md, spec.md, research.md, data-model.md, contracts/flujo-tickets.md, contracts/plugin.md, quickstart.md)

**Prerequisites**: plan.md y spec.md; constitución v1.1.1; ticket #9 fusionado (hooks, subagentes, skills y verificador ya en `main`).

**Orden de tickets (constitución v1.1.1)**: #9 → #10 → #2. Este ticket cierra el ecosistema; ningún ticket de funcionalidad se fusiona antes.

**Tests**: incluidos y obligatorios (constitución VI). **Regla de proceso**: en cada historia primero se escriben las pruebas, se ejecutan y se comprueba que fallan por la razón esperada, y solo entonces se implementa. Las pruebas comprueban el código de salida *y* el mensaje o el efecto, no solo el código.

**Reglas de redacción**: los textos de ejemplo, pruebas y documentos no escriben el nombre literal de archivos de entorno ni de secretos (se arma por partes o se describe), y los valores con forma de tarjeta, NIT o documento se generan en tiempo de ejecución con los ayudantes de `.claude/hooks/tests/helpers.py`.

**Modelo de amenaza**: los hooks del plugin son barreras contra descuidos del asistente, no contra ofuscación deliberada. Una sola revisión independiente en la fase final.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencia pendiente)
- **[Story]**: US1 siguiente-ticket · US2 sincronizar-tickets y `/abrir-pr` hasta Done · US3 plugin y catálogo · US4 verificador, inventario y documentación

## Phase 1: Setup

- [x] T001 Añadir `plugins/pasarela-revision/tests` a `testpaths` en `pyproject.toml` y comprobar que pytest recoge una prueba trivial colocada ahí (y que no entra en conflicto con otros `conftest.py`)
- [x] T002 [P] Crear la estructura vacía: `plugins/pasarela-revision/{.claude-plugin,agents,skills/revisar-cumplimiento,hooks,tests}/`, `.claude-plugin/` y `.claude/skills/{siguiente-ticket,sincronizar-tickets}/`

## Phase 2: Foundational (bloquea las historias)

- [x] T003 Comprobar en esta sesión que existen las herramientas MCP que usarán las skills (`mcp__github__projects_list`, `mcp__github__projects_write`, `mcp__github__issue_read`, `mcp__github__add_issue_comment`, `mcp__github__list_pull_requests`, `mcp__github__pull_request_read`) y anotar sus nombres exactos y los de las opciones de `Status` (`Todo`, `In Progress`, `In review`, `Done`) al final de `specs/010-automatizacion-project-plugin/contracts/flujo-tickets.md`, en una sección **Nombres verificados**

## Phase 3: User Story 1 - Tomar el siguiente ticket (Priority: P1) 🎯 MVP

**Goal**: `/siguiente-ticket` elige el siguiente ticket por el orden definido, lo pasa a `In Progress` y entrega su contenido como insumo de la especificación.

**Independent Test**: sobre el Project real, ejecutar la skill y comprobar el ticket elegido y su cambio de estado; con un ticket ya en progreso, comprobar que pide confirmación.

- [x] T004 [US1] Escribir `scripts/tests/test_flow_skills.py` con pruebas de `.claude/skills/siguiente-ticket/SKILL.md` (deben fallar antes de T005): existe; frontmatter con `name`, `description`, `allowed-tools` y `argument-hint`; `allowed-tools` incluye `mcp__github__projects_list`, `mcp__github__projects_write` y `mcp__github__issue_read` y **no** incluye `Edit`, `Write` ni `Bash` sin argumento; el cuerpo nombra los cuatro estados exactos (`Todo`, `In Progress`, `In review`, `Done`), el orden (#9 y #10 primero, luego por número), la confirmación si hay un ticket en progreso y el aviso si el servidor o el toolset no están disponibles
- [x] T005 [US1] Ejecutar `python -m pytest -q scripts/tests/test_flow_skills.py` y comprobar que falla por la razón esperada (la skill no existe)
- [x] T006 [US1] Crear `.claude/skills/siguiente-ticket/SKILL.md` según `contracts/flujo-tickets.md`: ejecuta primero la sincronización, aplica el orden de `data-model.md`, pasa el ticket a `In Progress` con `mcp__github__projects_write`, muestra título y contenido como insumo de `/speckit-specify`, pide confirmación si ya hay uno en progreso o si el elegido depende de uno abierto, y se detiene sin modificar nada si el servidor o el toolset no están disponibles
- [x] T007 [US1] Ejecutar las pruebas de T004 y comprobar que pasan

## Phase 4: User Story 2 - El estado refleja el avance hasta Done (Priority: P1)

**Goal**: `/abrir-pr` deja el ticket en `In review` con un comentario de avance de tres partes y `/sincronizar-tickets` pasa a `Done` los fusionados, de forma idempotente.

**Independent Test**: con el estado real del Project, ejecutar `/sincronizar-tickets` dos veces; la segunda no cambia nada. Con un pull request fusionado en `In review`, pasa a `Done`.

- [x] T008 [US2] Ampliar `scripts/tests/test_flow_skills.py` con pruebas de `.claude/skills/sincronizar-tickets/SKILL.md` y de `.claude/commands/abrir-pr.md` (deben fallar antes de T010 y T011): la skill existe con `allowed-tools` de lectura del Project y de pull requests más `mcp__github__projects_write`, sin herramientas de escritura de archivos; su cuerpo describe las transiciones de `data-model.md`, que un pull request cerrado sin fusionar no cambia nada, que es idempotente y que informa cada cambio; el comando exige el comentario con las secciones **Especificado**, **Decidido** y **Pendiente**, el paso a `In review` por `mcp__github__projects_write` y la parada explícita si el servidor o el toolset no están disponibles
- [x] T009 [US2] Ejecutar las pruebas de T008 y comprobar que fallan por la razón esperada
- [x] T010 [P] [US2] Crear `.claude/skills/sincronizar-tickets/SKILL.md` según `contracts/flujo-tickets.md` (detección de fusión por rama que empieza por el número del ticket o `Closes #N`, transiciones permitidas, idempotencia, informe de cada cambio, un ticket que no está en el Project solo se informa; invocar la skill es la autorización expresa de FR-010 y cada cambio se lista antes de aplicarse)
- [x] T011 [P] [US2] Ampliar `.claude/commands/abrir-pr.md`: ampliar `allowed-tools` con las herramientas del MCP necesarias y **sustituir `gh issue comment` por `mcp__github__add_issue_comment`** (FR-008: toda escritura del backlog pasa por el MCP; `gh pr create` se mantiene porque no escribe el backlog), reescribir el paso 5 con el comentario de avance de tres partes construido desde `spec.md`, `tasks.md`, `verification.md` y los veredictos, y el paso a `In review` por el MCP con parada explícita si no está disponible; mantener el resto de pasos y las dos revisiones
- [x] T012 [US2] Ejecutar las pruebas de T008 y comprobar que pasan

## Phase 5: User Story 3 - Plugin instalable desde un catálogo (Priority: P2)

**Goal**: otro equipo instala `pasarela-revision` desde `.claude-plugin/marketplace.json` y obtiene el subagente, la skill y el hook funcionando.

**Independent Test**: en un repositorio temporal vacío, registrar el catálogo, instalar, comprobar las tres piezas y el bloqueo del hook, y desinstalar sin residuos.

- [x] T013 [P] [US3] Escribir `plugins/pasarela-revision/tests/test_plugin_real_data_guard.py` (deben fallar antes de T016), ejecutando el script real como subproceso con JSON por stdin y valores sensibles generados en tiempo de ejecución con un generador **propio y autocontenido** en `plugins/pasarela-revision/tests/` (sin importar `helpers` de `.claude/hooks/tests/`, para que el plugin sea portable y no choque con otros `conftest.py`): tarjeta válida por Luhn → código 2 y mensaje con el valor enmascarado; NIT y documento → código 2; identificadores ficticios `CO-XX-000N` y `FICT-000N` → código 0; `Write`, `Edit`, `Bash` y `PowerShell` revisan `content`, `new_string` y `command`; entrada vacía o con forma inesperada → falla cerrado con código 2; **prueba de paridad**: el hook del plugin y `.claude/hooks/real_data_guard.py` deciden igual sobre las mismas 30 entradas (generadas) y enmascaran igual
- [x] T014 [P] [US3] Escribir `plugins/pasarela-revision/tests/test_plugin_layout.py` (deben fallar antes de T015 a T019): `plugin.json` es JSON válido con `name` `pasarela-revision` y `version` `0.1.0`; existe `agents/compliance-reviewer.md` con `tools: Read, Grep, Glob`; existe la skill con `context: fork`, `allowed-tools` y `argument-hint`; `hooks/hooks.json` registra `PreToolUse` con el comando `${CLAUDE_PLUGIN_ROOT}/hooks/real_data_guard.py` y ese archivo existe; ningún archivo del plugin referencia `.claude/hooks/` ni `scripts/` ni `specs/010`; ningún archivo contiene valores con forma de credencial (patrones armados por partes); el hook no importa nada del repositorio (solo biblioteca estándar); el catálogo `.claude-plugin/marketplace.json` lista el plugin con `source` relativa existente
- [x] T015 [US3] Ejecutar `python -m pytest -q plugins/pasarela-revision/tests` y comprobar que falla por la razón esperada (los archivos no existen)
- [x] T016 [US3] Crear `plugins/pasarela-revision/hooks/real_data_guard.py` autocontenido (solo biblioteca estándar): leer el payload, detectar tarjeta con Luhn (13 a 19 dígitos), NIT y documento con los mismos criterios que `.claude/hooks/real_data_guard.py`, enmascarar dejando los dos últimos dígitos, bloquear con código 2 y el mensaje "Contenido con forma de <tarjeta|NIT|documento> reales: <fragmento enmascarado>", y fallar cerrado ante un error propio
- [x] T017 [P] [US3] Crear `plugins/pasarela-revision/hooks/hooks.json` (`PreToolUse`, matcher `Edit|Write|Bash|PowerShell`, `python` con `args` a `${CLAUDE_PLUGIN_ROOT}/hooks/real_data_guard.py`, timeout 30) y `plugins/pasarela-revision/.claude-plugin/plugin.json`
- [x] T018 [P] [US3] Crear `plugins/pasarela-revision/agents/compliance-reviewer.md` (genérico: sin rutas ni nombres de tickets de este repositorio; revisa las reglas 1 a 5 contra lo que se le indique, usa la disposición de Spec Kit si existe y lo dice si no; `tools: Read, Grep, Glob`) y `plugins/pasarela-revision/skills/revisar-cumplimiento/SKILL.md` (`context: fork`, `allowed-tools: Read Grep Glob`, `argument-hint: <ticket>`)
- [x] T019 [P] [US3] Crear `.claude-plugin/marketplace.json` según `contracts/plugin.md` y `plugins/pasarela-revision/README.md` (qué incluye, instalación y desinstalación, uso de la skill, límites conocidos y el modelo de amenaza), con los textos de ejemplo sin nombres literales de archivos de entorno ni de secretos
- [x] T020 [US3] Ejecutar `python -m pytest -q plugins/pasarela-revision/tests` y comprobar que pasan; ejecutar `claude plugin validate plugins/pasarela-revision` y `claude plugin validate .`, corregir errores y anotar los avisos en `specs/010-automatizacion-project-plugin/verification.md`

**Nota de implementación (T013/T014)**: la prueba de paridad del hook y las pruebas del catálogo dependen de este repositorio, así que viven en `scripts/tests/test_plugin_repo.py`; las pruebas de `plugins/pasarela-revision/tests/` son autocontenidas y portables. El archivo del hook se llama `test_plugin_real_data_guard.py` para no chocar con la prueba homónima de `.claude/hooks/tests/`.

## Phase 6: User Story 4 - Verificador, inventario y documentación (Priority: P3)

**Goal**: la verificación automática reconoce plugin, catálogo y automatización, y cada pieza está inventariada y justificada.

**Independent Test**: `python scripts/verify_ecosystem.py` sale con 0; quitar una pieza hace fallar nombrándola.

- [ ] T022 [US4] Ampliar `scripts/tests/test_verify_ecosystem.py` con pruebas sobre árboles sintéticos en un directorio temporal (deben fallar antes de T023): árbol completo con plugin, catálogo y automatización → código 0; quitar el manifiesto, el subagente, la skill, el hook, el archivo del hook, el catálogo, una de las dos skills del flujo o las herramientas MCP de sus `allowed-tools` → falla con un mensaje que nombra la pieza (SC-006); un plugin cuyo hook referencia una ruta fuera del plugin → falla; pieza nueva en disco sin fila en `docs/ECOSISTEMA.md` → falla (SC-007); `--json` incluye las tres comprobaciones nuevas
- [ ] T023 [US4] Ampliar `scripts/verify_ecosystem.py` con las comprobaciones `plugin`, `catálogo` y `automatización del flujo` según `contracts/plugin.md` (solo biblioteca estándar) y hacerlas parte de `ALL_CHECKS`; ajustar `_expected_pieces` para que el inventario exija una fila por cada pieza nueva (plugin, catálogo, skills del flujo)
- [ ] T024 [US4] Ejecutar las pruebas de T022 y comprobar que pasan
- [ ] T025 [US4] Actualizar `docs/ECOSISTEMA.md`: una fila por pieza nueva (`siguiente-ticket`, `sincronizar-tickets`, `/abrir-pr` ampliado, plugin, subagente, skill y hook del plugin, catálogo) con `Pieza`, `Tipo`, `Necesidad` (N10 y N11), `Ubicación`, `Por qué ahí` y `Alternativa descartada` tomadas de las decisiones D1 a D12 de `research.md`; y añadir a **Límites conocidos** los de la sección final de `research.md` (Done al sincronizar, hereda los límites del hook de datos, supone Spec Kit, depende del Project nº 4)

## Phase 7: Cierre y verificación

- [ ] T026 Ejecutar `python -m pytest -q`, `python -m ruff check .`, `python -m ruff format --check .` y `python scripts/verify_ecosystem.py`; todo en verde. Hacer una verificación por mutación del hook del plugin: romper a propósito (permitir siempre, no enmascarar, ignorar `PowerShell`, aceptar entradas vacías) y comprobar que alguna prueba falla
- [ ] T027 Verificar `/sincronizar-tickets` contra el Project real: ejecutarla sobre el estado actual, comprobar que cada cambio informado es correcto (p. ej. #9 y #1 en `Done`, #10 en `In Progress`) y ejecutarla de nuevo comprobando que no modifica nada (SC-003); anotar la evidencia en `verification.md`
- [ ] T028 Verificar `/siguiente-ticket` con confirmación (hay un ticket en progreso) y con el servidor no disponible si es posible simularlo (por ejemplo, sin el toolset) sin dejar el Project modificado; anotar el resultado en `verification.md`; si no se puede simular el servidor caído, declararlo: solo se verifica el texto de la skill (SC-005 parcial)
- [ ] T029 Instalar el plugin en un repositorio temporal vacío (`git init` en una carpeta temporal fuera del proyecto): `claude plugin marketplace add`, `claude plugin install pasarela-revision@pasarela-austral --scope project`, `claude plugin list`, provocar el bloqueo del hook con un valor con forma de tarjeta generado en el momento, y después `claude plugin uninstall` y `claude plugin marketplace remove`, comprobando que no quedan residuos; cronometrar la instalación completa (SC-004: menos de 5 minutos) y anotar cada resultado en `verification.md`
- [ ] T021 [US3] Resolver el riesgo D11 de `research.md`: comprobar con la instalación de T029 si `agent:` en la skill del plugin resuelve el subagente; si no, ajustar la skill para lanzar el subagente por su nombre y anotar la decisión en `research.md` y `verification.md`
- [ ] T030 Actualizar `docs/TRAZABILIDAD.md`: filas N10, N11, E8, P3 a P5 y P8 con su estado real y evidencia (`Hecho` solo lo que existe en `main`; `En rama` lo de esta rama), la nota del ticket #10, el orden de los tickets que quedan y el resumen recalculado
- [ ] T031 La **única** revisión de código de este ticket (es el paso `code-reviewer` de `/abrir-pr`, no una adicional; la revisión de cumplimiento con `compliance-reviewer` sigue siendo obligatoria por la constitución), en sesión aparte, con el modelo de amenaza escrito (barreras contra descuidos, no contra ofuscación), pidiendo entradas reproducibles y dejando como bloqueantes solo el acceso accidental a datos o secretos y las mentiras graves de documentación; corregir los bloqueantes y declarar el resto en `docs/ECOSISTEMA.md` y en el PR; no repetir la revisión
- [ ] T032 Ejecutar `/abrir-pr 10`: comentario de avance de tres partes y ticket a `In review` por el MCP (la primera vez que el flujo se usa a sí mismo)

- [ ] T033 Tras la fusión del pull request (la hace la persona): ejecutar `/sincronizar-tickets` y comprobar que el #10 pasa a `Done`; dejar la evidencia en un comentario del issue y en la fila correspondiente de `docs/TRAZABILIDAD.md` del siguiente ticket (SC-001: ciclo completo)

## Dependencies & Execution Order

- Setup (T001-T002) → Foundational (T003) → historias → Cierre.
- US1 y US2 son P1; US2 puede empezar tras T003 y comparte archivo de pruebas con US1 (T004 y T008 no en paralelo); `siguiente-ticket` (T006) invoca la sincronización de US2, pero cada skill se prueba por separado.
- US3 es P2 e independiente de US1 y US2 tras T001-T002: T013 y T014 en paralelo; T016 antes de T017 a T019 solo en lo que el hook referencia.
- US4 depende de que existan las piezas de US1 a US3 (T023 y T025 después de T006, T010, T011 y T016 a T019).
- T029 necesita US3 completa; T021 está en la fase de cierre porque depende de T029; T033 ocurre tras la fusión; T027 y T028 necesitan US1 y US2; T030 va al final de las piezas y antes de T031.
- T031 y T032 son la última fase: el PR no se abre sin la revisión y sin los resultados de T026 a T029.

## Parallel Examples

- Fase 5: T013 y T014 (archivos distintos) en paralelo; T017, T018 y T019 en paralelo tras T016.
- Fase 4: T010 y T011 en paralelo (skills y comando distintos).
- Cierre: T027 y T028 (flujo contra el Project) en paralelo con T029 (plugin en repositorio temporal).

## Implementation Strategy

- **MVP**: Setup + Foundational + US1 + US2 (T001-T012): el flujo de tickets queda automatizado y se usa a sí mismo para cerrar este ticket.
- Siguiente: US3 (plugin y catálogo: un mínimo del enunciado), US4 (verificador, inventario) y el cierre.
- Cada historia se valida con su "Independent Test" antes de pasar a la siguiente.
- Riesgos declarados: la resolución de `agent:` en una skill de plugin (T021), la sintaxis de `${CLAUDE_PLUGIN_ROOT}` en hooks (T020 y T029) y que la instalación de prueba modifica temporalmente la configuración de usuario de Claude Code (se deshace al terminar, T029).
