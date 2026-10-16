# Ecosistema de Claude Code

Qué pieza hay, qué necesidad cubre, por qué está donde está y qué alternativa se descartó. Detalle y fuentes en `specs/009-ecosistema-claude-code/research.md` (D1 a D15). `python scripts/verify_ecosystem.py` comprueba que esta tabla y el disco coinciden: una pieza sin fila o una fila sin archivo hacen fallar la verificación.

Las skills y comandos de Spec Kit (`speckit-*`) vienen del flujo de especificación y no cuentan como piezas propias.

| Pieza | Tipo | Necesidad | Ubicación | Por qué ahí | Alternativa descartada |
|---|---|---|---|---|---|
| `CLAUDE.md` | Memoria de proyecto | N1 convenciones al clonar | Raíz | Se carga al abrir el proyecto; es corto y delega el detalle con `@docs/convenciones.md` | Un único archivo enorme (siempre en contexto y mezcla zonas) |
| `mcp_server/CLAUDE.md` | Memoria de subdirectorio | N1 | Zona del servidor de fuentes | Se carga solo al trabajar en esa zona, sin gastar contexto en el resto | Copiar sus convenciones en la raíz |
| `due_diligence/CLAUDE.md` | Memoria de subdirectorio | N1 | Zona del coordinador | Igual que la anterior, para el coordinador y los subagentes | Copiar sus convenciones en la raíz |
| `docs/convenciones.md` | Convenciones importadas | N1 | `docs/`, importado por la raíz | Mantiene la raíz corta y es legible también fuera de Claude Code | Duplicarlas en cada `CLAUDE.md` |
| `.claude/rules/tests.md` | Regla con `paths` | N3 convenciones de pruebas en varias carpetas | `.claude/rules/` | Con `paths` solo se carga al tocar pruebas, y se escribe una sola vez | Una regla de pruebas dentro de cada `CLAUDE.md` (diverge) |
| `.claude/rules/datos-ficticios.md` | Regla con `paths` | N5 datos solo ficticios | `.claude/rules/` | Orienta al editar `mcp_server/data/`; lo grave lo bloquea un hook | Dejarlo solo en el hook (el hook no explica cómo hacerlo bien) |
| `.claude/rules/specs.md` | Regla con `paths` | N4 especificación antes del código | `.claude/rules/` | Se carga al editar `specs/`, donde se aplican las plantillas | Reglas sin `paths` (siempre en contexto) |
| `.claude/agents/code-reviewer.md` | Subagente, solo lectura | N8 revisión independiente | `.claude/agents/` | `Read`, `Grep` y `Glob` bastan para revisar y no puede cambiar lo que revisa; contexto propio | Revisar en la misma sesión que escribió el código |
| `.claude/agents/compliance-reviewer.md` | Subagente, solo lectura | N9 revisión de cumplimiento | `.claude/agents/` | Contrasta las reglas de negocio 1 a 5 con especificación, código y pruebas; marca falta grave lo que dependa solo de un prompt | Ampliar `code-reviewer` (mezcla dos misiones) |
| `.claude/skills/revisar-cumplimiento/SKILL.md` | Skill, `context: fork` | N9 | `.claude/skills/` | Lanza al revisor de cumplimiento en un contexto aislado, con `allowed-tools` de solo lectura y `argument-hint` | Un comando (no admite `context: fork`) |
| `.claude/skills/verificar-ecosistema/SKILL.md` | Skill, `allowed-tools` | Verificación de los mínimos | `.claude/skills/` | Ejecuta `scripts/verify_ecosystem.py` y resume el resultado, con solo ese comando permitido | Una lista manual que se desactualiza |
| `.claude/commands/abrir-pr.md` | Comando propio | N8 y N9 flujo antes del PR | `.claude/commands/` | Es el flujo del equipo: verifica, lanza las dos revisiones y vuelca ambos veredictos en el PR | Dejar la revisión de cumplimiento como paso manual |
| `.claude/settings.json` | Configuración del proyecto | N4 a N7 | `.claude/`, versionado | Registra los hooks para todo el equipo; `settings.local.json` queda para preferencias personales | Comandos en línea (no se pueden probar) |
| `.claude/settings.json#permissions.deny` | Permisos | N6 secretos | Dentro de `settings.json` | Primera capa: niega leer y editar `.env`, `.env.local`, `.env.production`, `secrets/**`, `*.pem` y `*.key`; `.env.example` sigue accesible | `.env*` como comodín (taparía la plantilla) |
| `.claude/hooks/spec_gate.py` | Hook `PreToolUse`, bloquea | N4 | `.claude/hooks/` | Impide escribir código de producción sin `spec.md`, `plan.md` y `tasks.md` de la feature activa, también por `Bash` | Una instrucción en `CLAUDE.md` (no bloquea) |
| `.claude/hooks/real_data_guard.py` | Hook `PreToolUse`, bloquea | N5 | `.claude/hooks/` | Detecta tarjeta con Luhn, NIT y documento con etiqueta, y enmascara el valor en el aviso | Lista fija de ejemplos (obligaría a escribirlos en el repo) |
| `.claude/hooks/secrets_guard.py` | Hook `PreToolUse`, bloquea | N6 | `.claude/hooks/` | Segunda capa tras `permissions.deny`: inspecciona rutas y el texto de las órdenes `Bash` | `permissions.deny` como única capa |
| `.claude/hooks/format_after_edit.py` | Hook `PostToolUse` | N7 formateo | `.claude/hooks/` | Formatea con `ruff` tras cada edición de `.py`; nunca bloquea | Formatear en `Stop` (el archivo queda mal mientras se trabaja) |
| `.mcp.json` | Servidores MCP | MCP de GitHub y propio | Raíz | Declara GitHub (con el toolset `projects`, token por `${GITHUB_PERSONAL_ACCESS_TOKEN}`) y `pasarela-fuentes` por stdio; sin credenciales | Pegar el token en el archivo |
| `scripts/verify_ecosystem.py` | Verificación | Mínimos del enunciado | `scripts/` | Convierte los mínimos en una comprobación repetible con código de salida | Revisarlos a mano |

