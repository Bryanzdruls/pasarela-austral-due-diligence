---
description: "Tareas del ecosistema de Claude Code del equipo"
---

# Tasks: Ecosistema de Claude Code del equipo

**Input**: `specs/009-ecosistema-claude-code/` (plan.md, spec.md, research.md, data-model.md, contracts/hooks.md, quickstart.md)

**Prerequisites**: plan.md, spec.md; constitución v1.1.1; `.mcp.json` y `code-reviewer` ya versionados. Análisis `/speckit-analyze` aplicado.

**Orden de tickets (constitución v1.1.1)**: #9 → #10 → #2. Este ticket se implementa antes que el plugin por ser configuración del entorno; la excepción no se repite.

**Tests**: Incluidos y obligatorios (constitución VI). **Regla de proceso**: en cada historia primero se escriben las pruebas, se ejecutan y se comprueba que fallan por la razón esperada, y solo entonces se implementa. Los hooks se prueban ejecutando el script real como subproceso con JSON por stdin (código de salida y mensaje), no solo sus funciones.

**Orden deliberado**: `.claude/settings.json` se escribe *después* de que los scripts de cada hook estén probados, para que un hook defectuoso no bloquee el propio trabajo; los hooks registrados protegen desde ese momento.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencia pendiente)
- **[Story]**: US1 protecciones · US2 convenciones al clonar · US3 formateo · US4 revisiones independientes · US5 mínimos verificables y justificados

## Phase 1: Setup

- [x] T001 Añadir `.claude/hooks/tests` y `scripts/tests` a `testpaths` de pytest en `pyproject.toml` y comprobar que pytest recoge pruebas ubicadas en un directorio oculto (`.claude/`), que pytest suele omitir por defecto
- [x] T002 [P] Crear la estructura vacía: `.claude/hooks/`, `.claude/hooks/tests/`, `.claude/rules/`, `scripts/`, `scripts/tests/` (`docs/` ya existe)

## Phase 2: Foundational (bloquea todas las historias)

- [x] T003 Tests de `.claude/hooks/common.py` en `.claude/hooks/tests/test_common.py` (deben fallar antes de T005): lectura del JSON de stdin (válido, vacío, inválido); normalización de rutas (barras invertidas de Windows, mayúsculas, relativas y absolutas respecto de `cwd`); `is_production_path` **por exclusión**: es código de producción todo `.py` cuya ruta relativa "no contenga ninguno de estos directorios: `tests`, `scripts`, `.claude`, `.specify`, `.venv`, `docs`, `specs`" (un directorio de código nuevo como `chat/` queda protegido sin tocar la configuración; documentos, JSON y pruebas no); `bash_write_targets(comando)` que extrae las rutas hacia las que escribe una orden (`>`, `>>`, `tee`, `Set-Content`, `Out-File`, `sed -i`, `cp`/`mv` hacia, `python` que abre para escribir) y devuelve vacío para `cat`, `ls`, `pytest`, `git`; `active_feature` por prefijo numérico de la rama (`009-…` → la única `specs/009-*`) con respaldo en `.specify/feature.json` y `None` si no hay ticket; `block(mensaje)` sale con código 2 y escribe en stderr; el envoltorio `fail_closed` convierte cualquier excepción en código 2 con "El hook <nombre> falló y deniega por seguridad: <error>"
- [x] T004 [P] Crear `.claude/hooks/tests/helpers.py`: `run_hook(script, payload, cwd, env)` que ejecuta el script real con `sys.executable` y devuelve (código, stdout, stderr); `make_repo(tmp_path, branch, artefactos)` que crea un repositorio git temporal con rama y carpeta `specs/NNN-…` con los artefactos indicados; y generadores de datos sensibles **en tiempo de ejecución**: `make_card(longitud, agrupada)` con dígito de control Luhn válido, `make_nit()` y `make_documento(etiqueta, digitos)` (por ejemplo `cédula` + 6 a 10 dígitos), de modo que ningún valor sensible se escriba literal en ningún archivo
- [x] T005 Implementar `.claude/hooks/common.py` según T003 (solo biblioteca estándar)

**Checkpoint**: lectura de entrada, rutas, feature activa, escrituras por terminal y bloqueo seguro listos.

## Phase 3: User Story 1 — Las protecciones impiden los errores graves (P1) 🎯 MVP

**Goal**: tres bloqueos previos a la ejecución (especificación, datos reales, secretos) con motivo claro y fallo seguro, también frente a escrituras por terminal.

