---
name: verificar-ecosistema
description: Comprueba que el ecosistema de Claude Code del proyecto cumple los mínimos del enunciado (memoria, reglas, subagentes, skills, hooks, comando, MCP, credenciales e inventario). Úsala tras tocar `.claude/`, `.mcp.json` o `docs/ECOSISTEMA.md`.
allowed-tools: Bash(python scripts/verify_ecosystem.py*)
argument-hint: [--json]
---

Ejecuta `python scripts/verify_ecosystem.py $ARGUMENTS` desde la raíz del repositorio.

Después resume el resultado:

1. Di si salió con código 0 (todo cumple) o 1 (hay mínimos sin cumplir).
2. Por cada línea `FALLA`, nombra el mínimo y qué pieza falta, tal como lo dice la salida.
3. No corrijas nada por tu cuenta: propón la corrección y espera confirmación.
