# Guion de defensa (≤ 15 min)

Guía personal de estudio. Cada pieza lleva: qué decir, dónde está en el código y qué alternativa se descartó. Todo está tomado de este repositorio; si algo no lo recuerdas, ábrelo antes de grabar. Los tiempos suman 14:00 para dejar margen.

Regla para toda la defensa: **explica este código, no cómo debería ser un código así**. Cuando digas «hay un hook», abre el archivo y señala la línea.

## Plan de tiempos

| Min | Bloque | Qué se enseña |
|---|---|---|
| 0:00–1:00 | Apertura | Problema y mapa de la solución |
| 1:00–5:30 | Sistema multi-agente y MCP | Coordinador, subagentes, servidor, hooks del SDK |
| 5:30–9:30 | Ecosistema de Claude Code | Las 11 necesidades y sus piezas |
| 9:30–12:00 | Ciclo de vida con Spec Kit | Un ticket de punta a punta en GitHub |
| 12:00–13:30 | Lo que no está perfecto | Desviaciones declaradas |
| 13:30–14:00 | Cierre | Qué haría distinto |

## 0. Apertura (1:00)

- **Decir**: sistema que investiga a un comercio antes de habilitarlo en una pasarela de pagos ficticia. Un coordinador delega en cuatro subagentes (registro mercantil, listas restrictivas, noticias, riesgo de categoría) que consumen un servidor MCP propio con datos locales. Quien conversa es un analista interno.
- **Idea que vertebra todo**: lo grave se garantiza con código determinista (hooks), no con un prompt. Es el principio III de la constitución (`.specify/memory/constitution.md`) y vale igual para el sistema (hooks del SDK) y para el desarrollo (hooks de Claude Code).
- **Mostrar**: `README.md` (mapa de piezas) y `docs/TRAZABILIDAD.md` (cada requisito del enunciado con su evidencia).

## 1. Sistema multi-agente y MCP (4:30)

### 1.1 Servidor MCP propio (0:45)
- `mcp_server/server.py` expone seis herramientas: las cuatro de fuentes (`mcp_server/tools/registro.py`, `listas.py`, `noticias.py`, `riesgo.py`) y `registrar_informe` y `escalar_a_cumplimiento` (`mcp_server/tools/informes.py`).
- Cada respuesta usa un sobre con contenido y metadatos separados: `{ok, content, metadata:{source, fetched_at}}` (`mcp_server/envelope.py`). De ahí sale la procedencia de la regla 4.
- Las descripciones de las herramientas evitan confusiones (una mención en noticias no es una coincidencia en listas); están probadas en `mcp_server/tests/test_server.py`.
- Las fallas se inyectan con `PASARELA_FAULTS=noticias` (`mcp_server/faults.py`), que es como se prueba el caso 6.
- **Descartado**: datos reales o una API externa. Todo es ficticio (`FICT-000N`), lo vigila `mcp_server/tests/test_datos_ficticios.py`.

### 1.2 Coordinador y subagentes (1:15)
- `due_diligence/agents.py`: cuatro `AgentDefinition`, cada una con una sola herramienta MCP (`FRONT_TOOLS`).
- `due_diligence/options.py`: el coordinador solo tiene `Agent` (`tools=["Agent"]`); `setting_sources=[]` para que no herede el CLAUDE.md del desarrollo.
- **Restricción en dos capas** (D4 de `specs/002-coordinador-subagentes/research.md`): configuración más el hook `PreToolUse` de `due_diligence/guards.py`, porque la documentación no confirma que `tools` restrinja herramientas MCP concretas. **Descartado**: confiar solo en la configuración.
- **Contexto explícito** (D3): el subagente recibe solo el encargo; no hereda la conversación. Hay una prueba de que el encargo no arrastra datos del comercio anterior.
- **Paralelismo** (D6): registro, noticias y riesgo salen en un mismo turno; listas espera porque necesita lo que devuelve el registro. Es una dependencia de datos. **Descartado**: `asyncio.gather` sobre `query()` sueltos, porque el coordinador dejaría de ser un agente.
- **Hallazgo con modelo real (D15)**: la herramienta `Agent` lanzaba los frentes en segundo plano; el coordinador cerraba sin informe. Solución: `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`. Se probó antes `background=False` solo y no cambió nada. Buen ejemplo de por qué no basta con pruebas sin modelo.

