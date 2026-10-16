# Implementation Plan: Errores estructurados y cobertura parcial

**Branch**: `004-errores-cobertura-parcial` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-errores-cobertura-parcial/spec.md`

## Summary

La cobertura de cada frente se decide con lo que el **servidor devolvió** (el sobre `ok`/error de cada llamada a una fuente, observado con `PostToolUse`), no con lo que el subagente o el coordinador cuenten. Se amplía la maquinaria del #3, sin dependencias nuevas:

- `due_diligence/rules.py` (puro): el `CaseBook` añade el estado de cobertura por frente y sujeto (`observe` lo alimenta desde las cuatro fuentes), `check_fuente` (tope de un reintento y no reintentar lo no reintentable) y, en `check_informe` y `check_escalar`, la exigencia de **declarar sin cubrir** cada frente fallido y la de **tener registro y listas cubiertos para habilitar**.
- `due_diligence/rule_hooks.py`: el `PreToolUse` gobierna también las cuatro herramientas de fuentes (`check_fuente`); el `Stop` no cambia.
- `due_diligence/events.py`: un subagente que reporta un error estructurado produce un `FrontResult` con estado `fallido` (con lo obtenido y si es reintentable), distinto de `no_estructurado`, para el chat del #7.
- `due_diligence/prompts.py`: el formato de respuesta de los subagentes gana la forma de error, y el coordinador recibe la política (reintentar una vez lo reintentable, declarar el resto) y el formato de `cobertura`. Orienta; lo grave lo hace cumplir el hook.

Decisiones y alternativas en [research.md](research.md); entidades en [data-model.md](data-model.md); contrato de `cobertura` en [contracts/cobertura.md](contracts/cobertura.md).

## Technical Context

**Language/Version**: Python 3.12.

**Primary Dependencies**: `claude-agent-sdk` (ya en el proyecto). Sin dependencias nuevas.

**Storage**: estado en memoria por sesión (`CaseBook`); nada persistente.

**Testing**: `pytest` con `pytest-asyncio`. Reglas puras con entradas de la forma real medida en el #3 (`tool_response` como texto con el sobre del servidor); hooks con las mismas entradas; verificación por mutación ampliada en `scripts/mutate_rules.py`; una verificación manual con el modelo real y `PASARELA_FAULTS` en `verification.md`. Ninguna prueba llama al modelo.

**Target Platform**: Windows y Linux.

**Project Type**: biblioteca/aplicación de consola (paquete `due_diligence/`).

**Performance Goals**: sin objetivo propio; los hooks siguen siendo microsegundos.

**Constraints**: falla cerrado; sin mezclar fallas entre comercios ni entre solicitudes; decisiones deterministas; datos ficticios.

**Scale/Scope**: cambios en `rules.py`, `rule_hooks.py`, `events.py`, `prompts.py` y `scripts/mutate_rules.py`; pruebas nuevas y ajustes justificados en las del #3.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Cómo se cumple |
|---|---|---|
| I. Reglas de negocio garantizadas | Cumple | La regla 5 ("nunca un informe parcial como completo") se impone con el hook, no con el prompt |
| II. Datos ficticios | Cumple | Ejemplos con `CO-XX-000N` y `PE-000N` |
| III. Hooks vs instrucciones | Cumple | Lo grave (declarar la cobertura, no habilitar sin registro ni listas, tope de reintentos) en hooks; el prompt solo orienta |
| IV. Spec primero | Cumple | Spec, plan y tareas antes del código |
| V. Agentes con herramientas mínimas | Cumple | No cambia el reparto de herramientas |
| VI. Pruebas junto al código | Cumple | `due_diligence/tests/` |
| VII. Trazabilidad en GitHub | Cumple | Ticket movido por el flujo del #10 |
| VIII. Ecosistema primero | Cumple | #9 y #10 fusionados |

Sin violaciones. Re-evaluación tras el diseño: sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/004-errores-cobertura-parcial/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/cobertura.md
├── checklists/requirements.md
└── tasks.md             # lo genera /speckit-tasks
```

### Source Code (repository root)

```text
due_diligence/
├── rules.py              # cambia: cobertura por frente, check_fuente, declaración y habilitar
├── rule_hooks.py         # cambia: PreToolUse gobierna las cuatro fuentes
├── events.py             # cambia: estado `fallido` de un frente (error estructurado)
├── prompts.py            # cambia: forma de error de los subagentes y política de cobertura
└── tests/
    ├── test_rules.py     # ajustado y ampliado
    ├── test_rule_hooks.py
    ├── test_events.py
    └── test_prompts.py
scripts/mutate_rules.py   # cambia: mutaciones de la cobertura
```

**Structure Decision**: se mantiene la separación del #3: decisiones puras en `rules.py`, capa fina de hooks aparte. No se crea un módulo nuevo: la cobertura comparte el `CaseBook` con las reglas 1 a 3 porque lee el mismo estado de comercios y solicitudes.

## Complexity Tracking

Sin violaciones que justificar.
