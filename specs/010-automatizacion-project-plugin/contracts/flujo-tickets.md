# Contrato: flujo de tickets

## Herramientas MCP permitidas (`allowed-tools` de las skills)

Servidor `github` (toolset `projects` habilitado):

- `mcp__github__projects_list`: campos e ítems del Project.
- `mcp__github__projects_write`: cambiar el estado de un ítem.
- `mcp__github__issue_read`: contenido del issue.
- `mcp__github__add_issue_comment`: comentario de avance.
- `mcp__github__list_pull_requests`, `mcp__github__pull_request_read`: estado y fusión de los pull requests.

Más `Bash(git status:*)`, `Bash(git log:*)` y `Bash(git branch:*)` solo de lectura. Ninguna escritura sobre archivos.

## `siguiente-ticket` — `argument-hint: [número]`

| Entrada | Resultado |
|---|---|
| sin argumento | ejecuta la sincronización, elige el siguiente ticket por el orden de `data-model.md`, lo pasa a `In Progress`, muestra título y contenido del issue como insumo de `/speckit-specify` y dice por qué lo eligió |
| número de ticket | igual, pero para ese ticket (avisa si salta el orden) |
| ya hay un ticket `In Progress` | lo informa y pide confirmación antes de tomar otro |
| el elegido depende de uno abierto | lo advierte y propone el correcto |
| no quedan tickets en `Todo` | lo dice; no modifica nada |
| servidor o toolset no disponibles | se detiene, dice qué falta; no modifica nada |

## `sincronizar-tickets` — sin argumentos

1. Lee los ítems del Project con su estado y los pull requests del repositorio.
2. Para cada ticket aplica las transiciones permitidas de `data-model.md`.
3. Informa de cada cambio (`#N: In review → Done, por el PR #M fusionado`) o de que todo está al día.
4. Idempotente: sin cambios en la realidad, la segunda ejecución no modifica nada.
5. Un ticket que no está en el Project se informa; no se añade sin confirmación.
6. Un pull request cerrado sin fusionar se informa y no cambia el estado.

## `/abrir-pr <número>` (ampliado)

Después de los dos veredictos y de la confirmación de la persona:

1. `git push -u origin HEAD` y `gh pr create` con `Closes #N`.
2. Comentario de avance en el issue con las tres secciones de `data-model.md`.
3. Ticket a `In review` con `mcp__github__projects_write`.
4. Si el MCP o el toolset no están disponibles: lo dice explícitamente y no declara el ticket movido.

## Errores

Cualquier fallo de una llamada al MCP se muestra con su mensaje y detiene el flujo en ese punto, indicando qué ya se hizo y qué no (sin transiciones parciales ocultas).

## Nombres verificados

Comprobados el 2026-10-16 en la sesión (herramientas disponibles del servidor `github`) y con `list_project_fields` sobre el Project nº 4:

- Herramientas: `mcp__github__projects_list`, `mcp__github__projects_write`, `mcp__github__issue_read`, `mcp__github__add_issue_comment`, `mcp__github__list_pull_requests`, `mcp__github__pull_request_read`.
- Campo `Status` (single select, id 426295783), opciones exactas: `Todo`, `In Progress`, `In review`, `Done`. Para cambiar el estado se usa `projects_write` con `method: update_project_item`, `owner`, `project_number: 4`, `item_owner`, `item_repo`, `issue_number` y `updated_field: {"name": "Status", "value": "<opción>"}`.
