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
| R1 | Ninguna consulta a listas sin comercio identificado de forma unívoca en el registro | **Falta** | Hook del SDK: ticket #3. En la rama `002` solo hay orientación en el prompt, que **no cuenta** |
| R2 | Coincidencia en listas (comercio o representante) impide recomendar habilitación y escala | **Falta** | Hook del SDK: ticket #3; escalamiento: #6 |
| R3 | Alto riesgo nunca recibe habilitación automática | **Falta** | Hook del SDK: ticket #3 |
| R4 | Cada afirmación con su fuente; si dos fuentes se contradicen, se muestran ambas | Parcial | Servidor: cada respuesta lleva fuente y fecha, y las fechas contradictorias de `CO-FH-0006` se devuelven juntas con su origen (#1, Hecho). Informe del coordinador con procedencia: ticket #5 |
| R5 | Si una fuente no responde, el informe indica qué frente quedó sin cubrir | Parcial | Servidor: error estructurado e inyección de fallas `PASARELA_FAULTS` (#1, Hecho). Cobertura declarada en el informe: ticket #4 |

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
| P3 | Servidor MCP de GitHub en Claude Code con el toolset `projects` habilitado | En rama | `.mcp.json` en rama `009` (commit `66ec80b`), con la cabecera `X-MCP-Toolsets: default,projects` y el token por variable de entorno. Comprobado en uso: se movieron tickets con `projects_write` |
| P4 | Claude Code toma el siguiente ticket del Project y lo usa como insumo de `/speckit.specify` | **Falta** | Hoy lo hago a mano; automatización en el ticket #10 |
| P5 | Al iniciar un ticket lo mueve a In progress; al abrir el PR, a In review; al fusionar, a Done | Parcial | Se movieron #1 (In review, Done) y #2 (In progress) con el MCP, a petición; `/abrir-pr` describe el paso a In review. Sin automatismo completo (#10) |
| P6 | Cada PR referencia y cierra su issue | Hecho | PR #12 cierra #1 |
| P7 | El issue recibe comentarios de avance (qué se especificó, decidió y quedó pendiente) | Hecho | Comentarios en #1 y #2; el cierre del #2 está pendiente |
| P8 | Automatización por comando, skill, subagente, hook o combinación | Parcial | `/abrir-pr` (en `main`); falta el flujo de siguiente ticket y los hooks (#10) |
| P9 | Un evaluador puede reconstruir el avance solo mirando GitHub | En curso | Se valida al final |

## 5. Ecosistema de Claude Code (mínimos)

Los comandos que instala Spec Kit no cuentan. Cada pieza se justifica en `DECISIONES.md` (que **falta**).

| ID | Mínimo | Estado | Evidencia / pendiente |
|---|---|---|---|
| E1 | `CLAUDE.md` con jerarquía correcta (`@import` o uno por subdirectorio, justificado) | En rama | `CLAUDE.md` raíz con `@docs/convenciones.md` y `CLAUDE.md` en `mcp_server/` y `due_diligence/` (rama `009`) |
| E2 | 2 reglas en `.claude/rules/`, al menos 2 con `paths` | En rama | `.claude/rules/`: `datos-ficticios.md`, `specs.md`, `tests.md`, las tres con `paths` (rama `009`) |
| E3 | 2 subagentes con herramientas restringidas a su rol | En rama | `code-reviewer` y `compliance-reviewer`, ambos solo con Read, Grep y Glob (rama `009`) |
| E4 | 2 skills; entre todas usan `context: fork`, `allowed-tools` y `argument-hint` | En rama | `revisar-cumplimiento` (`context: fork`) y `verificar-ecosistema` (`allowed-tools`, `argument-hint`) (rama `009`) |
| E5 | 2 hooks: uno que bloquea antes de ejecutar y uno posterior a una edición | En rama | 4 hooks en `.claude/settings.json`: 3 `PreToolUse` y 1 `PostToolUse`; pruebas de los hooks y mutaciones detectadas (`specs/009-*/verification.md`) |
| E6 | 1 comando propio compartido por control de versiones | Hecho | `.claude/commands/abrir-pr.md` (en `main`) |
| E7 | 2 servidores MCP (GitHub y el propio), sin credenciales en el repo | En rama | `.mcp.json` (rama `009`); sin credenciales. **Sin verificar** que `pasarela-fuentes` arranque: se lanza con `python -m uv run` y `uv` no está instalado en el equipo del autor |
| E8 | 1 plugin con al menos 1 subagente, 1 skill y 1 hook reutilizables | **Falta** | Ticket #10 |

Necesidades que el ecosistema debe resolver:

| ID | Necesidad | Estado | Mecanismo previsto / evidencia |
|---|---|---|---|
| N1 | Convenciones del equipo al clonar el repositorio | En rama | `CLAUDE.md` de proyecto y `docs/convenciones.md` |
| N2 | Preferencias personales no afectan a compañeros | En rama | `.gitignore` ignora `CLAUDE.local.md` y `.claude/settings.local.json`; el `CLAUDE.md` compartido es el contraste |
| N3 | Tests junto al código, en muchas carpetas, con las mismas convenciones | En rama | Regla `.claude/rules/tests.md` con `paths` |
| N4 | No se escribe código de un ticket sin su especificación en `specs/` | En rama | Hook `spec_gate.py`; bloqueo comprobado en Claude Code real |
| N5 | Ningún archivo con forma de documento, NIT o tarjeta reales | En rama | Hook `real_data_guard.py`; bloqueo comprobado en Claude Code real |
| N6 | Los archivos de secretos y variables de entorno no se leen ni modifican | En rama | `permissions.deny` y hook `secrets_guard.py` (incluye `Bash`); bloqueos comprobados en Claude Code real |
| N7 | El código queda formateado tras cada edición | En rama | Hook `format_after_edit.py` (`ruff format`); comprobado en Claude Code real |
| N8 | Revisión independiente antes de abrir un PR | En rama | `/abrir-pr` lanza `code-reviewer` y `compliance-reviewer` en contexto aislado |
| N9 | Revisión de cumplimiento de las reglas de negocio | En rama | Subagente `compliance-reviewer` y skill `revisar-cumplimiento` |
| N10 | Estado de los tickets sincronizado sin intervención manual | **Falta** | Skill o comando de flujo de tickets (#10) |
| N11 | Otro equipo puede instalar las piezas reutilizables | **Falta** | Plugin y marketplace (#10) |

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
| B1 | Coordinador que delega en al menos tres subagentes, cada uno solo con las herramientas de su frente | En rama | `due_diligence/agents.py`, `options.py`, `guards.py` (rama `002`). Sin verificar con el modelo real |
| B2 | Contexto explícito; resultados que separan contenido y metadatos | En rama | `due_diligence/events.py`, `prompts.py` (rama `002`). Sin verificar con el modelo real |
| B3 | Ejecución en paralelo de los frentes independientes; los dependientes esperan | En rama | Orden de eventos verificado con cliente falso; el paralelismo real queda sin verificar |
| B4 | Ciclo agéntico por la razón de parada del modelo, sin contador ni búsqueda de palabras | En rama | `due_diligence/coordinator.py`, 8 mutaciones detectadas (rama `002`) |
| B5 | Reglas 1 y 2 con **hooks del SDK** | **Falta** | Ticket #3 |
| B6 | Descripciones de herramientas que eviten confusiones | Hecho | Descripciones verificadas por pruebas en `mcp_server/tests/test_server.py` |
| B7 | Errores estructurados y cobertura parcial; el coordinador decide reintentar o declarar | Parcial | Servidor Hecho; coordinador: ticket #4 |
| B8 | Procedencia y conflictos en el informe, con su origen | Parcial | Servidor Hecho; informe: ticket #5 |
| B9 | Varios comercios parecidos: el coordinador pide el identificador | Parcial | Servidor devuelve todas las coincidencias; el coordinador lo pide en su prompt (rama `002`). Verificación completa: tickets #5 y #8 |
| B10 | Escalar con criterio (listas y alto riesgo; no escalar bajo riesgo sin hallazgos) | **Falta** | Ticket #6 |
| B11 | Handoff útil al oficial de cumplimiento | Parcial | La herramienta valida los campos (#1); el resumen del coordinador: ticket #6 |
| B12 | Interfaz de chat que muestre mensajes, delegaciones, informe y escalamiento | **Falta** | Ticket #7. La consola interactiva de la rama `002` no cumple este requisito |

Casos de prueba que el repositorio debe incluir y pasar:

| ID | Caso | Estado | Evidencia / pendiente |
|---|---|---|---|
| C1 | Mensaje del escenario: comercio de alto riesgo que va a un oficial | Falta | Datos listos (`CO-TV-0001`); automatización de extremo a extremo: ticket #8 |
| C2 | Comercio de bajo riesgo sin hallazgos, con habilitación | Falta | Datos listos (`CO-LB-0002`); ticket #8 |
| C3 | Representante legal con coincidencia en listas | Falta | Datos listos (`CO-DA-0003`); ticket #8 |
| C4 | Dos comercios con nombres casi idénticos | Falta | Datos listos (`CO-CA-0004`/`0005`); ticket #8 |
| C5 | Consulta a listas sin identificación unívoca, bloqueada | **Falta** | Requiere el hook del ticket #3 |
| C6 | Falla del servicio de noticias con cobertura incompleta declarada | Falta | Inyección de fallas lista; informe: tickets #4 y #8 |
| C7 | Dos fuentes con fechas de constitución distintas | Falta | Datos listos (`CO-FH-0006`); ticket #8 |

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
| Una regla de negocio que dependa solo del prompt | **ABIERTA** | Las reglas 1-3 no tienen hook todavía (ticket #3). Cerrar antes del cierre del proyecto |
| Una credencial en el repositorio | Sin hallazgos | Escaneo de valores con forma de clave de Anthropic, de token de GitHub o de clave privada a mano antes de cada commit (sin hook de git que lo automatice) y, sobre la configuración, `scripts/tests/test_no_credentials.py`; `.env` ignorado; `.mcp.json` solo referencia variables |
| Un dato que parezca real | Sin hallazgos | `test_datos_ficticios.py`; hook de datos reales en la rama `009` (`real_data_guard.py`) |

## 9. Desviaciones del proceso reconocidas

Cosas hechas de forma distinta a lo que pide el enunciado o a lo que se acordó, para que no queden ocultas:

1. **Constitución v1.0.0 escrita a mano**, sin el comando `/speckit-constitution`. Corregido con la enmienda v1.1.0 hecha con el comando.
2. **`/speckit-implement` y `/speckit-converge` no se invocaron**: la implementación siguió `tasks.md` manualmente.
3. **El ecosistema de Claude Code se dejó como el ticket #9**, tarde, en lugar de configurarlo primero. La constitución v1.1.0 lo corrige (principio VIII).
4. **En el ticket #1, las historias US3 y US4 se implementaron antes que sus pruebas**. En el #2 se respetó escribir las pruebas primero.
5. **La revisión independiente del #1 la hizo un agente genérico**, porque el `code-reviewer` no estaba cargado en esa sesión.
6. **La rama del #2 solo existe en el equipo local.**
7. **Ticket #9 (nota):** el ecosistema se construyó con el orden #9 → #10 → #2 (ecosistema, luego plugin y flujo de tickets, luego el coordinador). Las verificaciones con Claude Code real están en `specs/009-ecosistema-claude-code/verification.md`; quedan **sin verificar** `/hooks` y `/memory` (interactivos) y la conexión del servidor `pasarela-fuentes`, que falló en la sesión.

## 10. Resumen

Requisitos trazados: **84** (reglas generales, reglas de negocio, Spec Kit, GitHub, ecosistema, sistema, casos de prueba y entregables).

| Estado | Cantidad |
|---|---|
| Hecho | 24 |
| Hecho (en main o en rama) | 3 |
| En rama | 20 |
| Parcial | 11 |
| Falta | 23 |
| Otro: En curso | 2 |
| Otro: Pendiente | 1 |

Última actualización: 2026-10-16, al terminar el ticket #9 (pendiente de fusión). Se actualiza al cerrar cada ticket.