**Independent Test**: cada acción prohibida de la matriz se bloquea (código 2 y mensaje); cada equivalente permitido pasa (código 0).

- [x] T006 [US1] Tests de `spec_gate.py` en `.claude/hooks/tests/test_spec_gate.py` (deben fallar antes de T007): matriz rama de ticket × artefactos presentes {ninguno, solo spec, spec+plan, spec+plan+tasks} × tipo de ruta {producción, directorio de código nuevo `chat/`, prueba, documento, `specs/`, `scripts/`, datos JSON, configuración} (SC-002: 100 % bloqueado sin los tres artefactos, 100 % permitido con los tres); herramientas `Edit`, `Write` y **`Bash`** (`echo x > mcp_server/a.py`, `tee`, `Set-Content`, `Out-File`, `sed -i`, `cp`, `python -c "open(…,'w')"` hacia producción → bloquea sin artefactos; `cat`, `ls`, `pytest -q`, `git status` → permite); rama sin prefijo numérico (`main`) → bloquea con "La rama no corresponde a un ticket"; respaldo con `.specify/feature.json`; el mensaje nombra el artefacto que falta y el comando `/speckit-…` que lo crea; un error interno (carpeta ilegible) → código 2
- [x] T007 [US1] Implementar `.claude/hooks/spec_gate.py` según `contracts/hooks.md`
- [x] T008 [US1] Tests de `real_data_guard.py` en `.claude/hooks/tests/test_real_data_guard.py` (deben fallar antes de T009), con valores construidos en tiempo de ejecución: tarjeta de "13 a 19 dígitos contiguos o en grupos de cuatro separados por espacio o guion que pasen la comprobación de Luhn" (longitudes 13, 16 y 19, contiguas y agrupadas) → bloquea; las mismas longitudes **sin** Luhn válido → permite; NIT con forma `NNN.NNN.NNN-D` o `NNNNNNNNN-D` → bloquea; documento con etiqueta (`cédula`, `cedula`, `CC`, `NIT`, `documento`, `identificación`) seguida de 6 a 10 dígitos → bloquea; número de 8 a 10 dígitos sin etiqueta → permite; `FICT-0001`, `CO-TV-0001`, marcas de tiempo ISO y sumas de verificación → permiten; `Write` (campo `content`), `Edit` (campo `new_string`) y **`Bash`** (texto de `command`: `echo <valor> > archivo` → bloquea; `pytest -q` → permite); el mensaje enmascara el valor detectado (no lo repite completo); **SC-003**: recorrer todos los archivos de texto versionados del repositorio (`git ls-files`) y comprobar que ninguno se bloquea al reescribirse
- [x] T009 [US1] Implementar `.claude/hooks/real_data_guard.py` según `data-model.md` (reglas de detección) y `contracts/hooks.md`
- [x] T010 [US1] Tests de `secrets_guard.py` en `.claude/hooks/tests/test_secrets_guard.py` (deben fallar antes de T011): `Read`, `Edit` y `Write` sobre `.env`, `.env.local`, `.env.production`, `.ENV`, ruta con barras invertidas, ruta absoluta y relativa, `secrets/x.txt`, `clave.pem`, `llave.key`, `credentials.json` → bloquea; `.env.example` → permite lectura y escritura; `Bash` con `cat .env`, `type .env`, `Get-Content .env`, `head .env`, `tail .env`, `sed … .env`, `cp .env x`, `echo x > .env`, `python -c "open('.env')"` → bloquea; `Bash` con `ls`, `cat .env.example`, `git status` → permite; un error interno → código 2
- [x] T011 [US1] Implementar `.claude/hooks/secrets_guard.py` según `data-model.md` (archivos de secretos) y `contracts/hooks.md`
- [x] T012 [US1] Tests de `.claude/settings.json` en `scripts/tests/test_settings.py` (deben fallar antes de T013): JSON válido; los tres hooks `PreToolUse` registrados (`Edit|Write|Bash` → `spec_gate.py` y `real_data_guard.py`; `Read|Edit|Write|Bash` → `secrets_guard.py`); cada uno con `type: command`, `command: python`, `args` con `${CLAUDE_PROJECT_DIR}/.claude/hooks/<script>.py` y `timeout: 30`; cada script referenciado existe; `permissions.deny` contiene `.env`, `.env.local`, `.env.production`, `secrets/**`, `*.pem` y `*.key` para lectura y edición, y **no** contiene un comodín que cubra `.env.example`
- [x] T013 [US1] Crear `.claude/settings.json` con los tres hooks `PreToolUse` y `permissions.deny`, según `contracts/hooks.md`
- [x] T014 [US1] Comprobar a mano, en una terminal, los escenarios 1 a 7, 9 y 10 de `quickstart.md` ejecutando los scripts reales con JSON por stdin y anotar los códigos de salida; confirmar que el comando `python` de los hooks funciona en esta máquina (punto **[No confirmado]** de `research.md` D5) y registrar el resultado en `research.md`

