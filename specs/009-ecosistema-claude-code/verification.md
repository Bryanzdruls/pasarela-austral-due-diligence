# Verificación del ticket #9 (T035 y T036)

Fecha: 2026-10-16. Rama `009-ecosistema-claude-code`.

## T035: pruebas, estilo y mutación

| Comprobación | Resultado |
|---|---|
| `pytest -q` (todo el repositorio) | 487 pruebas en verde (antes de añadir una prueba nueva del hook de formato) |
| `ruff check .` | Sin avisos |
| `ruff format --check .` | 91 archivos ya formateados |
| `python scripts/verify_ecosystem.py` | Código 0, "Ecosistema completo" (10 comprobaciones OK) |

`uv` no está instalado en este equipo (`python -m uv` falla), así que se ejecutaron `python -m pytest` y `python -m ruff` directamente, con el mismo resultado esperado.

### Mutación de los hooks

Se rompió cada hook a propósito, se corrieron las pruebas de `.claude/hooks/tests/` y se restauró el archivo.

| Mutación | Resultado |
|---|---|
| `block()` no hace nada (permitir siempre) | Detectada |
| La máscara no oculta los dígitos | Detectada |
| Ignorar los archivos `.env.*` (p. ej. `.env.local`) | Detectada |
| `chat/` deja de contar como directorio excluido de producción | Detectada |
| El hook de formato también procesa `.md` | **Sobrevivió** con las pruebas originales: `ruff` deja intacto un `.md`, así que la prueba de "no se modifican" no lo distinguía. Se añadió `test_the_formatter_is_never_invoked_for_files_that_are_not_python`, que comprueba que el formateador ni se invoca; con ella la mutación se detecta |

## T036: Claude Code real

Hecho en la sesión viva de Claude Code, con los hooks cargados desde `.claude/settings.json`.

| Caso provocado | Resultado observado |
|---|---|
| `Write` de un `.py` con un número con forma de tarjeta válida | Bloqueado por `real_data_guard.py`: "Contenido con forma de tarjeta reales: **************66" (valor enmascarado) |
| `Write` de `.env.local` | Denegado por `permissions.deny` (primera capa) |
| `Bash` con `cat` sobre `.env.local` | Bloqueado por `secrets_guard.py` (capa de respaldo) |
| `Bash` con un script que nombraba `.env.local` en su texto | Bloqueado por `secrets_guard.py`, mismo mensaje |
| `Write` de un `.py` de producción en una rama `099-prueba` sin `specs/099-*` | Bloqueado por `spec_gate.py`: "La rama no corresponde a un ticket…" |
| `Write` de un `.py` en la rama `009-…` con spec, plan y tareas | Permitido |
| `Write` de un `.py` tras el que actúa el formateador | El hook `PostToolUse` reformateó el archivo (se notificó la modificación) |

Las ramas temporales se borraron y el árbol volvió a `009-ecosistema-claude-code`.

### Sin verificar

No se ejecutaron los comandos interactivos `/hooks` y `/memory` (no se pueden lanzar desde la propia sesión del agente): comprobar a mano que `/hooks` lista los cuatro hooks y que `/memory` muestra `CLAUDE.md` y las reglas. Además, el servidor MCP `pasarela-fuentes` no conectó en esta sesión (`CONNECTION_CLOSED`); su verificación real queda pendiente.

## Correcciones tras la revisión independiente

`code-reviewer` devolvió `corregir antes del PR`. Se corrigieron los hallazgos importantes, cada uno con prueba nueva (`.claude/hooks/tests/test_bypasses.py` y `test_secrets_guard.py`):

- `ls && cat <secreto>` y similares: la orden se juzga por tramos y una sustitución de comandos nunca se trata como segura.
- Mensajes de commit o PR con `$(...)` o comillas invertidas entre comillas dobles (o heredoc sin comillas): ya no se recortan.
- Redirección pegada a la palabra (`echo x>ruta.py`): ahora la detecta `spec_gate`.
- El hook de secretos también cubre `Grep`, `Glob` y `PowerShell`; los otros dos hooks cubren `PowerShell`.
- `docs/TRAZABILIDAD.md`: se quitó la afirmación de un escaneo automático en cada commit (no hay hook de git) y se anotó que el arranque de `pasarela-fuentes` está sin verificar.

### Segunda ronda

`code-reviewer` volvió a devolver `corregir antes del PR` por una regresión de la corrección de mensajes: un heredoc de otra orden encadenada tras `git commit` quedaba oculto. Se corrigió (el cuerpo solo se poda si no hay separadores antes del `<<`), se cerró también `ls > <secreto>` (una redirección ya no vuelve segura la orden) y se documentaron como límites conocidos en `docs/ECOSISTEMA.md` los huecos de `Grep` sobre directorios y del recorte por expresiones regulares. Pruebas en `test_bypasses_round2.py`.
