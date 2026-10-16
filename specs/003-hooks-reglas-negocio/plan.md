# Implementation Plan: Hooks del SDK para las reglas de negocio 1 a 3

**Branch**: `003-hooks-reglas-negocio` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-hooks-reglas-negocio/spec.md`

## Summary

Las tres reglas se imponen con hooks del Agent SDK que deciden con lo que las fuentes **devolvieron**, no con lo que el modelo diga:

- Un módulo de reglas puro, `due_diligence/rules.py`, sin dependencias del SDK: un `CaseBook` (estado por conversación) que observa los resultados de las herramientas y decide `check_listas` (regla 1), `check_informe` (reglas 2 y 3 y vocabulario cerrado) y `check_escalar`.
- Hooks en `due_diligence/rule_hooks.py`: `PreToolUse` (aplica las decisiones), `PostToolUse` (observa registro, listas, riesgo y escalamientos), `UserPromptSubmit` (lee la categoría declarada por el analista) y `Stop` (exige escalar antes de cerrar, una sola vez; D12). Se componen con el guard de aislamiento del #2.
- El coordinador pasa a poder usar `registrar_informe` y `escalar_a_cumplimiento`, solo bajo esas reglas.
- `DueDiligenceSession` crea un `CaseBook` por conversación y lo comparte con los hooks.

Decisiones y alternativas en [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12.

**Primary Dependencies**: `claude-agent-sdk` (ya en el proyecto; hooks `PreToolUse`, `PostToolUse` y `UserPromptSubmit`). Sin dependencias nuevas.

**Storage**: estado en memoria por sesión (`CaseBook`); nada persistente.

**Testing**: `pytest` con `pytest-asyncio`. Las pruebas de reglas son puras; las de hooks invocan las funciones con entradas con la forma real medida en una ejecución con modelo (`tool_response` como texto JSON). Sin modelo en las pruebas; una comprobación con modelo real queda documentada en `verification.md`.

**Target Platform**: Windows y Linux, igual que el resto.

**Project Type**: biblioteca/aplicación de consola (paquete `due_diligence/`).

**Performance Goals**: los hooks añaden microsegundos (parseo de un JSON pequeño); no hay objetivo propio.

**Constraints**: falla cerrado; sin mezclar datos entre comercios; decisiones deterministas; sin credenciales; datos solo ficticios.

**Scale/Scope**: 1 módulo de reglas, 1 módulo de hooks, cambios en `guards.py`, `options.py`, `coordinator.py`, `prompts.py`, y pruebas nuevas.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Cómo se cumple |
|---|---|---|
| I. Reglas de negocio garantizadas | Cumple | Es el ticket que las impone con hooks del SDK; cada regla con su prueba y su mutación |
| II. Datos ficticios | Cumple | Ejemplos con `CO-XX-000N` y `PE-000N`; sin valores reales |
| III. Hooks vs instrucciones | Cumple | Lo grave va en hooks; el prompt solo orienta y declara el vocabulario |
| IV. Spec primero | Cumple | Spec, plan y tareas antes del código |
| V. Agentes con herramientas mínimas | Cumple | Los subagentes no cambian; el coordinador gana solo las dos herramientas de salida, bajo las reglas |
| VI. Pruebas junto al código | Cumple | `due_diligence/tests/` |
| VII. Trazabilidad en GitHub | Cumple | Ticket movido por el flujo del #10 |
| VIII. Ecosistema primero | Cumple | #9 y #10 fusionados |

Sin violaciones. Re-evaluación tras el diseño: sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/003-hooks-reglas-negocio/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/rules.md
├── checklists/requirements.md
└── tasks.md             # lo genera /speckit-tasks
```

### Source Code (repository root)

```text
due_diligence/
├── rules.py              # nuevo: CaseBook, Decision, vocabulario, categorías de alto riesgo
├── rule_hooks.py         # nuevo: hooks PreToolUse/PostToolUse/UserPromptSubmit
├── guards.py             # cambia: el coordinador puede usar registrar_informe y escalar
├── options.py            # cambia: build_options(book) registra los hooks y permite las herramientas
├── coordinator.py        # cambia: un CaseBook por conversación
├── prompts.py            # cambia: vocabulario de recomendaciones y herramientas de salida
└── tests/
    ├── test_rules.py         # nuevo: reglas puras
    ├── test_rule_hooks.py    # nuevo: hooks con entradas reales
    └── (test_guards, test_options, test_prompts, test_coordinator ajustados)
```

**Structure Decision**: la lógica de decisión es pura y vive aparte de los hooks para probarla sin el SDK; los hooks son una capa fina que parsea la entrada del SDK, consulta el `CaseBook` y devuelve la forma de respuesta del SDK.

## Complexity Tracking

Sin violaciones que justificar.