### 1.3 Ciclo agéntico (0:30)
- `due_diligence/coordinator.py`: `DueDiligenceSession.ask` recorre los mensajes hasta el `ResultMessage` y lee `stop_reason`. No hay contador de iteraciones ni búsqueda de palabras. En el #2 se comprobó a mano que cortar el turno por una palabra de cierre o por un número de mensajes hace fallar las pruebas de ciclo (`specs/002-coordinador-subagentes/research.md`, D7; `docs/TRAZABILIDAD.md`, B4, habla de 8 mutaciones). **Ojo**: esas mutaciones no están en `scripts/mutate_rules.py`, que solo rompe reglas de negocio y cableado; si te piden reproducirlas, di que se hicieron a mano en ese ticket.
- Un `ClaudeSDKClient` por conversación (D11): permite preguntas de seguimiento y cambio de comercio sin reinvestigar.

### 1.4 Hooks del SDK: las reglas de negocio (2:00)
Este es el centro de la defensa.
- `due_diligence/rules.py` tiene el `CaseBook`, el estado por conversación (D8), con decisiones puras. `due_diligence/rule_hooks.py` es la capa fina que adapta la forma del SDK.
- **`PostToolUse` observa** lo que devolvió cada fuente (`make_post_tool_use`); **`PreToolUse` decide** (`make_pre_tool_use`). La decisión sale de lo que respondió el servidor, no de lo que el modelo escriba (D1). **Descartado**: leer el texto del modelo, que es justo lo que el enunciado excluye.
- **Regla 1**: listas solo si el registro devolvió `ok`, `match_count == 1`, `ambiguous == false` y `existe == true`; con `tipo: persona`, la persona debe ser el representante legal de un comercio identificado (D3). **Descartado**: bastar con haber consultado el registro alguna vez.
- **Reglas 2 y 3**: se imponen en `registrar_informe`, donde sale la decisión. Vocabulario cerrado de recomendación: `habilitar`, `no_habilitar`, `escalar_a_cumplimiento` (D5). **Descartado**: aceptar variantes o comprobar por palabras.
- **Escalamiento obligatorio**: hook `Stop` (`make_stop`, D12). La regla 2 dice «impide recomendar y **escala**»; bloquear `habilitar` solo cubría la mitad. Exige escalar una sola vez (`stop_hook_active`) para no crear un bucle.
- **Falla cerrado** (D7): ante un error, `PreToolUse` deniega; `PostToolUse` nunca convierte un error en permiso.
- **Reglas 4 y 5**: `procedencia`, `conflicto`, `ambiguedad`, cobertura (`sin_cubrir`) y tope de un reintento (`check_fuente`). Escalar con criterio (`escalation_grounds`) y handoff completo.
- **Verificación por mutación**: `python scripts/mutate_rules.py` rompe a propósito cada regla y comprueba que alguna prueba falla. Hoy son 89 de 89 detectadas: 85 de reglas (acumuladas hasta el #6) y 4 de sistema del #8, que rompen el cableado de producción y solo las detectan los casos obligatorios. Di esto con precisión: demuestra que las pruebas detectan el error, no que el código sea perfecto.

### 1.5 Los siete casos y la interfaz (0:00, solo menciónalos si sobra tiempo)
- Sin modelo: `due_diligence/tests/test_casos_obligatorios.py`. Con modelo: `python scripts/run_casos.py`. Interfaz: `due_diligence/web/` (Starlette y SSE): `observadores.py` recoge los bloqueos del hook (`on_decision`) y el informe y el escalamiento del sobre `ok: true` del servidor, y `hallazgos.py` redacta el hallazgo de cada fuente desde ese mismo sobre, no desde lo que cuenta el modelo. Si el video de funcionamiento no llega a grabarse (límite de gasto del workspace), no lo des por enseñado: dilo en la defensa.

## 2. Ecosistema de Claude Code (4:00)

Ve por `DECISIONES.md`, fila por fila, sin leerla. Para cada una: mecanismo, por qué, alternativa descartada, y abre el archivo.

| # | Necesidad | Qué abrir | Frase clave |
|---|---|---|---|
| 1 | Convenciones al clonar | `CLAUDE.md`, `docs/convenciones.md`, `mcp_server/CLAUDE.md`, `due_diligence/CLAUDE.md` | La raíz queda corta; los de subdirectorio se cargan solo en su zona. |
| 2 | Preferencias personales | `.gitignore` | `CLAUDE.local.md` y `settings.local.json` nunca se versionan. |
| 3 | Pruebas junto al código | `.claude/rules/tests.md` | Una regla con `paths`, no la misma instrucción copiada en cada carpeta. |
| 4 | No código sin spec | `.claude/hooks/spec_gate.py` | Bloquea en `PreToolUse`, también si se escribe desde la terminal. |
| 5 | Datos reales | `.claude/hooks/real_data_guard.py`, `.claude/rules/datos-ficticios.md` | Tarjeta con Luhn, NIT y documento; los valores de prueba se generan en ejecución. |
| 6 | Secretos | `.claude/settings.json` (`permissions.deny`), `.claude/hooks/secrets_guard.py` | Dos capas; el hook ve también las órdenes de `Bash`. |
| 7 | Formato tras editar | `.claude/hooks/format_after_edit.py` | `PostToolUse`, nunca bloquea. |
| 8 | Revisión independiente | `.claude/agents/code-reviewer.md`, `.claude/commands/abrir-pr.md` | Solo `Read`, `Grep`, `Glob`: no puede editar lo que revisa. |
| 9 | Revisión de cumplimiento | `.claude/agents/compliance-reviewer.md`, `.claude/skills/revisar-cumplimiento/SKILL.md` | `context: fork`; marca falta grave lo que dependa solo de un prompt. |
| 10 | Tickets sincronizados | `.claude/skills/siguiente-ticket/SKILL.md`, `sincronizar-tickets/SKILL.md`, `.mcp.json` | Un hook no puede llamar al MCP; por eso son skills. |
| 11 | Piezas reutilizables | `plugins/pasarela-revision/`, `.claude-plugin/marketplace.json` | Instalado en un repositorio ajeno y desinstalado sin residuos. |

Cuatro puntos para no tropezar:
- **Hook de Claude Code frente a hook del SDK**: los primeros protegen el desarrollo; los segundos, el producto. Son mecanismos distintos con el mismo principio. Dilo explícitamente.
- Los hooks de desarrollo son barreras contra descuidos del asistente, **no** contra una ofuscación deliberada (`docs/ECOSISTEMA.md`, límites). Si te preguntan, admítelo.
- **Mínimos del enunciado**: 2 reglas con `paths` (hay 3), 2 subagentes con herramientas restringidas, 2 skills (`context: fork`, `allowed-tools`, `argument-hint`), 2 hooks (uno bloqueante pre, uno post-edición; hay 4), un comando propio (`abrir-pr`), dos MCP y un plugin.
- Pruebas de los hooks: se ejecuta el script real con JSON por stdin; hay seis rondas de evasiones en `.claude/hooks/tests/test_bypasses*.py`.

## 3. Ciclo de vida (2:30)

Elige **un** ticket y recórrelo. Recomiendo el #11 o el #3 porque tienen verificación con modelo real.
1. Issue en el Project nº 4 (`https://github.com/users/Bryanzdruls/projects/4`), movido por `/siguiente-ticket` a In progress.
2. `specs/NNN-…/`: `spec.md` (qué y por qué), `plan.md` y `research.md` (cómo, con alternativa descartada), `tasks.md` (con `[x]`), `verification.md`.
3. `/speckit-analyze` antes de implementar (en el #11 dejó ocho correcciones aprobadas —I1, C1, C2, I2, U1, A1, T1 y T2— que están en `specs/011-readme-decisiones-videos/tasks.md`).
4. Pruebas primero y se ven fallar.
5. `/abrir-pr N`: los dos revisores, una sola ronda de repetición, comentario Especificado/Decidido/Pendiente en el issue y paso a In review por el MCP.
6. `/sincronizar-tickets` pasa a Done cuando el PR está fusionado.
- Muestra el PR con `Closes #N` y los dos veredictos en su descripción.

## 4. Lo que no está perfecto (1:30)

Decirlo tú antes de que lo pregunten es lo que más puntos da. Está en `docs/TRAZABILIDAD.md`, sección 9:
- **La constitución v1.0.0 se escribió a mano**; la v1.1.0 se hizo con `/speckit-constitution`.
- **`/speckit-implement` y `/speckit-converge` no se invocaron**: se implementó siguiendo `tasks.md` a mano. Tenlo preparado: es la desviación más visible respecto a lo que pide el enunciado.
- **El ecosistema (#9) llegó después del #1**, no antes. La constitución v1.1.1 fijó el orden #9 → #10 → #2 para los siguientes.
- **En el #1, las historias US3 y US4 se implementaron antes que sus pruebas**; desde el #2 se respetó pruebas primero.
- **Starlette en lugar de FastAPI** (D1 del #7). Pregúntate por qué lo decidiste antes de grabar; si no lo recuerdas, léelo en `specs/007-chat-eventos-visibles/research.md`.
- **Con el modelo real, el caso 5 no ejerce el hook**: el modelo se negó a saltarse el registro. El hook sí se ejerció forzándolo con un prompt de sistema de prueba (`specs/003-hooks-reglas-negocio/verification.md`). Y la denegación `conflicto` tampoco se ejerció con el modelo, solo con pruebas.
- **Reglas 4 y 5 en la interfaz, solo en parte**: la tarjeta de hallazgo trae fuente y fecha, el informe dice «Sin cubrir: …» y el hallazgo del registro avisa de fechas de constitución distintas (`due_diligence/web/hallazgos.py`). El informe no lista los valores en conflicto con su origen; eso lo declara el texto del coordinador, y el hook lo exige. Los hooks sí imponen las dos reglas.
- **El video de funcionamiento no se grabó**: el workspace de la clave alcanzó su límite de gasto (vuelve el 1 de noviembre). El README lo marca como pendiente. Con el modelo real, los siete casos se recorrieron por la interfaz (`specs/007-chat-eventos-visibles/evidencia/`) y los casos 1 y 2 se repitieron con la versión final. Los demás no se repitieron tras el PR #23.
- **Contradicciones entre frentes distintos**: solo por prompt, no por hook. No la presentes como garantizada.
- **Autenticación**: el SDK usa `ANTHROPIC_API_KEY`; durante el desarrollo se usó el inicio de sesión de claude.ai porque la variable devolvía `Invalid API key`.

## 5. Cierre (0:30)

Una frase por cada eje: el sistema (hooks para lo grave), el ecosistema (cada necesidad con su mecanismo y su alternativa descartada) y el ciclo (cada ticket con su spec, su PR y su revisión independiente). Termina con qué harías distinto: configurar el ecosistema antes de la primera funcionalidad y usar `/speckit-implement`.

---

## Preguntas probables y respuesta corta

**¿Por qué un hook y no una instrucción en el prompt?** Porque el modelo puede equivocarse o ser inducido a ello, y la regla es de negocio. Un hook decide con lo que devolvió el servidor y falla cerrado. Un prompt solo orienta.

**¿Qué pasa si el modelo no llama a `registrar_informe` y escribe la recomendación en texto?** El hook no actúa sobre ese texto. Es un límite declarado (D4 del #3 y sus límites conocidos): el sistema depende de que el informe se registre; el prompt lo exige y el hook `Stop` obliga a escalar cuando corresponde.

**¿Cómo sabes que las pruebas de los hooks no son decorativas?** Mutación: se rompe cada regla a propósito y se comprueba que falla alguna prueba (`scripts/mutate_rules.py`). Varias veces la mutación reveló pruebas débiles y se reforzaron.

**¿Por qué dos capas para restringir herramientas por subagente?** Porque la documentación no confirma que `tools` restrinja herramientas MCP concretas; el hook lo garantiza sin depender de ese detalle y se prueba sin modelo.

**¿Cómo se cumple el paralelismo en Python?** No hay primitiva de «B después de A» documentada; el prompt ordena tres frentes en un mismo turno y listas después, porque depende de datos. Verificado con el modelo real en el caso 1 (D15). La garantía de la dependencia es el hook de la regla 1, no el orden.

**¿Un hook de Claude Code puede llamar al MCP de GitHub?** No; por eso la sincronización de tickets son skills con `allowed-tools` limitadas a `mcp__github__*`. **Descartado**: una GitHub Action, que exige un token con permisos como secreto y no pasa por el MCP.

**¿Qué NO cubre el zip verificado?** Solo detecta claves de Anthropic, tokens de GitHub y claves privadas. Los archivos del zip en UTF-16 sí se leen (`_texts` en `scripts/verify_delivery.py`), pero el historial de git se busca con `git log -G` sobre los bytes, así que un secreto en UTF-16 dentro del historial no lo vería. El enlace del video se valida por su forma. Está en el PR #24.

**¿Cómo evitas datos reales?** Datos ficticios por construcción, hook `real_data_guard.py` en el desarrollo, y los valores con forma de tarjeta o NIT de las pruebas se generan en ejecución, nunca como literales.

## Antes de grabar

- Ejecuta `python -m uv run pytest -q` y ten el resultado a la vista (1.694 pruebas).
- Abre de antemano los archivos de las tablas de arriba, en pestañas, en el orden del guion.
- Ten abierto el PR #24 y el Project para el bloque 3.
- No leas los documentos: señala una línea y explica con tus palabras.
- No afirmes nada que no hayas comprobado con el modelo real; si no lo recuerdas, di «está en `verification.md`».
