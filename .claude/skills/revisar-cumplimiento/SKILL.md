---
name: revisar-cumplimiento
description: Lanza la revisión independiente de cumplimiento de las reglas de negocio de la pasarela sobre el código y la especificación de un ticket, en un contexto aislado. Úsala antes de abrir un pull request o para saber si una regla depende solo de un prompt.
context: fork
agent: compliance-reviewer
allowed-tools: Read Grep Glob
argument-hint: <ticket>
---

Revisa el cumplimiento de las reglas de negocio de la pasarela para el ticket **$ARGUMENTS** (número del issue de GitHub).

Pasos:

1. Localiza la carpeta `specs/NNN-*` del ticket $ARGUMENTS (por su prefijo numérico) y lee su `spec.md`, `plan.md` y `contracts/`. Lee también `.specify/memory/constitution.md`.
2. Encuentra el código y las pruebas que implementan lo que el ticket promete sobre cada una de las reglas 1 a 5.
3. Aplica el procedimiento de `compliance-reviewer`: califica cada regla como cumplida, parcial o ausente con evidencia (`archivo:línea`), distingue lo que queda fuera del alcance del ticket y reporta como **falta grave** cualquier regla 1, 2 o 3 que el ticket dé por cumplida apoyándose solo en un prompt.
4. Termina con la tabla por regla, la lista de faltas graves y una última línea `VEREDICTO: ...`.

Esta skill se ejecuta en un contexto aislado: no ve la conversación de desarrollo y solo puede leer.
