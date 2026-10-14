---
description: Revisa la rama con un revisor independiente y abre el pull request que cierra su issue
argument-hint: <número-de-issue>
allowed-tools: Bash(git diff:*), Bash(git status:*), Bash(git log:*), Bash(git push:*), Bash(gh pr create:*), Bash(gh issue comment:*), Bash(uv run:*), Bash(python -m uv run:*)
---

Vas a preparar el pull request del issue #$ARGUMENTS. Sigue estos pasos en orden y detente si alguno falla.

## 1. Verificación local
Ejecuta `uv run pytest -q` y `uv run ruff check .` (si `uv` no está en el PATH, usa `python -m uv run ...`). Si algo falla, corrígelo antes de seguir.

## 2. Revisión independiente
Invoca el subagente `code-reviewer` con la tarea de revisar los cambios de esta rama. Pásale explícitamente, porque no hereda la conversación:
- el número de issue #$ARGUMENTS y la carpeta `specs/` de la feature,
- el listado de archivos cambiados y el diff.

Contexto de la rama:

- Archivos cambiados: !`git diff main...HEAD --stat`
- Commits: !`git log main..HEAD --oneline`

Diff completo: !`git diff main...HEAD`

## 3. Decisión
- Si el veredicto es `corregir antes del PR`, muestra los hallazgos BLOQUEANTES e IMPORTANTES, corrígelos, vuelve al paso 1 y repite la revisión.
- Si el veredicto es `aprobar`, muestra los hallazgos MENORES (si los hay) y sigue.

## 4. Pull request
Antes de crear nada, muestra al usuario el título y la descripción del PR y pide confirmación. Con su confirmación:
1. `git push -u origin HEAD`
2. `gh pr create` con título corto, descripción que resuma lo especificado, lo decidido y lo pendiente, el resultado de la revisión independiente, y la línea `Closes #$ARGUMENTS`.
3. Comenta el avance en el issue con `gh issue comment`.
4. Si el MCP de GitHub tiene el toolset de projects, mueve el ticket a **In review**; si no, dilo explícitamente.