## Límites conocidos

Los hooks reducen el riesgo, no lo eliminan. Esto es lo que no cubren:

- Una orden que construya en tiempo de ejecución el nombre del archivo o el valor sensible puede eludir la inspección del texto de `Bash`.
- `Grep` y `Glob` se revisan por su `path` y su `glob`: una búsqueda sobre un directorio sin filtro (`path: "."`) o con un patrón de nombre amplio (`.e*`, `*.env`) puede devolver líneas de un archivo de secretos; ahí solo protege `permissions.deny`, que tampoco cubre `Grep`.
- El hook de secretos inspecciona el texto entero de la orden, también el de un mensaje de commit o de pull request: un mensaje que nombre un archivo de secretos se bloquea. Se decidió así tras varias revisiones que seguían evadiendo la poda de mensajes con expresiones regulares: se prefiere un falso bloqueo a una lectura permitida. El mensaje se escribe en un archivo y se pasa con `git commit -F archivo`.
- El hook de datos reales no reconoce una tarjeta pegada a un prefijo (`card_<16 dígitos>`) ni con puntos como separador, y puede bloquear un número largo con suma de verificación válida que no es una tarjeta (p. ej. una marca de tiempo en milisegundos).
- El hook de secretos no exime ninguna orden: `ls` de un archivo de secretos también se bloquea. Une las comillas y quita las barras invertidas antes de comparar, pero no expande variables ni sustituciones.
- En `Bash` y `PowerShell`, una búsqueda recursiva sobre un directorio (`grep -r KEY .`, `Get-ChildItem -Recurse | Select-String`) puede leer un archivo de secretos sin nombrarlo; `rm`, `cp` o `git -C` sobre el directorio de secretos a secas y `git show HEAD:<ruta>` tampoco se detectan.
- `NotebookEdit` no está cubierto: el proyecto no usa notebooks.
- El aislamiento a nivel de sistema operativo requeriría el modo aislado (sandbox) de Claude Code, fuera de alcance.
- Los hooks de proyecto se leen al arrancar la sesión y requieren la confianza del proyecto: un hook defectuoso solo protege tras reiniciar.
- Estos hooks son de Claude Code y protegen el desarrollo. Las reglas de negocio 1 a 3 de la pasarela se garantizan con hooks del Agent SDK (ticket #3) y siguen abiertas hasta entonces.
- **Abiertos tras la séptima revisión (no corregidos):** el hook de secretos compara texto y no interpreta el shell. No cubre globs y llaves (`.e{n,}v`, `.en[v]`), la cita `$'...'` de Bash, la continuación de línea con `\`, el acento grave de PowerShell dentro de un nombre, los flujos alternos de NTFS (`archivo::$DATA`) ni un `cd` a un directorio de secretos seguido de un nombre relativo. La barrera que sí los cubre es `permissions.deny` para las herramientas de archivo; para `Bash` y `PowerShell` es un riesgo aceptado y declarado.
