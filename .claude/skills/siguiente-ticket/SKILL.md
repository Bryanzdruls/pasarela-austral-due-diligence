---
name: siguiente-ticket
description: Toma el siguiente ticket del GitHub Project de Pasarela Austral según el orden del proyecto, lo pasa a In Progress y entrega su contenido como insumo de /speckit-specify. Úsala al empezar un ticket nuevo; no la uses para solo consultar el estado (para eso está sincronizar-tickets).
argument-hint: [número-de-ticket]
allowed-tools: mcp__github__projects_list, mcp__github__projects_write, mcp__github__issue_read, mcp__github__list_pull_requests, mcp__github__pull_request_read, Bash(git status:*), Bash(git branch:*), Bash(git log:*)
---

Vas a arrancar el siguiente ticket del Project nº 4 del repositorio `Bryanzdruls/pasarela-austral-due-diligence`. Toda lectura y escritura del backlog pasa por el servidor MCP de GitHub (toolset `projects`); no uses la interfaz web ni `gh` para mover tarjetas.

Argumento opcional: **$ARGUMENTS** (número de un ticket concreto). Sin argumento, eliges tú según el orden de abajo.

## Si el servidor o el toolset no están disponibles

Si una herramienta `mcp__github__projects_*` no existe o falla por conexión o permisos, **no modifiques nada**: di qué falta (servidor `github` conectado, cabecera `X-MCP-Toolsets: default,projects` en `.mcp.json` y el token por variable de entorno) y detente. No finjas haber movido ninguna tarjeta.

## Pasos

1. **Sincroniza primero.** Invoca la skill `sincronizar-tickets` para que los estados reflejen los pull requests ya fusionados antes de elegir. Si no puedes invocarla, aplica sus mismas reglas.
2. **Lee el Project.** `mcp__github__projects_list` con `method: list_project_items`, `owner: Bryanzdruls`, `project_number: 4` y `field_names: ["Status"]`; pagina hasta el final. Los estados exactos son `Todo`, `In Progress`, `In review` y `Done`.
3. **Si ya hay un ticket en `In Progress`**, dilo y pide confirmación antes de tomar otro. Sin una confirmación expresa de la persona, no muevas nada.
4. **Elige el ticket** entre los que están en `Todo`:
   - Con argumento: ese ticket, solo si está en `Todo`; si está en `In Progress`, `In review` o `Done`, dilo y no muevas nada. Si salta el orden, adviértelo y pide confirmación.
   - Sin argumento: primero los tickets de configuración del entorno de Claude Code (#9 y #10, principio VIII de la constitución) y después el resto por número ascendente.
   - Si el elegido es de funcionalidad (#2 en adelante) y el #9 o el #10 no están en `Done`, advierte que la constitución exige fusionarlos antes y propón el ticket correcto.
   - Si no queda ningún ticket en `Todo`, dilo claramente y no modifiques nada.
5. **Arranca el ticket.** `mcp__github__projects_write` con `method: update_project_item`, `owner: Bryanzdruls`, `project_number: 4`, `item_owner: Bryanzdruls`, `item_repo: pasarela-austral-due-diligence`, `issue_number: <N>` y `updated_field: {"name": "Status", "value": "In Progress"}`.
6. **Trae el contenido.** `mcp__github__issue_read` (`method: get`) del issue: título y cuerpo.
7. **Informa**: qué ticket tomaste y por qué (orden aplicado), el título y el contenido del issue, y que ese contenido es el insumo de `/speckit-specify`. Propón ejecutar `/speckit-specify` con él; no lo ejecutes sin que la persona lo pida. Si fallan llamadas a medio camino, di qué se hizo y qué no.

## Reglas

- Cada cambio de estado se informa: `#N: Todo → In Progress`.
- Un ticket que no aparece en el Project se informa; no se añade sin confirmación.
- No edites archivos del repositorio: esta skill solo lee el backlog y mueve una tarjeta.
