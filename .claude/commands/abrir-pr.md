---
description: Revisa la rama con un revisor independiente y uno de cumplimiento, y abre el pull request que cierra su issue
argument-hint: <número-de-issue>
allowed-tools: Bash(git diff:*), Bash(git status:*), Bash(git log:*), Bash(git push:*), Bash(gh pr create:*), Bash(uv run:*), Bash(python -m uv run:*), mcp__github__add_issue_comment, mcp__github__projects_list, mcp__github__projects_write
---

Vas a preparar el pull request del issue #$ARGUMENTS. Sigue estos pasos en orden y detente si alguno falla.

## 1. Verificación local
Ejecuta `uv run pytest -q` y `uv run ruff check .` (si `uv` no está en el PATH, usa `python -m uv run ...`). Si algo falla, corrígelo antes de seguir.

## 2. Revisión independiente del código
Invoca el subagente `code-reviewer` con la tarea de revisar los cambios de esta rama. Pásale explícitamente, porque no hereda la conversación:
- el número de issue #$ARGUMENTS y la carpeta `specs/` de la feature,
- el listado de archivos cambiados y el diff.

Contexto de la rama:

- Archivos cambiados: !`git diff main...HEAD --stat`
- Commits: !`git log main..HEAD --oneline`

Diff completo: !`git diff main...HEAD`

## 3. Revisión de cumplimiento
Invoca el subagente `compliance-reviewer` con el número de ticket $ARGUMENTS y la carpeta `specs/NNN-*` de la feature. Es independiente de la sesión que escribió el código y comprueba las reglas de negocio de la pasarela contra la especificación, el código y las pruebas.

## 4. Decisión
- Si `code-reviewer` devuelve `corregir antes del PR`, o `compliance-reviewer` devuelve `incumplimiento grave`: **no abras el PR**. Muestra los hallazgos BLOQUEANTES, IMPORTANTES y las faltas graves, corrígelos, vuelve al paso 1 y repite las dos revisiones. Para que el ciclo termine: escribe el modelo de amenaza en la petición al revisor (qué se protege y qué queda fuera de alcance), pide una entrada reproducible por hallazgo, corrige solo los BLOQUEANTES y repite como máximo **una** vez; lo demás se declara como pendiente en la descripción del PR.
- Si `compliance-reviewer` devuelve `cumple parcialmente`: muestra qué reglas quedan abiertas y a qué ticket las remite la especificación, y pide al usuario que confirme antes de seguir.
- Si ambos aprueban (`aprobar` y `cumple`): muestra los hallazgos MENORES, si los hay, y sigue.

## 5. Pull request
Antes de crear nada, muestra al usuario el título y la descripción del PR y pide confirmación. Con su confirmación:
1. `git push -u origin HEAD`
2. `gh pr create` con título corto, descripción que resuma lo especificado, lo decidido y lo pendiente, **el veredicto de `code-reviewer` y el de `compliance-reviewer`** (cada uno con sus hallazgos principales) y la línea `Closes #$ARGUMENTS`. Los dos veredictos van siempre en la descripción del PR.
3. Comenta el avance en el issue con `mcp__github__add_issue_comment` (no con `gh`: toda escritura del backlog pasa por el MCP). El comentario tiene tres secciones fijas, en este orden, armadas desde `spec.md`, `tasks.md`, `verification.md` y los veredictos:
   - **Especificado**: qué cubre la especificación y cuántas tareas están hechas.
   - **Decidido**: las decisiones relevantes y los veredictos de las dos revisiones.
   - **Pendiente**: lo que queda abierto o sin verificar.
4. Mueve el ticket a **In review** con `mcp__github__projects_write` (`method: update_project_item`, `project_number: 4`, `updated_field: {"name": "Status", "value": "In review"}`). Si el servidor o el toolset `projects` no están disponibles, **detente y dilo explícitamente**: no declares el ticket movido ni modifiques nada más del Project.
5. Tras la fusión del pull request, el paso a **Done** lo hace `/sincronizar-tickets`.
