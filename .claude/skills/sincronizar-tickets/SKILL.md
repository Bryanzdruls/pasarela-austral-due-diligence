---
name: sincronizar-tickets
description: Reconcilia el estado de los tickets del GitHub Project de Pasarela Austral con el de sus pull requests (pasa a Done los ya fusionados) y informa cada cambio. Úsala tras fusionar un pull request, al empezar una sesión o cuando el Project no refleje la realidad; es idempotente.
allowed-tools: mcp__github__projects_list, mcp__github__projects_write, mcp__github__list_pull_requests, mcp__github__pull_request_read, mcp__github__issue_read
---

Vas a sincronizar el Project nº 4 del repositorio `Bryanzdruls/pasarela-austral-due-diligence` con la realidad de sus pull requests. Toda lectura y escritura del backlog pasa por el servidor MCP de GitHub (toolset `projects`).

**Autorización.** Invocar esta skill es la autorización expresa de la persona para que se apliquen los cambios de estado de abajo. Antes de aplicarlos, lista cada uno; después de cada llamada, informa su resultado.

## Si el servidor o el toolset no están disponibles

Si una herramienta `mcp__github__projects_*` no existe o falla por conexión o permisos, **no modifiques nada**: di qué falta (servidor `github` conectado, cabecera `X-MCP-Toolsets: default,projects` y el token por variable de entorno) y detente.

## Pasos

1. **Lee el Project.** `mcp__github__projects_list` con `method: list_project_items`, `owner: Bryanzdruls`, `project_number: 4` y `field_names: ["Status"]`; pagina hasta el final. Estados exactos: `Todo`, `In Progress`, `In review`, `Done`.
2. **Lee los pull requests** del repositorio con `mcp__github__list_pull_requests` (todos los estados) y, si hace falta, `mcp__github__pull_request_read` para su cuerpo y su fecha de fusión.
3. **Asocia cada ticket con su pull request.** La señal principal es que el cuerpo contenga `Closes #N` (o `Fixes #N`). Solo si ningún pull request lo cierra, usa como respaldo que la **rama** empiece por el número del ticket (`010-…`). **Un pull request cuyo cuerpo solo dice `Refs #N` no cierra el ticket**: no lo uses para marcarlo `Done` aunque su rama empiece por ese número (por ejemplo, una rama de corrección `009-fix-…`); solo se informa. El número debe coincidir completo (`Closes #1` no es `Closes #11`). Considera **fusionado** solo un pull request con fecha de fusión (`merged_at` no nula): lee `mcp__github__pull_request_read` (`method: get`) cuando la lista no la traiga; un pull request cerrado no es un pull request fusionado. Si hay varios que cierran el mismo ticket, usa el más reciente.
4. **Aplica solo estas transiciones**:

   | Situación | Cambio |
   |---|---|
   | pull request fusionado y el ticket está en `In review` | `In review` → `Done` |
   | pull request fusionado y el ticket sigue en `In Progress` (fusión hecha fuera del flujo) | `In Progress` → `Done` |
   | pull request abierto y el ticket está en `In Progress` | informa; el paso a `In review` lo hace `/abrir-pr`, no esta skill |
   | pull request **cerrado sin fusionar** | no cambia nada; informa |
   | ticket sin pull request | no cambia nada |

   Cualquier otra combinación solo se informa. Nunca marques `Done` un ticket cuyo pull request no se fusionó, ni por haber cerrado el issue a mano.
5. **Cambia el estado** con `mcp__github__projects_write`: `method: update_project_item`, `owner: Bryanzdruls`, `project_number: 4`, `item_owner: Bryanzdruls`, `item_repo: pasarela-austral-due-diligence`, `issue_number: <N>` y `updated_field: {"name": "Status", "value": "Done"}`.
6. **Informa** cada cambio como `#N: In review → Done, por el PR #M fusionado`. Si no hubo ninguno: `Todo está al día: el Project coincide con los pull requests.`

## Reglas

- **Idempotente**: si la realidad no cambió, una segunda ejecución no modifica nada y lo dice.
- Un ticket que no está en el Project se informa; no se añade sin confirmación.
- Si una llamada falla a medio camino, di qué cambios ya se aplicaron y cuáles no; no dejes transiciones parciales ocultas.
- No edites archivos del repositorio: esta skill solo lee el backlog y mueve tarjetas.
