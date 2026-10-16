# Contrato: hooks de proyecto y verificación de mínimos

## Entrada común de los hooks (stdin, JSON)

Campos usados: `hook_event_name`, `tool_name`, `tool_input`, `cwd`. Según la herramienta, `tool_input` trae:

| Herramienta | Campos |
|---|---|
| `Edit` | `file_path`, `old_string`, `new_string`, `replace_all` |
| `Write` | `file_path`, `content` |
| `Read` | `file_path`, `offset`, `limit` |
| `Bash` | `command`, `description`, `timeout` |

`file_path` llega absoluta y, en Windows, con barras invertidas: se normaliza antes de comparar.

## Salida

- Permitir: código de salida 0, sin salida.
- Bloquear: código de salida 2 con el motivo por stderr (una o dos líneas: qué se detectó y qué hacer).
- Ante una excepción propia de un hook de bloqueo: código de salida 2 con el mensaje `El hook <nombre> falló y deniega por seguridad: <error>`.

## `spec_gate.py` — PreToolUse, matcher `Edit|Write|Bash|PowerShell`

| Entrada | Resultado |
|---|---|
| Ruta de código de producción y feature activa con `spec.md`, `plan.md` y `tasks.md` | permitir |
| Ruta de código de producción y feature sin alguno de los artefactos | bloquear: "Falta <artefacto> en specs/<carpeta>/. Ejecuta /speckit-<comando> antes de escribir código." |
| Ruta de código de producción sin ticket en la rama | bloquear: "La rama no corresponde a un ticket (NNN-…): no hay especificación activa." |
| Cualquier otra ruta (documentos, specs, docs, pruebas, scripts, configuración, datos) | permitir |
| `Bash` que escribe (redirección, `tee`, `Set-Content`, `Out-File`, `sed -i`, `cp`, `mv`, `python` que abre para escribir) a una ruta de producción, con los artefactos incompletos | bloquear con el mismo mensaje |
| `Bash` que solo lee o ejecuta (`cat`, `ls`, `pytest`, `git`) | permitir |

## `real_data_guard.py` — PreToolUse, matcher `Edit|Write|Bash|PowerShell`

Revisa `content` (Write), `new_string` (Edit) o el texto de `command` (Bash). Bloquea con "Contenido con forma de <tarjeta|NIT|documento> reales: <fragmento enmascarado>. Usa un identificador ficticio (FICT-NNNN)." El fragmento mostrado se enmascara (no se repite completo). Cualquier otro contenido: permitir.

## `secrets_guard.py` — PreToolUse, matcher `Read|Edit|Write|Bash|PowerShell|Grep|Glob`

- `Read`, `Edit`, `Write`: bloquea si la ruta es un archivo protegido (ver el modelo de datos); permite `.env.example`.
- `Bash` y `PowerShell`: bloquea si el texto de la orden nombra un archivo protegido, sin mirar el verbo (también `ls`) y comparando además el texto sin comillas ni barras invertidas; permite `.env.example`.
- `Grep` y `Glob`: bloquea si `path` o `glob` nombran un archivo o directorio protegido.

## `format_after_edit.py` — PostToolUse, matcher `Edit|Write`

Si `file_path` termina en `.py`: ejecuta el formateador sobre ese archivo (`ruff format <archivo>`; si no hay `ruff`, `python -m uv run ruff format <archivo>`). Siempre sale con 0: si no hay formateador, o falla, escribe un aviso por stderr sin bloquear. Para cualquier otra extensión no hace nada.

## `settings.json`

```
hooks.PreToolUse   -> [ {Edit|Write|Bash|PowerShell: spec_gate.py, real_data_guard.py},
                        {Read|Edit|Write|Bash|PowerShell|Grep|Glob: secrets_guard.py} ]
hooks.PostToolUse  -> [ {Edit|Write: format_after_edit.py} ]
permissions.deny   -> Read/Edit de .env, .env.local, .env.production, secrets/**, *.pem, *.key
```

Cada hook: `type: command`, `command: python`, `args: ["${CLAUDE_PROJECT_DIR}/.claude/hooks/<script>.py"]`, `timeout: 30`.

## `scripts/verify_ecosystem.py`

- Uso: `python scripts/verify_ecosystem.py [--json]`.
- Salida: una línea por mínimo (`OK` o `FALLA` con el motivo) y, al final, el resumen. Con `--json`, un objeto con la lista de comprobaciones.
- Código de salida: 0 si todos los mínimos se cumplen; 1 si alguno falla.
- Comprobaciones: las de D12 de `research.md`.
