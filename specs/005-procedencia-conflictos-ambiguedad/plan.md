# Implementation Plan: Procedencia, conflictos entre fuentes y ambigüedad

**Branch**: `005-procedencia-conflictos-ambiguedad` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-procedencia-conflictos-ambiguedad/spec.md`

## Summary

Igual que en el #3 y el #4, las comprobaciones salen de lo que el **servidor devolvió** (observado con `PostToolUse`), no de lo que el modelo cuente. Se amplía el `CaseBook` sin dependencias nuevas:

- `due_diligence/rules.py` (puro): el `CaseBook` observa (1) la **fuente y la fecha** de cada respuesta correcta por frente, (2) las **contradicciones** que el registro señala (`conflicts` más `fuentes_registro`) y (3) los **candidatos ambiguos** del registro (`ambiguous: true`). `check_informe` y `check_escalar` añaden tres reglas: `ambiguedad` (no se registra ni se escala a nombre de un candidato sin identificar), `procedencia` (cada hallazgo de un frente cita una fuente que respondió y su fecha) y `conflicto` (el informe de un comercio con contradicción declara todos los valores con su origen).
- `due_diligence/rule_hooks.py`: no cambia su estructura; `PreToolUse` ya llama a `check_informe` y `check_escalar`. Se añade a la traza la regla de cada denegación (ya existente).
- `due_diligence/prompts.py`: el coordinador recibe el formato de `hallazgos` (`fuente`, `fecha`), de `conflictos`, la instrucción de pedir el identificador mostrando los candidatos y la de no elegir entre valores contradictorios. Orienta; lo grave lo hace cumplir el hook.
- `mcp_server/tools/informes.py`: solo la descripción de `registrar_informe` (forma de `hallazgos` y `conflictos`). El servidor sigue informando, no decidiendo.

Decisiones y alternativas en [research.md](research.md); entidades en [data-model.md](data-model.md); contrato en [contracts/procedencia.md](contracts/procedencia.md).

## Technical Context

**Language/Version**: Python 3.12.

**Primary Dependencies**: `claude-agent-sdk` (ya en el proyecto). Sin dependencias nuevas.

**Storage**: estado en memoria por sesión (`CaseBook`); nada persistente.

**Testing**: `pytest` con `pytest-asyncio`. Reglas puras con la forma real del sobre del servidor (`tool_response` como texto JSON con `content` y `metadata`); hooks con las mismas entradas; `scripts/mutate_rules.py` ampliado; verificación con el modelo real de los casos C4 (nombres casi idénticos) y C7 (fechas distintas) en `verification.md`. Ninguna prueba llama al modelo.

**Target Platform**: Windows y Linux.

**Project Type**: biblioteca/aplicación de consola (paquete `due_diligence/`).

**Performance Goals**: sin objetivo propio.

**Constraints**: falla cerrado; sin mezclar candidatos, conflictos ni fuentes entre comercios; decisiones deterministas; datos ficticios.

**Scale/Scope**: cambios en `rules.py`, `prompts.py` y la descripción de una herramienta del servidor; pruebas nuevas y ajustes justificados en las de #3 y #4.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Cómo se cumple |
|---|---|---|
| I. Reglas de negocio garantizadas | Cumple | La regla 4 (procedencia y contradicciones) y la identificación sin ambigüedad se imponen con el hook, no con el prompt |
| II. Datos ficticios | Cumple | Ejemplos con `CO-XX-000N`, `PE-000N` y las fuentes ficticias |
| III. Hooks vs instrucciones | Cumple | Lo grave (fuente real, conflicto declarado, candidato sin identificar) en hooks; la presentación al analista y las contradicciones entre frentes, por prompt y declarado |
| IV. Spec primero | Cumple | Spec, plan y tareas antes del código |
| V. Agentes con herramientas mínimas | Cumple | No cambia el reparto de herramientas |
| VI. Pruebas junto al código | Cumple | `due_diligence/tests/` |
| VII. Trazabilidad en GitHub | Cumple | Ticket movido por el flujo del #10 |
| VIII. Ecosistema primero | Cumple | #9 y #10 fusionados |

Sin violaciones. Re-evaluación tras el diseño: sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/005-procedencia-conflictos-ambiguedad/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/procedencia.md
├── checklists/requirements.md
└── tasks.md             # lo genera /speckit-tasks
```

### Source Code (repository root)

```text
due_diligence/
├── rules.py              # cambia: fuentes respondidas, contradicciones, candidatos y tres reglas
├── prompts.py            # cambia: hallazgos con fuente y fecha, conflictos, candidatos
└── tests/
    ├── test_rules_procedencia.py   # nuevo
    ├── test_rule_hooks.py          # ampliado
    ├── test_prompts.py             # ampliado
    └── (test_rules, test_rules_cobertura, test_rule_hooks ajustados donde hace falta)
mcp_server/tools/informes.py        # cambia: solo la descripción de registrar_informe
scripts/mutate_rules.py             # cambia: mutaciones de procedencia, conflicto y ambigüedad
```

**Structure Decision**: se mantiene la separación del #3 y el #4 (decisiones puras en `rules.py`, capa fina de hooks). `rules.py` crece, pero la lógica comparte el mismo estado de comercios y solicitudes; separar un módulo obligaría a pasarse el `CaseBook` en cada llamada. Si supera lo razonable, la extracción a `rules_procedencia.py` es un refactor aparte.

## Complexity Tracking

Sin violaciones que justificar.
