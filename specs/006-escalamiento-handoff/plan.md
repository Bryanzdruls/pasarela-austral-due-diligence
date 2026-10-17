# Implementation Plan: Escalamiento con criterio y handoff a cumplimiento

**Branch**: `006-escalamiento-handoff` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-escalamiento-handoff/spec.md`

## Summary

Misma técnica del #3 al #5: el `CaseBook` decide con lo que las fuentes devolvieron y `PreToolUse` aplica la decisión. Sin dependencias nuevas.

- `due_diligence/rules.py` (puro): el `CaseBook` calcula los **motivos de escalamiento** de un comercio (`escalation_grounds`: coincidencia en listas, alto riesgo, contradicción, menciones en noticias) y observa las menciones de noticias. `check_informe` (con la recomendación `escalar_a_cumplimiento`) y `check_escalar` aplican tres reglas nuevas: `escalamiento` (no hay motivo), `handoff_hallazgos` (falta el hallazgo, con fuente, del frente que motiva) y `handoff_causa` (la causa no nombra un motivo). `check_escalar` exige además los `conflictos` declarados, como el informe.
- `mcp_server/tools/informes.py`: `escalar_a_cumplimiento` acepta `conflictos` (cierra la limitación D9 del #5) y su descripción dice el contenido del resumen. El servidor sigue informando, no decidiendo.
- `due_diligence/prompts.py`: el coordinador recibe el criterio (qué es un hallazgo, qué no justifica escalar) y el contenido del resumen. Orienta; lo grave lo hace cumplir el hook.
- `rule_hooks.py` no cambia: ya llama a `check_informe` y `check_escalar`; el hook `Stop` tampoco.

Decisiones y alternativas en [research.md](research.md); entidades en [data-model.md](data-model.md); contrato en [contracts/escalamiento.md](contracts/escalamiento.md).

## Technical Context

**Language/Version**: Python 3.12.

**Primary Dependencies**: `claude-agent-sdk` (ya en el proyecto). Sin dependencias nuevas.

**Storage**: estado en memoria por sesión (`CaseBook`); nada persistente.

**Testing**: `pytest` con `pytest-asyncio`. Reglas puras con la forma real del sobre; hooks con las mismas entradas; `scripts/mutate_rules.py` ampliado; verificación con el modelo real de C1, C2 y C3 en `verification.md`. Ninguna prueba llama al modelo.

**Target Platform**: Windows y Linux.

**Project Type**: biblioteca/aplicación de consola (paquete `due_diligence/`).

**Performance Goals**: sin objetivo propio.

**Constraints**: falla cerrado; sin mezclar motivos entre comercios; decisiones deterministas; datos ficticios.

**Scale/Scope**: cambios en `rules.py`, `prompts.py` y la herramienta de escalamiento del servidor; pruebas nuevas y ajustes justificados en las del #4 y el #5 que escalaban sin motivo.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Cómo se cumple |
|---|---|---|
| I. Reglas de negocio garantizadas | Cumple | El criterio de escalamiento y el contenido del resumen se imponen con el hook |
| II. Datos ficticios | Cumple | Ejemplos con `CO-XX-000N`, `PE-000N` y fuentes `_ficticia(s)` |
| III. Hooks vs instrucciones | Cumple | Lo grave (escalar sin motivo, resumen incompleto) en hooks; la calidad de la redacción por prompt y revisión |
| IV. Spec primero | Cumple | Spec, plan y tareas antes del código |
| V. Agentes con herramientas mínimas | Cumple | No cambia el reparto de herramientas |
| VI. Pruebas junto al código | Cumple | `due_diligence/tests/` |
| VII. Trazabilidad en GitHub | Cumple | Ticket movido por el flujo del #10 |
| VIII. Ecosistema primero | Cumple | #9 y #10 fusionados |

Sin violaciones. Re-evaluación tras el diseño: sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/006-escalamiento-handoff/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/escalamiento.md
├── checklists/requirements.md
└── tasks.md             # lo genera /speckit-tasks
```

### Source Code (repository root)

```text
due_diligence/
├── rules.py              # cambia: motivos, menciones y tres reglas
├── prompts.py            # cambia: criterio y contenido del resumen
└── tests/
    ├── test_rules_escalamiento.py   # nuevo
    ├── test_rule_hooks.py           # ampliado
    ├── test_prompts.py              # ampliado
    └── (test_rules_cobertura, test_rules_procedencia, test_rule_hooks ajustados donde escalaban sin motivo)
mcp_server/tools/informes.py         # cambia: `conflictos` y descripción de escalar_a_cumplimiento
scripts/mutate_rules.py              # cambia: mutaciones del escalamiento
```

**Structure Decision**: se mantiene la separación del #3 al #5. `rules.py` crece; si supera lo razonable, extraer un módulo es un refactor aparte (el estado se comparte con el resto de reglas).

## Complexity Tracking

Sin violaciones que justificar.
