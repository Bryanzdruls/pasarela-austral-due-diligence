# Implementation Plan: Automatización del GitHub Project y plugin reutilizable

**Branch**: `010-automatizacion-project-plugin` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/010-automatizacion-project-plugin/spec.md`

## Summary

Dos entregas de configuración del entorno de Claude Code, sin código de producción de la pasarela:

1. **Flujo de tickets** (necesidad 10): dos skills de proyecto, `siguiente-ticket` y `sincronizar-tickets`, que leen y escriben el Project solo por el servidor MCP oficial de GitHub (toolset `projects`), y una ampliación de `/abrir-pr` que pasa el ticket a In review y publica el comentario de avance de tres partes. La transición a Done se registra al sincronizar (supuesto del spec).
2. **Plugin reutilizable** (necesidad 11, mínimo E8): `plugins/pasarela-revision/` con un subagente de cumplimiento genérico, una skill de revisión y un hook autónomo de datos reales, instalable desde un catálogo `.claude-plugin/marketplace.json` publicado en este repositorio.

Se amplía `scripts/verify_ecosystem.py` (biblioteca estándar) para comprobar las piezas nuevas y se actualizan `docs/ECOSISTEMA.md` y `docs/TRAZABILIDAD.md`. Detalle de decisiones en [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12 solo para el verificador, el hook del plugin y sus pruebas (biblioteca estándar); el resto es Markdown con frontmatter y JSON.

**Primary Dependencies**: ninguna nueva. Servidor MCP oficial de GitHub con `X-MCP-Toolsets: default,projects` (ya en `.mcp.json`) y la CLI `claude plugin` para validar e instalar.

**Storage**: N/A (el estado vive en GitHub; el plugin y el catálogo son archivos versionados).

**Testing**: `pytest` con las pruebas junto al código: `scripts/tests/` para el verificador y `plugins/pasarela-revision/tests/` para el hook del plugin; validación manual documentada con `claude plugin validate` y una instalación en un repositorio temporal.

**Target Platform**: Claude Code 2.1.x en Windows (PowerShell y Git Bash) y en Linux/macOS.

**Project Type**: configuración de entorno de desarrollo (skills, comando, plugin, catálogo, verificador).

**Performance Goals**: instalar el plugin y tener sus tres piezas funcionando en menos de 5 minutos (SC-004).

**Constraints**: ninguna credencial ni dato con apariencia de real en plugin, catálogo o skills; el flujo nunca modifica el Project si el servidor o el toolset no están disponibles; el hook del plugin no importa nada del repositorio.

**Scale/Scope**: 1 plugin, 1 catálogo, 2 skills nuevas, 1 comando ampliado, 3 comprobaciones nuevas del verificador.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Cómo se cumple |
|---|---|---|
| I. Reglas de negocio garantizadas | N/A | No toca la lógica de la pasarela |
| II. Datos ficticios | Cumple | El hook del plugin los protege; ejemplos y pruebas con valores generados en tiempo de ejecución; SC-007 |
| III. Hooks vs instrucciones | Cumple | El hook del plugin bloquea (daño: dato real); el flujo de tickets son skills porque un hook no puede llamar al MCP; se justifica en `docs/ECOSISTEMA.md` |
| IV. Spec primero | Cumple | Este ticket tiene spec, plan y tareas antes de tocar `.claude/` o `plugins/` |
| V. Agentes con herramientas mínimas | Cumple | El subagente del plugin es de solo lectura (Read, Grep, Glob) |
| VI. Pruebas junto al código | Cumple | Pruebas del verificador en `scripts/tests/`, del hook del plugin en `plugins/pasarela-revision/tests/` |
| VII. Trazabilidad en GitHub | Cumple | Es el ticket que la automatiza; se usa a sí mismo (ya está In Progress por el MCP) |
| VIII. Ecosistema primero | Cumple | Cierra el ecosistema (plugin y automatización) antes de cualquier ticket de funcionalidad; ningún ticket de funcionalidad se fusiona antes que este |

Sin violaciones. Re-evaluación tras el diseño: sigue sin violaciones (ver Complexity Tracking).

## Project Structure

### Documentation (this feature)

```text
specs/010-automatizacion-project-plugin/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── flujo-tickets.md
│   └── plugin.md
├── checklists/requirements.md
└── tasks.md             # lo genera /speckit-tasks
```

### Source Code (repository root)

```text
.claude/
├── skills/
│   ├── siguiente-ticket/SKILL.md      # nueva: elige y arranca el siguiente ticket
│   └── sincronizar-tickets/SKILL.md   # nueva: reconcilia estados Project <-> PR
└── commands/abrir-pr.md               # ampliado: In review + comentario de avance

.claude-plugin/
└── marketplace.json                   # catálogo del repositorio

plugins/pasarela-revision/
├── .claude-plugin/plugin.json
├── agents/compliance-reviewer.md      # genérico, solo lectura
├── skills/revisar-cumplimiento/SKILL.md
├── hooks/
│   ├── hooks.json                     # PreToolUse -> real_data_guard.py
│   └── real_data_guard.py             # autocontenido (sin importar el repo)
├── tests/test_plugin_real_data_guard.py, test_plugin_layout.py
└── README.md                          # instalación, uso y límites

scripts/
├── verify_ecosystem.py                # ampliado: plugin, catálogo, automatización
└── tests/test_verify_ecosystem.py     # ampliado

docs/
├── ECOSISTEMA.md                      # filas y límites de las piezas nuevas
└── TRAZABILIDAD.md                    # N10, N11, E8, P4, P5, P8
```

**Structure Decision**: el plugin vive en `plugins/pasarela-revision/` y el catálogo en `.claude-plugin/marketplace.json` en la raíz, de modo que quien añada este repositorio como marketplace obtiene el plugin por ruta relativa, sin un repositorio aparte. Las skills del flujo viven en `.claude/skills/` (proyecto) y no en el plugin: dependen del Project nº 4 de este repositorio y no son reutilizables por otro equipo.

## Complexity Tracking

Sin violaciones que justificar. La única duplicación asumida es el hook de datos reales (existe en `.claude/hooks/` y en el plugin): el del plugin debe ser autocontenido para instalarse en otro repositorio. Se mitiga con una prueba de paridad que compara ambas implementaciones sobre las mismas entradas (D8 en [research.md](research.md)).
