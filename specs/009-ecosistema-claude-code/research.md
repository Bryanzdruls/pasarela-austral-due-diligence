# Research: Ecosistema de Claude Code

Fuente: documentación oficial de Claude Code consultada el 2026-10-16 (code.claude.com/docs/en: `memory`, `sub-agents`, `skills`, `hooks`, `hooks-guide`, `settings`, `permissions`, `setup`). Lo que la documentación no confirma se marca **[No confirmado]** y se comprueba con una prueba o manualmente.

Cada decisión registra *dónde vive la pieza, por qué ahí y qué alternativa se descartó*; es el insumo del `DECISIONES.md` (ticket #11) y del inventario `docs/ECOSISTEMA.md`.

## D1. `CLAUDE.md` con jerarquía: raíz + subdirectorios + una importación
- **Dónde**: `CLAUDE.md` (raíz), `mcp_server/CLAUDE.md`, `due_diligence/CLAUDE.md`; la raíz importa `docs/convenciones.md` con `@docs/convenciones.md`.
- **Por qué**: los de la raíz y sus superiores se cargan al arrancar; los de subdirectorio se cargan **bajo demanda** al leer archivos de esa zona, así las convenciones del servidor de fuentes y las del coordinador no ocupan contexto cuando no se trabaja en ellas. La importación mantiene la raíz corta (< 200 líneas recomendadas) y reutilizable. Las rutas del `@import` son relativas al archivo que importa y admiten hasta 4 saltos.
- **Alternativas descartadas**: un único `CLAUDE.md` enorme (siempre en contexto, mezcla zonas); copiar las convenciones en cada subdirectorio (duplicación); `.claude/CLAUDE.md` (oculta lo que debe verse al clonar).

## D2. Preferencias personales fuera de git
- **Dónde**: `CLAUDE.local.md` y `.claude/settings.local.json`, ambos en `.gitignore` (ya presentes).
- **Por qué**: `CLAUDE.local.md` **no** se ignora automáticamente: hay que añadirlo a `.gitignore`. `settings.local.json` tiene mayor precedencia que `settings.json`, así que cada persona puede sobrescribir sin afectar al equipo.
- **Alternativa descartada**: guardar preferencias en `~/.claude` y no documentar nada (el equipo no sabría dónde ponerlas).

## D3. Reglas con alcance por ruta
- **Dónde**: `.claude/rules/tests.md` (`paths`: `**/tests/**/*.py`, `**/test_*.py`), `.claude/rules/datos-ficticios.md` (`paths`: `mcp_server/data/**`), `.claude/rules/specs.md` (`paths`: `specs/**`).
- **Por qué**: una regla con `paths` solo se carga cuando se lee, escribe o edita un archivo que coincide (Read, Write, Edit). Las convenciones de tests aplican igual en todas las carpetas de tests sin repetirse (necesidad N3). Las reglas sin `paths` se cargan siempre, por eso las tres llevan alcance.
- **Alternativa descartada**: una regla de tests dentro de cada `CLAUDE.md` de subdirectorio (se duplica y diverge); reglas sin `paths` (siempre en contexto).
- **[No confirmado]**: que Grep y Glob también activen las reglas; no se depende de ello.

## D4. Hooks de proyecto en `.claude/settings.json`
- **Dónde**: `.claude/settings.json` (versionado), apuntando a scripts en `.claude/hooks/`.
- **Por qué**: lo que invalida la entrega o causa daño se hace cumplir con un hook determinista (constitución, principio III). Un `PreToolUse` que deniega aplica en todos los modos de permisos, incluido el que salta confirmaciones. El bloqueo se hace con código de salida 2 y el motivo por stderr; cualquier otro código distinto de 0 y 2 no bloquea, por eso los scripts capturan sus propios errores y salen con 2.
- **Matcher**: `Edit|Write` (sensible a mayúsculas). **[No confirmado]** `MultiEdit`; no se usa.
- **Alternativas descartadas**: instrucciones en `CLAUDE.md` (no bloquean); `permissions.deny` como única capa (no inspecciona contenido ni la feature activa); comandos en línea dentro de `settings.json` (no se pueden probar ni leer cómodamente).

## D5. Hooks como scripts de Python con biblioteca estándar
- **Dónde**: `.claude/hooks/*.py`; en `settings.json` el comando es `python` con `args` (forma ejecutable) y `${CLAUDE_PROJECT_DIR}` para la ruta.
- **Por qué**: se prueban ejecutándolos con JSON por stdin; no dependen del entorno virtual; el comando `python` está en el PATH de la máquina de desarrollo. En la forma ejecutable, `command` debe ser un `.exe` real y los `args` evitan problemas de comillas con rutas con espacios (el repo vive en una ruta con espacios).
- **[No confirmado]** en la documentación: `python` frente a `py -3` en Windows; se comprueba ejecutando los hooks reales en esta máquina antes de darlos por buenos.
- **Alternativas descartadas**: PowerShell (solo Windows); `-ExecutionPolicy Bypass` (no se salta ninguna política de ejecución); bash (depende de Git Bash).

## D6. Hook de especificación previa (`spec_gate.py`, necesidad N4)
- **Dónde**: `PreToolUse` sobre `Edit|Write`.
- **Regla**: bloquea escribir código de producción (archivos `.py` bajo `mcp_server/`, `due_diligence/` y los directorios de la lista, excluyendo `tests/`) si la feature activa no tiene `spec.md`, `plan.md` y `tasks.md` en `specs/`.
- **Feature activa**: primero el prefijo numérico de la rama (`009-...` → `specs/009-*`); si la rama no tiene prefijo numérico, el puntero `.specify/feature.json`. Sin feature, se bloquea.
- **Por qué rama primero**: `.specify/feature.json` está ignorado por git y apunta a la última especificación creada, que puede no ser la del ticket actual; el nombre de la rama es la fuente fiable de cada ticket.
- **Alternativa descartada**: exigir solo `spec.md` (el enunciado dice "su especificación", pero la constitución exige especificación, plan y tareas).

## D7. Hook de datos reales (`real_data_guard.py`, necesidad N5)
- **Qué detecta**: números de tarjeta de 13 a 19 dígitos (contiguos o en grupos de cuatro) que pasen la comprobación de Luhn; NIT con forma `NNN.NNN.NNN-D` o `NNNNNNNNN-D`; y cédula o NIT precedidos de una etiqueta (`cédula`, `CC`, `NIT`, `documento`, `identificación`) con 6 a 10 dígitos.
- **Qué no bloquea**: los identificadores ficticios del proyecto (`FICT-0001`, `CO-TV-0001`) y números que no cumplen las formas anteriores.
- **Por qué solo con etiqueta para documentos**: un número de 8-10 dígitos suelto aparece en marcas de tiempo y sumas de verificación; sin etiqueta habría falsos positivos constantes. Las tarjetas se filtran por Luhn.
- **Pruebas**: los ejemplos sensibles se construyen en tiempo de ejecución (un generador de números con dígito de control válido); ningún archivo contiene el valor literal.
- **Alternativa descartada**: lista de ejemplos fijos (no generaliza y obligaría a escribir los valores en el repositorio).

## D8. Hook de secretos (`secrets_guard.py`) y `permissions.deny` (necesidad N6)
- **Dónde**: `PreToolUse` sobre `Read|Edit|Write|Bash`, más `permissions.deny` en `settings.json`.
- **Dos capas**: `permissions.deny` con los nombres explícitos (`.env`, `.env.local`, `.env.production`, `secrets/**`, `*.pem`, `*.key`) y el hook como red de seguridad que inspecciona `file_path` y, en Bash, el texto del comando.
- **Por qué dos capas**: `deny` también cubre `cat .env` en Bash, pero no subprocesos que abren archivos por su cuenta (por ejemplo `python -c "open('.env')"`); el hook revisa el texto del comando y cierra parte de ese hueco. La plantilla `.env.example` debe seguir accesible, por eso `deny` no usa el comodín `.env*` y la excepción se resuelve en el hook.
- **Límite conocido**: un comando que construya el nombre del archivo en tiempo de ejecución puede eludir la inspección de texto; el aislamiento a nivel de sistema operativo requeriría el modo aislado (sandbox), que queda fuera de alcance y se documenta.

## D9. Hook de formateo (`format_after_edit.py`, necesidad N7)
- **Dónde**: `PostToolUse` sobre `Edit|Write`.
- **Qué hace**: ejecuta el formateador del proyecto solo sobre archivos `.py` editados. Busca `ruff` en el PATH y, si no está, usa `python -m uv run ruff`; si no hay ninguno, avisa sin bloquear (un fallo posterior a la edición no debe perder la edición).
- **Por qué `PostToolUse`**: actúa tras la edición, que es lo que pide el enunciado; no bloquea.
- **Alternativa descartada**: formatear en un hook de `Stop` (formatea todo al final, pero el archivo queda mal formateado mientras se trabaja).

## D10. Segundo subagente: revisión de cumplimiento (`compliance-reviewer`, necesidad N9)
- **Dónde**: `.claude/agents/compliance-reviewer.md`, herramientas `Read, Grep, Glob`.
- **Por qué solo lectura**: un revisor no debe poder cambiar lo que revisa; es independiente de la sesión que escribió el código porque tiene contexto propio.
- **Qué hace**: por cada regla de negocio (1 a 5) busca la implementación, la especificación y las pruebas, y reporta cumplida / parcial / ausente con evidencia; reporta como **falta grave** cualquier regla 1-3 que dependa solo de un prompt.
- **Alternativa descartada**: ampliar `code-reviewer` (mezcla dos misiones y dificulta reutilizar cada una por separado).

## D11. Skills (necesidad N9 y verificación del ecosistema)
- **`revisar-cumplimiento`** (`context: fork`, `agent: compliance-reviewer`, `allowed-tools: Read Grep Glob`, `argument-hint: <ticket>`): lanza la revisión de cumplimiento en un contexto aislado. **[No confirmado]** que `agent` acepte un subagente propio; si no, se usa `general-purpose` con el mismo prompt, y se comprueba a mano.
- **`verificar-ecosistema`** (`allowed-tools: Bash(python scripts/verify_ecosystem.py*)`, `argument-hint: [--json]`): ejecuta la verificación automática de mínimos y resume el resultado.
- **Por qué skills y no solo comandos**: skills y comandos crean ambos `/nombre`, pero las skills admiten `context: fork` y carpeta de apoyo, y la documentación las recomienda para trabajo nuevo. `/abrir-pr` queda como comando porque es el flujo del equipo ya existente.
- **Mínimo del enunciado**: entre las dos usan `context: fork`, `allowed-tools` y `argument-hint`.

## D12. Verificación automática de mínimos (`scripts/verify_ecosystem.py`)
- **Qué comprueba**: `CLAUDE.md` raíz y al menos un `CLAUDE.md` de subdirectorio o una importación; al menos 2 reglas con `paths`; al menos 2 subagentes con `tools` restringidas a lectura; al menos 2 skills (excluyendo las de Spec Kit) que usen entre todas `context: fork`, `allowed-tools` y `argument-hint`; al menos 2 hooks de proyecto incluyendo un `PreToolUse` y un `PostToolUse`; al menos 1 comando propio; `.mcp.json` con GitHub (toolset `projects`) y el servidor propio, sin credenciales; y que cada pieza del disco tenga su fila en `docs/ECOSISTEMA.md`.
- **Por qué**: convierte los mínimos del enunciado en una comprobación repetible; falla indicando qué pieza falta. El plugin lo comprueba el ticket #10.
- **Alternativa descartada**: una lista manual (se desactualiza).

## D13. Qué queda fuera
- Plugin reutilizable y automatización del flujo de tickets: ticket #10. `DECISIONES.md`: ticket #11. Los hooks del Agent SDK (reglas de negocio 1-3): ticket #3; no se confunden con los hooks de Claude Code de este ticket.
