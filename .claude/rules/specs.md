---
paths:
  - "specs/**"
---

# Artefactos de Spec Kit

- Cada ticket tiene su carpeta `specs/NNN-nombre/` con `spec.md`, `plan.md`, `tasks.md` y, según el caso, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `checklists/` y `verification.md`.
- Se generan con los comandos de Spec Kit (`/speckit-specify`, `/speckit-plan`, `/speckit-tasks`, `/speckit-analyze`), en español, y se versionan: son evidencia del proceso.
- La spec dice **qué y por qué**, sin tecnología; el plan dice **cómo**. Las decisiones llevan su alternativa descartada: alimentan `DECISIONES.md`.
- Una tarea terminada se marca `[x]` en `tasks.md` en el mismo commit que la completa.
- Los documentos de `specs/` no llevan código de producción ni datos con apariencia de reales.
- Cada ticket se valida contra el enunciado de la prueba al cerrarse, y `docs/TRAZABILIDAD.md` se actualiza.
