# Trazabilidad contra el enunciado de la prueba

Documento de control: cada requisito del enunciado ("Prueba técnica Claude Code + Agent SDK — Escenario Pagos: Due diligence de comercios", 11 páginas) con su estado real y la evidencia que se puede comprobar. Lo exige la constitución (v1.1.0): se actualiza **al cerrar cada ticket**. Quien lo revise debe poder contrastar cada fila con el PDF y con el repositorio.

**Fecha límite de los tres entregables: domingo 18-oct-2026.**

## Cómo leerlo

| Estado | Significado |
|---|---|
| **Hecho** | Existe en `main`, con evidencia comprobable |
| **En rama** | Hecho y probado, pero en una rama sin fusionar (se indica cuál) |
| **Parcial** | Una parte existe; se dice qué falta |
| **Falta** | No existe todavía; se indica el ticket que lo cubre |

Ramas: `main` (incluye el ticket #1 fusionado en el PR #12) · `009-ecosistema-claude-code` (esta; ecosistema de Claude Code) · `002-coordinador-subagentes` (ticket #2, **solo en el equipo local**, aún no subida a GitHub).

La columna "Sin verificar" marca lo que no se puede demostrar sin ejecutar el modelo real.

---

## 1. Reglas generales

| ID | Requisito del enunciado | Estado | Evidencia / pendiente |
|---|---|---|---|
| G1 | Los tres entregables cargados a más tardar el domingo 18-oct-2026 | Falta | En curso; ver sección 7 |
| G2 | MVP sólido; si falta tiempo, priorizar los comportamientos obligatorios | Parcial | Criterio recogido en la constitución (Restricciones adicionales) |
| G3 | Usar Claude Code durante toda la construcción | Hecho | Todo el historial se construyó con Claude Code |
| G4 | Todos los datos ficticios (ni en logs ni en configuración) | Hecho | `mcp_server/data/*.json` con `FICT-000N`; prueba `mcp_server/tests/test_datos_ficticios.py`; escaneo manual de secretos y patrones antes de cada commit (no hay un hook de git que lo automatice). El hook que lo impone en la edición está en la rama `009` (N5) |
| G5 | Repositorio propio en GitHub con acceso para los evaluadores | Parcial | Repo privado `Bryanzdruls/pasarela-austral-due-diligence`. **Falta añadir a los evaluadores como colaboradores** (no se conocen sus usuarios) |
| G5b | GitHub Project donde vive el backlog | Hecho | Project nº 4 "Pasarela Austral - Due diligence" |
| G6 | Lenguaje Python o TypeScript | Hecho | Python 3.12 |
| G7 | Trabajo individual | Hecho | Un único autor |

## 2. Reglas de negocio de la pasarela

| ID | Regla | Estado | Evidencia / pendiente |
|---|---|---|---|
| R1 | Ninguna consulta a listas sin comercio identificado de forma unívoca en el registro | Hecho | Hook `PreToolUse` sobre `consultar_listas_restrictivas`: solo para un comercio identificado de forma unívoca por el registro (o su representante), con lo que devolvió la fuente; `due_diligence/rules.py` y `rule_hooks.py` (en `main`, PR #17). verificado con modelo real (`specs/003-*/verification.md`): denegada con el modelo aunque se le ordenó saltarla |
| R2 | Coincidencia en listas (comercio o representante) impide recomendar habilitación y escala | Hecho | Hook sobre `registrar_informe` (rechaza `habilitar` tras una coincidencia del comercio o de su representante) y hook `Stop` que exige escalar antes de cerrar, una sola vez; `due_diligence/rules.py` y `rule_hooks.py` (en `main`, PR #17). verificado con modelo real (`specs/003-*/verification.md`). El contenido y el criterio del escalamiento: ticket #6 |
| R3 | Alto riesgo nunca recibe habilitación automática | Hecho | Hook sobre `registrar_informe` con la lista de la pasarela (apuestas, criptoactivos, suplementos dietarios, medicamentos) desde el registro, el catálogo y la solicitud del analista, también si el catálogo dice `sin_clasificar`; `due_diligence/rules.py` y `rule_hooks.py` (en `main`, PR #17). verificado con modelo real (`specs/003-*/verification.md`) |
| R4 | Cada afirmación con su fuente; si dos fuentes se contradicen, se muestran ambas | Hecho | El `CaseBook` guarda las fuentes que respondieron y las contradicciones que el registro señala; `PreToolUse` rechaza un hallazgo cuya fuente no respondió o no trae fecha (`procedencia`) y un informe que no declare todos los valores en conflicto con su origen (`conflicto`); `due_diligence/rules.py` (en `main`, PR #19), 61 mutaciones detectadas. Con el modelo real: el informe de `CO-FH-0006` declaró ambas fechas con su origen (`specs/005-*/verification.md`); la denegación `conflicto` **no se ejerció con el modelo real** (se negó a violarla), solo con pruebas. Contradicciones entre frentes distintos: solo por prompt |
| R5 | Si una fuente no responde, el informe indica qué frente quedó sin cubrir | Hecho | La cobertura sale de lo que el servidor devolvió (`PostToolUse`/`PostToolUseFailure`): `registrar_informe` y `escalar_a_cumplimiento` se rechazan si un frente caído no consta como `sin_cubrir` en `cobertura`, y `habilitar` exige registro y listas cubiertos; `due_diligence/rules.py` y `rule_hooks.py` (en `main`, PR #18), mutaciones detectadas (la forma real de `PostToolUseFailure` no se midió) (`specs/004-*/verification.md`) |

## 3. Ciclo de vida: Spec Driven Development con Spec Kit

| ID | Requisito | Estado | Evidencia / pendiente |
|---|---|---|---|
| S1 | Instalar Spec Kit con la integración para Claude Code | Hecho | `.specify/`, `.claude/skills/speckit-*` |
| S2 | `/speckit.constitution` una vez por proyecto | Hecho (con salvedad) | `.specify/memory/constitution.md`. La v1.0.0 se escribió **a mano**, sin invocar el comando; la v1.1.0 se produjo con `/speckit-constitution` (commit `99a03e9`) |
| S2b | La constitución recoge reglas de negocio, datos ficticios y criterio hooks vs instrucciones | Hecho | Principios I, II y III |
| S3 | `/speckit.specify` por ticket con el contenido del issue; `/speckit.clarify` si hay ambigüedad | Hecho | `specs/001-*` (main) y `specs/002-*` (rama `002`). `clarify` no se usó: no quedaron ambigüedades |
| S4 | `/speckit.plan` con decisiones técnicas | Hecho | `specs/001-*/plan.md`; `specs/002-*/plan.md` (rama `002`) |
| S5 | `/speckit.tasks` (opcional `taskstoissues`) | Hecho | `tasks.md` en `specs/001-*` y `specs/002-*`; `taskstoissues` no usado (opcional) |
| S6 | `/speckit.analyze` antes de implementar | Hecho | Ejecutado en #1 y #2; correcciones aplicadas |
| S7 | `/speckit.implement` para construir y `/speckit.converge` si quedan brechas | **Parcial** | Se implementó siguiendo `tasks.md` **a mano**; los comandos `/speckit-implement` y `/speckit-converge` **no se invocaron**. Pendiente decidir cómo se hace en los tickets que quedan |
| S8 | Artefactos versionados (`.specify/memory/`, `specs/`) | Hecho / En rama | #1 en `main`; #2 en rama `002` |
| S9 | Cada ticket implementado tiene spec, plan y tareas en el repositorio | Hecho / En rama | #1 completo; #2 completo en rama `002` |

## 4. Gestión del proyecto en GitHub

| ID | Requisito | Estado | Evidencia / pendiente |
|---|---|---|---|
| P1 | Repo y Project con campo de estado (Todo, In progress, In review, Done) | Hecho | Project nº 4 con las cuatro opciones |
| P2 | Backlog propio: un issue por funcionalidad, añadidos al Project | Hecho | Issues #1 a #11, todos en el Project |
| P3 | Servidor MCP de GitHub en Claude Code con el toolset `projects` habilitado | Hecho | `.mcp.json` en rama `009` (commit `66ec80b`), con la cabecera `X-MCP-Toolsets: default,projects` y el token por variable de entorno. Comprobado en uso: se movieron tickets con `projects_write` (en `main`, PR #13) |
| P4 | Claude Code toma el siguiente ticket del Project y lo usa como insumo de `/speckit.specify` | Hecho | Skill `/siguiente-ticket` (rama `010`): elige el ticket por el orden del proyecto, lo pasa a `In Progress` por el MCP y entrega su contenido como insumo de `/speckit-specify`. Probada contra el Project real: con #2 y #10 en progreso se detiene y pide confirmación (en `main`, PR #15) |
| P5 | Al iniciar un ticket lo mueve a In progress; al abrir el PR, a In review; al fusionar, a Done | Hecho | `/siguiente-ticket` (a `In Progress`), `/abrir-pr` ampliado (a `In review` y comentario Especificado/Decidido/Pendiente por el MCP) y `/sincronizar-tickets` (a `Done` al fusionar, idempotente; ejecutada sobre el estado real sin cambios). Done se registra al sincronizar, no en el instante de la fusión; el ciclo completo del #10 se cierra tras su fusión (T033) (en `main`, PR #15) |
| P6 | Cada PR referencia y cierra su issue | Hecho | PR #12 cierra #1 |
| P7 | El issue recibe comentarios de avance (qué se especificó, decidió y quedó pendiente) | Hecho | Comentarios en #1 y #2; el cierre del #2 está pendiente |
| P8 | Automatización por comando, skill, subagente, hook o combinación | Hecho | Combinación de skills (`siguiente-ticket`, `sincronizar-tickets`) y comando (`/abrir-pr`) con `allowed-tools` limitadas al MCP de GitHub; verificadas por `scripts/tests/test_flow_skills.py` y el verificador del ecosistema (en `main`, PR #15) |
| P9 | Un evaluador puede reconstruir el avance solo mirando GitHub | En curso | Se valida al final |

## 5. Ecosistema de Claude Code (mínimos)

Los comandos que instala Spec Kit no cuentan. Cada pieza se justifica en `DECISIONES.md` (que **falta**).

| ID | Mínimo | Estado | Evidencia / pendiente |
|---|---|---|---|
| E1 | `CLAUDE.md` con jerarquía correcta (`@import` o uno por subdirectorio, justificado) | Hecho | `CLAUDE.md` raíz con `@docs/convenciones.md` y `CLAUDE.md` en `mcp_server/` y `due_diligence/` (rama `009`) (en `main`, PR #13) |
| E2 | 2 reglas en `.claude/rules/`, al menos 2 con `paths` | Hecho | `.claude/rules/`: `datos-ficticios.md`, `specs.md`, `tests.md`, las tres con `paths` (rama `009`) (en `main`, PR #13) |
| E3 | 2 subagentes con herramientas restringidas a su rol | Hecho | `code-reviewer` y `compliance-reviewer`, ambos solo con Read, Grep y Glob (rama `009`) (en `main`, PR #13) |
| E4 | 2 skills; entre todas usan `context: fork`, `allowed-tools` y `argument-hint` | Hecho | `revisar-cumplimiento` (`context: fork`) y `verificar-ecosistema` (`allowed-tools`, `argument-hint`) (rama `009`) (en `main`, PR #13) |
| E5 | 2 hooks: uno que bloquea antes de ejecutar y uno posterior a una edición | Hecho | 4 hooks en `.claude/settings.json`: 3 `PreToolUse` y 1 `PostToolUse`; pruebas de los hooks y mutaciones detectadas (`specs/009-*/verification.md`) (en `main`, PR #13) |
| E6 | 1 comando propio compartido por control de versiones | Hecho | `.claude/commands/abrir-pr.md` (en `main`) |
| E7 | 2 servidores MCP (GitHub y el propio), sin credenciales en el repo | Hecho | `.mcp.json`; sin credenciales. `pasarela-fuentes` se lanza con `python -m uv run python -m mcp_server`: handshake MCP por stdio comprobado el 2026-10-16, arranca y lista las 6 herramientas. Requiere `uv` (`python -m uv sync`). **Sin verificar** desde una sesión nueva de Claude Code (`claude mcp list` lo muestra pendiente de aprobación). El PR #14 (`python -m mcp_server` directo) se cerró sin fusionar: el `python` del sistema trae un `mcp` sin `mcp.server.mcpserver` |
| E8 | 1 plugin con al menos 1 subagente, 1 skill y 1 hook reutilizables | Hecho | `plugins/pasarela-revision/` con subagente `compliance-reviewer`, skill `revisar-cumplimiento` y hook `real_data_guard`; `claude plugin validate --strict` sin avisos (rama `010`). En una sesión real en un repositorio ajeno el hook bloqueó un valor con forma de tarjeta y la skill resolvió el subagente del plugin; además lo cubren sus pruebas, la paridad con el hook del proyecto y 5 mutaciones detectadas (en `main`, PR #15) |

Necesidades que el ecosistema debe resolver:

| ID | Necesidad | Estado | Mecanismo previsto / evidencia |
|---|---|---|---|
| N1 | Convenciones del equipo al clonar el repositorio | Hecho | `CLAUDE.md` de proyecto y `docs/convenciones.md` (en `main`, PR #13) |
| N2 | Preferencias personales no afectan a compañeros | Hecho | `.gitignore` ignora `CLAUDE.local.md` y `.claude/settings.local.json`; el `CLAUDE.md` compartido es el contraste (en `main`, PR #13) |
| N3 | Tests junto al código, en muchas carpetas, con las mismas convenciones | Hecho | Regla `.claude/rules/tests.md` con `paths` (en `main`, PR #13) |
| N4 | No se escribe código de un ticket sin su especificación en `specs/` | Hecho | Hook `spec_gate.py`; bloqueo comprobado en Claude Code real (en `main`, PR #13) |
| N5 | Ningún archivo con forma de documento, NIT o tarjeta reales | Hecho | Hook `real_data_guard.py`; bloqueo comprobado en Claude Code real (en `main`, PR #13) |
| N6 | Los archivos de secretos y variables de entorno no se leen ni modifican | Hecho | `permissions.deny` y hook `secrets_guard.py` (incluye `Bash`); bloqueos comprobados en Claude Code real (en `main`, PR #13) |
| N7 | El código queda formateado tras cada edición | Hecho | Hook `format_after_edit.py` (`ruff format`); comprobado en Claude Code real (en `main`, PR #13) |
| N8 | Revisión independiente antes de abrir un PR | Hecho | `/abrir-pr` lanza `code-reviewer` y `compliance-reviewer` en contexto aislado (en `main`, PR #13) |
| N9 | Revisión de cumplimiento de las reglas de negocio | Hecho | Subagente `compliance-reviewer` y skill `revisar-cumplimiento` (en `main`, PR #13) |
| N10 | Estado de los tickets sincronizado sin intervención manual | Hecho | Skills `siguiente-ticket` y `sincronizar-tickets` y `/abrir-pr` ampliado (rama `010`). Sin intervención manual para mover tarjetas; Done al sincronizar. El caso 'servidor o toolset no disponibles' solo está verificado en el texto de la skill (en `main`, PR #15) |
| N11 | Otro equipo puede instalar las piezas reutilizables | Hecho | Catálogo `.claude-plugin/marketplace.json` (`pasarela-austral`) y plugin `pasarela-revision`: instalado en un repositorio ajeno y desinstalado sin residuos en 5 s (rama `010`) (en `main`, PR #15) |

## 6. Sistema multi-agente y servidor MCP

Herramientas mínimas del servidor MCP:

| ID | Herramienta | Estado | Evidencia |
|---|---|---|---|
| T1 | `consultar_registro_mercantil` | Hecho | `mcp_server/tools/registro.py` y pruebas |
| T2 | `consultar_listas_restrictivas` | Hecho | `mcp_server/tools/listas.py` |
| T3 | `buscar_noticias` | Hecho | `mcp_server/tools/noticias.py` |
| T4 | `consultar_riesgo_categoria` | Hecho | `mcp_server/tools/riesgo.py` |
| T5 | `registrar_informe` | Hecho | `mcp_server/tools/informes.py` |
| T6 | `escalar_a_cumplimiento` | Hecho | `mcp_server/tools/informes.py` |

Comportamientos obligatorios:

| ID | Comportamiento | Estado | Evidencia / pendiente |
|---|---|---|---|
| B1 | Coordinador que delega en al menos tres subagentes, cada uno solo con las herramientas de su frente | Hecho | `due_diligence/agents.py`, `options.py`, `guards.py` (rama `002`). Verificado con modelo real (5 casos, `specs/002-*/verification.md`): el SDK entrega el `agent_type` y cada frente usó solo su herramienta; el coordinador solo usó `Agent` (en `main`, PR #16) |
| B2 | Contexto explícito; resultados que separan contenido y metadatos | Hecho | `due_diligence/events.py`, `prompts.py` (rama `002`). Verificado con modelo real: los `encargo` del caso 3 no contienen datos del comercio anterior y los informes separan contenido y metadatos (fuente y fecha) (en `main`, PR #16) |
| B3 | Ejecución en paralelo de los frentes independientes; los dependientes esperan | Hecho | Verificado con modelo real en el caso 1: los tres frentes independientes arrancan antes de que termine cualquiera y las listas esperan al registro. Hizo falta forzar la ejecución en primer plano (`CLAUDE_CODE_DISABLE_BACKGROUND_TASKS`, D15). En los casos 3 y 5 el riesgo no corrió en paralelo porque no había categoría declarada (en `main`, PR #16) |
| B4 | Ciclo agéntico por la razón de parada del modelo, sin contador ni búsqueda de palabras | Hecho | `due_diligence/coordinator.py`, 8 mutaciones detectadas (rama `002`); con modelo real todos los turnos cerraron por `ResultMessage` (`end_turn`) (en `main`, PR #16) |
| B5 | Reglas 1 y 2 con **hooks del SDK** | Hecho | Reglas 1 y 2 (y 3) con hooks del SDK, 15 mutaciones detectadas (`python scripts/mutate_rules.py`); `due_diligence/rules.py` y `rule_hooks.py` (en `main`, PR #17) |
| B6 | Descripciones de herramientas que eviten confusiones | Hecho | Descripciones verificadas por pruebas en `mcp_server/tests/test_server.py` |
| B7 | Errores estructurados y cobertura parcial; el coordinador decide reintentar o declarar | Hecho | Error estructurado del subagente (`FrontStatus.FALLIDO`), tope de un reintento y ninguno para lo no reintentable impuesto por hook (`check_fuente`), y declaración de la cobertura en el informe (en `main`, PR #18). El coordinador decide reintentar por su prompt; el hook solo pone el tope |
| B8 | Procedencia y conflictos en el informe, con su origen | Hecho | Ver R4: hallazgos con `fuente` y `fecha` exigidos por hook, y `conflictos` completos (en `main`, PR #19) |
| B9 | Varios comercios parecidos: el coordinador pide el identificador | Hecho | Con el modelo real el coordinador mostró los candidatos y pidió el identificador, y siguió solo con el elegido; un hook rechaza el informe o el escalamiento a nombre de un candidato sin identificar (`ambiguedad`, probado sin el modelo, no ejercido con él) (en `main`, PR #19) |
| B10 | Escalar con criterio (listas y alto riesgo; no escalar bajo riesgo sin hallazgos) | En rama | `CaseBook.escalation_grounds` (coincidencia en listas, alto riesgo, contradicción, menciones en noticias) y `PreToolUse` rechaza escalar, o recomendar escalar, un comercio sin motivo (`escalamiento`); una cobertura incompleta sola no es motivo (lectura literal del enunciado, decisión D2); `due_diligence/rules.py` (rama `006`), 85 mutaciones detectadas. Con el modelo real: C1 y C3 se escalaron, C2 se habilitó y, con una fuente caída, `CO-LB-0002` recibió `no_habilitar` y no se escaló; una orden de escalar `CO-LB-0002` fue rechazada una vez (`specs/006-*/verification.md`) |
| B11 | Handoff útil al oficial de cumplimiento | En rama | `escalar_a_cumplimiento` acepta `conflictos`; el hook exige el hallazgo, con fuente y fecha, del frente que motiva (`handoff_hallazgos`), una causa que nombra cada motivo (`handoff_causa`, por palabras clave) y las contradicciones declaradas (rama `006`). Con el modelo real los resúmenes de C1 y C3 salieron completos; el rechazo de una causa vaga no se ejerció con el modelo (rechazó escribirla) |
| B12 | Interfaz de chat que muestre mensajes, delegaciones, informe y escalamiento | **Falta** | Ticket #7. La consola interactiva de la rama `002` no cumple este requisito |

Casos de prueba que el repositorio debe incluir y pasar:

| ID | Caso | Estado | Evidencia / pendiente |
|---|---|---|---|
| C1 | Mensaje del escenario: comercio de alto riesgo que va a un oficial | Parcial | Verificado con el modelo real (`CO-TV-0001`, `specs/006-*/verification.md`, rama `006`); automatización de extremo a extremo: ticket #8 |
| C2 | Comercio de bajo riesgo sin hallazgos, con habilitación | Parcial | Verificado con el modelo real (`CO-LB-0002`, rama `006`); automatización de extremo a extremo: ticket #8 |
| C3 | Representante legal con coincidencia en listas | Parcial | Verificado con el modelo real (`CO-DA-0003`, `specs/006-*/verification.md`, rama `006`); automatización de extremo a extremo: ticket #8 |
| C4 | Dos comercios con nombres casi idénticos | Parcial | Verificado con el modelo real (`CO-CA-0004`/`0005`, `specs/005-*/verification.md`, rama `005`); automatización de extremo a extremo: ticket #8 |
| C5 | Consulta a listas sin identificación unívoca, bloqueada | Hecho | Prueba del caso del enunciado en `due_diligence/tests/test_rule_hooks.py` (listas sin identificación unívoca, denegada con la regla 1) y bloqueo real con el modelo (`specs/003-*/verification-forzado.txt`). La automatización de extremo a extremo con el modelo: ticket #8 |
| C6 | Falla del servicio de noticias con cobertura incompleta declarada | Parcial | Verificado con el modelo real con `PASARELA_FAULTS=noticias` (`specs/004-*/verification.md`, rama `004`); la automatización de extremo a extremo con el modelo: ticket #8 |
| C7 | Dos fuentes con fechas de constitución distintas | Parcial | Verificado con el modelo real (`CO-FH-0006`, `specs/005-*/verification.md`, rama `005`); automatización de extremo a extremo: ticket #8 |

## 7. Entregables y sustentación

| ID | Requisito | Estado | Evidencia / pendiente |
|---|---|---|---|
| D1 | Repositorio y Project con el historial real, sin reescribirlo | En curso | Historial intacto hasta hoy |
| D2 | README: correr sistema y tests en menos de 5 minutos, enlace al Project y al video de funcionamiento | **Falta** | Ticket #11 |
| D3 | `DECISIONES.md` de máximo dos páginas con mecanismo y motivo por necesidad | **Falta** | Ticket #11 |
| D4 | Artefactos de Spec Kit versionados | Hecho / En rama | Ver S8 |
| D5 | Zip con `.git`, sin dependencias instaladas, máximo 50 MB, **sin `.env` ni credenciales** | **Falta** | Se arma al final (#11); el escaneo de secretos se hace a mano antes de cada commit; `scripts/tests/test_no_credentials.py` lo repite sobre la configuración |
| D6 | Video de funcionamiento de máximo 5 minutos, con los casos obligatorios en la interfaz de chat, público y enlazado en el README | **Falta** | Tickets #7, #8 y #11; requiere `ANTHROPIC_API_KEY` |
| D7 | Video de defensa de máximo 15 minutos: ecosistema, especificaciones y sistema | **Falta** | A cargo del autor; requiere que todo lo anterior exista |
| D8 | Revisión de autoría: la explicación coincide con el código | Pendiente | Depende del autor (explicar *este* código) |

## 8. Faltas graves (vigilancia permanente)

| Falta grave | Estado hoy | Cómo se controla |
|---|---|---|
| Una regla de negocio que dependa solo del prompt | **Cerrada en `main` (PR #17)** | Las reglas 1 a 3 las imponen hooks del SDK, con pruebas, 15 mutaciones detectadas y verificación con el modelo real. La regla 5 (informe parcial nunca como completo) también la impone un hook (en `main`, PR #18) y la regla 4 (procedencia y conflictos) desde la rama `005`; el escalamiento con criterio y el resumen al oficial también los impone un hook desde la rama `006` |
| Una credencial en el repositorio | Sin hallazgos | Escaneo de valores con forma de clave de Anthropic, de token de GitHub o de clave privada a mano antes de cada commit (sin hook de git que lo automatice) y, sobre la configuración, `scripts/tests/test_no_credentials.py`; `.env` ignorado; `.mcp.json` solo referencia variables |
| Un dato que parezca real | Sin hallazgos | `test_datos_ficticios.py`; hook de datos reales en `main` (`real_data_guard.py`) |

## 9. Desviaciones del proceso reconocidas

Cosas hechas de forma distinta a lo que pide el enunciado o a lo que se acordó, para que no queden ocultas:

1. **Constitución v1.0.0 escrita a mano**, sin el comando `/speckit-constitution`. Corregido con la enmienda v1.1.0 hecha con el comando.
2. **`/speckit-implement` y `/speckit-converge` no se invocaron**: la implementación siguió `tasks.md` manualmente.
3. **El ecosistema de Claude Code se dejó como el ticket #9**, tarde, en lugar de configurarlo primero. La constitución v1.1.0 lo corrige (principio VIII).
4. **En el ticket #1, las historias US3 y US4 se implementaron antes que sus pruebas**. En el #2 se respetó escribir las pruebas primero.
5. **La revisión independiente del #1 la hizo un agente genérico**, porque el `code-reviewer` no estaba cargado en esa sesión.
6. **La rama del #2 solo existía en el equipo local**; se subió a GitHub el 2026-10-16 tras fusionar el #10. Corregido.
7. **Ticket #9 (nota):** el ecosistema se construyó con el orden #9 → #10 → #2 (ecosistema, luego plugin y flujo de tickets, luego el coordinador). Las verificaciones con Claude Code real están en `specs/009-ecosistema-claude-code/verification.md`; quedan **sin verificar** `/hooks` y `/memory` (interactivos) y la conexión del servidor `pasarela-fuentes`, que falló en la sesión.
8. **Ticket #10 (nota):** el flujo de tickets y el plugin quedan en la rama `010`. El #9 y el #10 se ejecutaron en ese orden, como fija la constitución (v1.1.1); ningún ticket de funcionalidad se fusiona antes de que el #10 esté fusionado. Queda **sin verificar** el comportamiento de las skills con el servidor o el toolset no disponibles; el hook del plugin y la skill se comprobaron en una sesión real (con el inicio de sesión de claude.ai: la variable `ANTHROPIC_API_KEY` actual devuelve `Invalid API key`). Las evidencias están en `specs/010-automatizacion-project-plugin/verification.md`.
9. **Ticket #3 (nota):** los hooks de las reglas 1 a 3 quedan en la rama `003`. La verificación con modelo real mostró que el modelo respeta su prompt en el flujo normal, así que las denegaciones se ejercieron con un prompt de sistema de prueba que le ordena violar cada regla (los hooks son los de producción). Queda **sin verificar** con una `ANTHROPIC_API_KEY` válida (se usó el inicio de sesión de claude.ai) y la regla 3 por la categoría declarada se detecta con raíces de la lista, no con sinónimos.

## 10. Resumen

Requisitos trazados: **84** (reglas generales, reglas de negocio, Spec Kit, GitHub, ecosistema, sistema, casos de prueba y entregables).

| Estado | Cantidad |
|---|---|
| Hecho | 60 |
| Hecho (en main o en rama) | 3 |
| En rama | 2 |
| Parcial | 9 |
| Falta | 7 |
| Otro: En curso | 2 |
| Otro: Pendiente | 1 |

Última actualización: 2026-10-17, al preparar el PR del ticket #6 (pendiente de fusión). Se actualiza al cerrar cada ticket.