**Checkpoint**: las tres protecciones existen, están probadas y registradas.

## Phase 4: User Story 2 — Convenciones al clonar (P1)

**Goal**: memoria de proyecto jerárquica, reglas por ruta y preferencias personales aisladas.

**Independent Test**: en un clon limpio las convenciones están cargadas; los archivos personales están excluidos; las reglas solo aplican a su zona.

- [x] T015 [US2] Tests de convenciones en `scripts/tests/test_conventions.py` (deben fallar antes de T016-T021): existe `CLAUDE.md` en la raíz con menos de 200 líneas e importa `@docs/convenciones.md`, cuyo destino existe; existen `mcp_server/CLAUDE.md` y `due_diligence/CLAUDE.md`; hay al menos 2 reglas en `.claude/rules/` con frontmatter `paths` con globs, y una de ellas cubre `**/tests/**/*.py` y `**/test_*.py`; `.gitignore` excluye `CLAUDE.local.md` y `.claude/settings.local.json`; ni `CLAUDE.local.md` ni `settings.local.json` están versionados; **`CLAUDE.md`, `docs/convenciones.md`, los `CLAUDE.md` de subdirectorio, las reglas y `.claude/settings.json` están versionados** (`git ls-files`), que es lo que garantiza que un clon limpio los reciba sin configurar nada (SC-001)
- [x] T016 [US2] Crear `docs/convenciones.md` (estilo de código, nombres, mensajes de commit, flujo de Spec Kit, qué va a hooks y qué a instrucciones) y `CLAUDE.md` en la raíz (propósito del proyecto, comandos para correr pruebas y formateo, reglas de oro, referencia a la constitución, orden de tickets #9 → #10 → #2) con `@docs/convenciones.md`, menos de 200 líneas
- [x] T017 [P] [US2] Crear `mcp_server/CLAUDE.md`: convenciones del servidor de fuentes (sobre `{ok, content, metadata}`, constante `SOURCE` por herramienta, descripciones como contrato, datos solo ficticios, el servidor no decide reglas de negocio)
- [x] T018 [P] [US2] Crear `due_diligence/CLAUDE.md`: convenciones del coordinador (una herramienta por frente, hook de aislamiento, sin `max_turns`, turno cerrado por `RunFinished`, resultados de frente validados). El directorio `due_diligence/` existe solo en la rama del ticket #2; el archivo se crea ahora en esta rama como convención futura, y si `due_diligence/` no existe en `main` el `CLAUDE.md` se ubica igualmente allí
- [x] T019 [P] [US2] Crear `.claude/rules/tests.md` con `paths: ["**/tests/**/*.py", "**/test_*.py"]`: pruebas junto al código, nombres, primero la prueba y verla fallar, sin llamar al modelo real, valores sensibles generados en tiempo de ejecución
- [x] T020 [P] [US2] Crear `.claude/rules/datos-ficticios.md` con `paths: ["mcp_server/data/**"]`: formatos `CO-XX-000N` y `FICT-000N`, fuentes terminadas en `_ficticio` o `_ficticia`, nada con apariencia de real
- [x] T021 [P] [US2] Crear `.claude/rules/specs.md` con `paths: ["specs/**"]`: estructura de artefactos de Spec Kit, idioma, referencia al issue, sin código

## Phase 5: User Story 3 — Formateo tras cada edición (P1)

**Goal**: el código queda formateado después de cada edición sin que nadie lo pida.

**Independent Test**: editar un `.py` mal formateado lo deja formateado; un archivo que no es código no se toca.

- [ ] T022 [US3] Tests de `format_after_edit.py` en `.claude/hooks/tests/test_format_after_edit.py` (deben fallar antes de T023): `.py` mal formateado → queda formateado (SC-005) y sale con 0; archivo `.md`, `.json` o `.txt` → no se modifica; sin formateador disponible (PATH vacío) → sale con 0 y avisa por stderr; el formateador falla → sale con 0 y avisa; ruta relativa y con barras invertidas; archivo inexistente → sale con 0
- [ ] T023 [US3] Implementar `.claude/hooks/format_after_edit.py`: solo `.py`; `ruff format <archivo>` y, si no hay `ruff`, `python -m uv run ruff format <archivo>`; nunca bloquea
- [ ] T024 [US3] Añadir a `scripts/tests/test_settings.py` la comprobación del hook `PostToolUse` (`Edit|Write` → `format_after_edit.py`, mismas propiedades que los demás) y registrarlo en `.claude/settings.json`

## Phase 6: User Story 4 — Revisiones independientes (P2)

**Goal**: dos revisores de solo lectura, una skill que lanza la revisión de cumplimiento en contexto aislado y un comando de PR que lanza ambas revisiones.

**Independent Test**: los dos agentes existen con herramientas de solo lectura; la skill declara contexto aislado, herramientas permitidas y pista de argumento; `/abrir-pr` lanza las dos revisiones.

- [ ] T025 [US4] Tests en `scripts/tests/test_agents_skills.py` (deben fallar antes de T026-T028): `code-reviewer` y `compliance-reviewer` tienen frontmatter con `name`, `description` y `tools` limitado a `Read, Grep, Glob`; ninguno tiene `Write`, `Edit` ni `Bash`; `revisar-cumplimiento` tiene `context: fork`, `allowed-tools` y `argument-hint`; el cuerpo del agente de cumplimiento nombra las reglas 1 a 5 y la calificación de falta grave para una regla 1-3 que dependa solo de un prompt; **`.claude/commands/abrir-pr.md` invoca tanto `code-reviewer` como `compliance-reviewer`, impide abrir el PR ante un incumplimiento grave y deja ambos veredictos en la descripción** (FR-017)
- [ ] T026 [US4] Crear `.claude/agents/compliance-reviewer.md` (`tools: Read, Grep, Glob`): para cada regla de negocio busca implementación, especificación y pruebas, y reporta cumplida / parcial / ausente con evidencia; marca falta grave cualquier regla 1-3 que dependa solo de un prompt; termina con un veredicto
- [ ] T027 [US4] Crear `.claude/skills/revisar-cumplimiento/SKILL.md` con `context: fork`, `agent: compliance-reviewer`, `allowed-tools: Read Grep Glob` y `argument-hint: <ticket>`; si `agent` no acepta un subagente propio (**[No confirmado]**), usar `general-purpose` con el mismo prompt y dejarlo anotado en `research.md`
- [ ] T028 [US4] Actualizar `.claude/commands/abrir-pr.md`: tras las pruebas y el formateo, lanzar `code-reviewer` y `compliance-reviewer`; si alguna reporta un incumplimiento grave o un hallazgo bloqueante, no abrir el PR y corregir; incluir ambos veredictos en la descripción del PR (hallazgo E1 del análisis; `research.md` D14)

## Phase 7: User Story 5 — Mínimos verificables y justificados (P2)

**Goal**: comprobación automática de los mínimos del enunciado, inventario con la justificación de cada pieza y ausencia de credenciales en la configuración.

**Independent Test**: la verificación pasa en el repositorio y falla, indicando la pieza, al quitar cualquiera de las requeridas.

- [ ] T029 [US5] Tests de `scripts/verify_ecosystem.py` en `scripts/tests/test_verify_ecosystem.py` (deben fallar antes de T030), sobre árboles sintéticos en un directorio temporal: un árbol completo pasa (código 0); para cada mínimo, quitar la pieza hace fallar la verificación con un mensaje que nombra el mínimo (SC-006): `CLAUDE.md` raíz; ni importación ni `CLAUDE.md` de subdirectorio; menos de 2 reglas con `paths`; menos de 2 subagentes con `tools` restringidas a lectura; menos de 2 skills fuera de las de Spec Kit; falta alguna de `context: fork`, `allowed-tools` o `argument-hint` entre las skills; menos de 2 hooks o falta uno `PreToolUse` o uno `PostToolUse`; sin comando propio; `.mcp.json` sin GitHub, sin `projects` en `X-MCP-Toolsets` o sin el servidor propio; credencial literal en `.mcp.json`; pieza del disco sin fila en `docs/ECOSISTEMA.md` o fila cuya ruta no existe (SC-007); las skills y comandos de Spec Kit no cuentan; `--json` produce un objeto válido
- [ ] T030 [US5] Implementar `scripts/verify_ecosystem.py` según `contracts/hooks.md` (solo biblioteca estándar)
- [ ] T031 [US5] Crear `docs/ECOSISTEMA.md`: inventario con una fila por pieza (`Pieza`, `Tipo`, `Necesidad`, `Ubicación`, `Por qué ahí`, `Alternativa descartada`), tomando el contenido de las decisiones D1 a D14 de `research.md`; incluir `CLAUDE.md` ×3, `docs/convenciones.md`, las 3 reglas, los 2 agentes, las 2 skills, `/abrir-pr`, `settings.json`, los 4 hooks, `permissions.deny`, `.mcp.json` y `scripts/verify_ecosystem.py`; y una sección **Límites conocidos** con lo de `research.md` D15
- [ ] T032 [US5] Crear `.claude/skills/verificar-ecosistema/SKILL.md` con `allowed-tools: Bash(python scripts/verify_ecosystem.py*)` y `argument-hint: [--json]`, que ejecuta la verificación y resume el resultado
- [ ] T033 [US5] Ejecutar `python scripts/verify_ecosystem.py` sobre el repositorio real y corregir cualquier brecha hasta que salga con código 0
- [ ] T034 [US5] Test en `scripts/tests/test_no_credentials.py` (debe fallar si se introduce una credencial de muestra construida en tiempo de ejecución en un archivo temporal de configuración): recorre `.claude/`, `.mcp.json`, `CLAUDE.md`, `docs/` y los `CLAUDE.md` de subdirectorio con el escaneo estricto (valores con forma de clave de Anthropic, de token de GitHub o de clave privada) y comprueba 0 coincidencias en el repositorio real (SC-008, FR-016)

## Phase 8: Cierre y verificación

- [ ] T035 Ejecutar `python -m uv run pytest -q`, `python -m uv run ruff check .` y `python -m uv run ruff format --check .`; todo en verde. Hacer una verificación por mutación: romper a propósito cada hook (permitir siempre, no enmascarar, ignorar `.env.local`, formatear también `.md`, tratar `chat/` como no producción) y comprobar que alguna prueba falla
- [ ] T036 Verificación con Claude Code real: reiniciar la sesión en este repositorio, comprobar con `/hooks` que aparecen los cuatro hooks y con `/memory` que se cargan `CLAUDE.md` y las reglas; provocar a propósito un bloqueo de cada tipo (incluido uno por `Bash`) y anotar el resultado de cada caso en `specs/009-ecosistema-claude-code/verification.md`; si algún hook no se comporta como en las pruebas, corregirlo y repetir
- [ ] T037 Actualizar `docs/TRAZABILIDAD.md`: filas E1-E7 y N1-N9 con su estado y evidencia reales, la nota del ticket #9, el orden #9 → #10 → #2 y el resumen recalculado
- [ ] T038 Ejecutar `/abrir-pr 9`: revisión independiente y de cumplimiento, corregir hallazgos, abrir el PR que cierra #9, comentar el avance en el issue y mover el ticket a In review por el MCP de GitHub

## Dependencies & Execution Order

- Setup (T001-T002) → Foundational (T003-T005) → historias → Cierre.
- US1, US2 y US3 son P1 e independientes entre sí tras la fase 2; US3 reutiliza `common.py` y el `settings.json` creado en US1 (T024 depende de T013).
- US4 y US5 son P2; **T032 depende de T030**; **T031 depende de que existan todas las piezas** (US1 a US4); T033 depende de T031 y T032; T034 puede escribirse en cualquier momento tras US2.
- `settings.json` lo tocan T013 y T024: no en paralelo. `docs/ECOSISTEMA.md` se escribe al final de las piezas para no desactualizarse.
- T036 exige reiniciar la sesión (los hooks de proyecto se leen al arrancar): es la única tarea que depende del entorno real de Claude Code.
- Después de este ticket: el #10 (plugin y automatización del flujo de tickets) y solo entonces el #2.

## Parallel Examples

- Fase 2: T004 en paralelo con T003.
- Fase 4: T017 a T021 (archivos distintos) tras T016.
- US1: los tests T006, T008 y T010 son independientes entre sí y pueden escribirse juntos.

## Implementation Strategy

- **MVP**: Setup + Foundational + US1 (T001-T014): las tres protecciones críticas (especificación previa, datos reales, secretos) quedan activas.
- Siguiente: US2 (convenciones), US3 (formateo), US4 (revisores y `/abrir-pr`) y US5 (verificación, inventario y credenciales).
- Cada historia se valida con su "Independent Test" antes de pasar a la siguiente.
- Riesgos declarados: la sintaxis de `agent` en una skill con un subagente propio y el comando `python` en Windows se comprueban en T014, T027 y T036.
