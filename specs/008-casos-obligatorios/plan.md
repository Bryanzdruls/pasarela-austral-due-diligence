# Implementation Plan: Casos de prueba obligatorios automatizados

**Branch**: `008-casos-obligatorios` | **Date**: 2026-10-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/008-casos-obligatorios/spec.md`

## Summary

Se añaden pruebas, un comando y un documento; el sistema no cambia (FR-010).

- **Arnés de escenario** (`due_diligence/tests/escenario.py`): ejecuta un guion de llamadas a herramientas como lo haría el SDK, pero con las piezas reales: los hooks se toman de `build_options(book)` (el cableado de producción: aislamiento por rol, reglas, observación, parada), las herramientas son las funciones reales del servidor (`mcp_server/tools/*`) con sus datos ficticios y la inyección de fallas, y los informes y escalamientos se guardan en un directorio temporal. Cada llamada devuelve si se permitió, la regla y el motivo del rechazo, y la respuesta del servidor. La única parte simulada es qué herramienta llama el modelo.
- **Siete casos** (`due_diligence/tests/test_casos_obligatorios.py`): una prueba por caso con el nombre del caso, más las variantes que pide el enunciado (el caso 5 en sus dos formas, el caso 6 con falla reintentable y no reintentable).
- **Ejecución con el modelo real** (`due_diligence/casos_reales.py` + `scripts/run_casos.py`): corre los mismos siete casos con el coordinador real y decide cada resultado por las llamadas, los registros y las denegaciones observadas con los mismos hooks (no por el texto). Sin clave termina con un mensaje claro; con `--caso N` corre uno solo.
- **Documento** (`docs/CASOS.md`): mensaje, resultado esperado, prueba y cómo repetir cada caso.
- **Mutaciones de sistema** (`scripts/mutate_rules.py`): desconectar el hook de reglas o el de parada, o ignorar la inyección de fallas, debe hacer fallar los casos.

Decisiones y alternativas en [research.md](research.md); el contrato del arnés y del comando en [contracts/casos.md](contracts/casos.md).

## Technical Context

**Language/Version**: Python 3.12.

**Primary Dependencies**: `pytest`, `pytest-asyncio` (ya en el proyecto) y `claude-agent-sdk` (solo la ejecución real). Sin dependencias nuevas.

**Storage**: directorio temporal por prueba (`PASARELA_RUNTIME_DIR`); nada persistente.

**Testing**: `pytest`. Ninguna prueba llama al modelo ni exige clave. La ejecución real es un comando aparte.

**Target Platform**: Windows y Linux.

**Project Type**: biblioteca/aplicación de consola.

**Performance Goals**: los siete casos en menos de un minuto.

**Constraints**: sin cambiar el comportamiento del sistema; datos solo ficticios; sin literales con forma de tarjeta, NIT o documento.

**Scale/Scope**: 3 archivos nuevos de prueba/arnés, 2 de ejecución real, 1 documento y mutaciones.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Cómo se cumple |
|---|---|---|
| I. Reglas de negocio garantizadas | Cumple | Los casos prueban que las reglas las imponen los hooks, de extremo a extremo |
| II. Datos ficticios | Cumple | Solo los datos de `mcp_server/data/` |
| III. Hooks vs instrucciones | Cumple | Los casos ejercen los hooks de producción, no el prompt |
| IV. Spec primero | Cumple | Spec, plan y tareas antes del código |
| V. Agentes con herramientas mínimas | Cumple | El arnés pasa por el aislamiento por rol de producción |
| VI. Pruebas junto al código | Cumple | `due_diligence/tests/`; ninguna llama al modelo |
| VII. Trazabilidad en GitHub | Cumple | Ticket movido por el flujo del #10 |
| VIII. Ecosistema primero | Cumple | #9 y #10 fusionados |

Sin violaciones. Re-evaluación tras el diseño: sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/008-casos-obligatorios/
├── plan.md
├── research.md
├── quickstart.md
├── contracts/casos.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
due_diligence/
├── casos_reales.py              # nuevo: los 7 casos con el modelo real y sus comprobaciones
└── tests/
    ├── escenario.py             # nuevo: arnés (hooks de producción + herramientas reales)
    ├── test_escenario.py        # nuevo: el arnés se comporta como el SDK
    ├── test_casos_obligatorios.py   # nuevo: los 7 casos sin modelo
    └── test_casos_reales.py     # nuevo: comprobaciones de la ejecución real con datos grabados
scripts/run_casos.py             # nuevo: comando de la ejecución real
docs/CASOS.md                    # nuevo
scripts/mutate_rules.py          # cambia: mutaciones de sistema
```

**Structure Decision**: el arnés vive en `tests/` (es código de prueba); la ejecución real vive en el paquete porque es una función de la aplicación que un evaluador puede invocar, y su lógica de comprobación se prueba con llamadas grabadas, sin modelo.

## Complexity Tracking

Sin violaciones que justificar.
