# Convenciones del equipo

Complementa a la constitución (`.specify/memory/constitution.md`), que manda en caso de duda. Lo importa `CLAUDE.md`, así que Claude Code lo recibe al abrir el proyecto.

## Qué va dónde (principio III de la constitución)

| Si incumplirlo… | Se hace cumplir con… | Ejemplo |
|---|---|---|
| causa daño o invalida la entrega | un **hook** determinista que bloquea | datos reales, secretos, código sin especificación |
| es una convención o una preferencia de estilo | `CLAUDE.md` o una regla de `.claude/rules/` | nombres, formato de commits, cómo se escriben las pruebas |
| es una opinión personal | `CLAUDE.local.md` / `.claude/settings.local.json` (no se versionan) | tu editor, tus atajos |

Una instrucción en un prompt o en este archivo **nunca** sustituye a un hook para lo grave.

## Código

- Python 3.12, `ruff` como formateador y linter (`line-length = 100`). Los hooks formatean tras cada edición.
- Identificadores del dominio en español (`comercio`, `frente`, `hallazgos`, `representante_legal`); términos técnicos y nombres de pruebas en inglés (`test_a_valid_card_number_is_blocked`).
- Docstrings y comentarios en español, breves: explican el *porqué*, no repiten el código.
- Solo biblioteca estándar en los hooks y en `scripts/`; el resto de dependencias se declara en `pyproject.toml`.

## Pruebas

- Junto al código que prueban (`mcp_server/**/tests/`, `due_diligence/**/tests/`, `.claude/hooks/tests/`, `scripts/tests/`).
- Primero la prueba, se ejecuta y se ve fallar por la razón esperada; después se implementa. Una prueba que solo comprueba un código de salida vacío no prueba nada: comprueba también el mensaje o el efecto.
- Ninguna prueba llama al modelo real. Los hooks se prueban ejecutando el script real con JSON por stdin.
- Los valores con forma de tarjeta, NIT o documento se **generan en tiempo de ejecución**; nunca se escriben literales.

## Datos

- Todo dato es ficticio: identificadores `CO-XX-000N`, documentos y NIT `FICT-000N`, fuentes terminadas en `_ficticio` o `_ficticia`.
- Ninguna credencial en el repositorio. Los secretos llegan por variables de entorno (`ANTHROPIC_API_KEY`, `GITHUB_PERSONAL_ACCESS_TOKEN`); `.env.example` solo lleva los nombres.

## Git y GitHub

- Una rama por ticket, con el número del issue: `009-ecosistema-claude-code`.
- Mensajes de commit en español, en imperativo, con el cuerpo explicando el porqué y `Refs #N` (o `Closes #N` en el PR). Incluyen los trailers de atribución que indique la sesión.
- Antes de abrir un PR: `/abrir-pr N` (revisión independiente y de cumplimiento). El PR cierra su issue y el ticket pasa a In review y luego a Done.
- El historial no se reescribe.

## Flujo de un ticket (Spec Kit)

`/speckit-specify` → (`/speckit-clarify`) → `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → implementar con pruebas primero → `/abrir-pr`. El hook de especificación impide escribir código de producción sin `spec.md`, `plan.md` y `tasks.md`.
