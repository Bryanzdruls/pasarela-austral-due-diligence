# Implementation Plan: Ecosistema de Claude Code del equipo

**Branch**: `009-ecosistema-claude-code` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/009-ecosistema-claude-code/spec.md`

## Summary

Configurar Claude Code en el repositorio con piezas pequeñas, bien ubicadas y verificables: memoria de proyecto jerárquica (`CLAUDE.md` raíz + uno por subdirectorio + una importación), reglas con alcance por ruta, cuatro hooks de proyecto (tres que bloquean antes de ejecutar —también sobre órdenes de terminal que escriben archivos— y uno posterior a la edición) escritos en Python estándar y probados sin el modelo, un segundo subagente de revisión (cumplimiento), dos skills, y una verificación automática de los mínimos del enunciado junto con un inventario que justifica cada pieza. Los bloqueos fallan cerrado y explican su motivo.

## Technical Context

**Language/Version**: Python 3.12 (hooks y verificación solo con la biblioteca estándar, para no depender de un entorno virtual al ejecutarse); Markdown con frontmatter para reglas, agentes y skills; JSON para `settings.json`

**Primary Dependencies**: ninguna nueva en tiempo de ejecución; `pytest` (ya presente) para las pruebas; `ruff` (ya presente) como formateador

**Storage**: N/A (archivos de configuración versionados en `.claude/`, `docs/` y `scripts/`)

**Testing**: pytest, con las pruebas junto al código (`.claude/hooks/tests/`, `scripts/tests/`); los hooks se prueban ejecutando los scripts reales como subproceso con JSON por stdin (entrada, código de salida y mensaje), más pruebas unitarias de sus funciones

**Target Platform**: Windows 11 (desarrollo actual), con rutas normalizadas para que también funcione en Linux/macOS

**Project Type**: Configuración de herramienta de desarrollo (Claude Code) y scripts auxiliares

**Performance Goals**: cada hook responde de forma imperceptible (< 1 s en archivos de tamaño normal); `timeout` de 30 s por hook

**Constraints**: sin dependencias externas en los hooks; los hooks de bloqueo deniegan ante un error propio; ningún valor con apariencia de real ni credencial en la configuración; los ejemplos de números sensibles en las pruebas se construyen en tiempo de ejecución

**Scale/Scope**: 4 hooks, 3 reglas, 2 subagentes, 2 skills, 1 comando existente, 3 `CLAUDE.md`, 1 inventario, 1 verificación de mínimos

## Constitution Check

*GATE: pasa antes de la investigación y se reevaluó tras el diseño.*

| Principio | Cumple | Cómo |
|---|---|---|
| I. Reglas de negocio garantizadas | Sí | El revisor de cumplimiento detecta como falta grave cualquier regla que dependa solo del prompt. Los hooks del SDK (reglas 1-3) son el ticket #3 |
| II. Datos exclusivamente ficticios | Sí | Hook de datos reales, hook de secretos y `permissions.deny`; las pruebas construyen los ejemplos sensibles en tiempo de ejecución |
| III. Hooks vs instrucciones | Sí | Lo que invalida la entrega (spec, datos reales, secretos) → hook que bloquea. Convenciones → `CLAUDE.md` y reglas. Documentado en el inventario |
| IV. Spec primero | Sí | spec → plan → tasks → analyze antes de implementar; el hook de spec protege los tickets siguientes |
| V. Agentes con herramientas mínimas | Sí | Revisores de solo lectura (Read, Grep, Glob) |
| VI. Pruebas junto al código | Sí | `.claude/hooks/tests/`, `scripts/tests/`; los hooks se prueban sin modelo |
| VII. Trazabilidad | Sí | Issue #9, rama y PR que lo cierra; `docs/TRAZABILIDAD.md` se actualiza al cerrar |
| VIII. Ecosistema primero | Es esta feature (con el #10) | #9 y #10 se fusionan, en ese orden, antes de cualquier ticket de funcionalidad (constitución v1.1.1) |

Sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/009-ecosistema-claude-code/
├── plan.md
├── research.md          # decisiones y alternativas descartadas (insumo de DECISIONES.md)
├── data-model.md        # inventario de piezas y reglas de detección
├── quickstart.md
├── contracts/
│   └── hooks.md         # entrada, salida y códigos de cada hook; CLI de la verificación
├── checklists/requirements.md
└── tasks.md             # lo genera /speckit-tasks
```

### Source Code (repository root)

```text
CLAUDE.md                           # convenciones de proyecto; importa docs/convenciones.md
CLAUDE.local.md                     # personal; ignorado por git (ya en .gitignore)
docs/
├── convenciones.md                 # importado por CLAUDE.md
└── ECOSISTEMA.md                   # inventario y justificación de cada pieza
mcp_server/CLAUDE.md                # convenciones del servidor de fuentes (carga bajo demanda)
due_diligence/CLAUDE.md             # convenciones del coordinador (carga bajo demanda)
.claude/
├── settings.json                   # hooks de proyecto y permissions.deny (versionado)
├── rules/
│   ├── tests.md                    # paths: tests junto al código
│   ├── datos-ficticios.md          # paths: datos del servidor
│   └── specs.md                    # paths: specs/**
├── agents/
│   ├── code-reviewer.md            # existente
│   └── compliance-reviewer.md      # nuevo: revisión de cumplimiento
├── skills/
│   ├── revisar-cumplimiento/SKILL.md   # context: fork, allowed-tools, argument-hint
│   └── verificar-ecosistema/SKILL.md   # allowed-tools, argument-hint
├── commands/abrir-pr.md            # existente; se actualiza para lanzar ambas revisiones
└── hooks/
    ├── common.py                   # lectura de stdin, bloqueo con mensaje, rutas, feature activa
    ├── spec_gate.py                # PreToolUse Edit|Write|Bash|PowerShell: spec+plan+tasks antes del código
    ├── real_data_guard.py          # PreToolUse Edit|Write|Bash|PowerShell: tarjeta, documento y NIT reales
    ├── secrets_guard.py            # PreToolUse Read|Edit|Write|Bash|PowerShell|Grep|Glob: secretos y .env
    ├── format_after_edit.py        # PostToolUse Edit|Write: ruff format
    └── tests/                      # pruebas de los hooks (subproceso + unitarias)
scripts/
├── verify_ecosystem.py             # verificación de los mínimos del enunciado
└── tests/test_verify_ecosystem.py
.mcp.json                           # ya versionado (commit 66ec80b)
```

**Structure Decision**: Los hooks viven en `.claude/hooks/` junto a `settings.json` porque son configuración del ecosistema y viajan con el repositorio; son scripts de Python estándar (no comandos en línea) para poder probarlos y leerlos. La verificación de mínimos vive en `scripts/` porque es una herramienta del equipo, no un hook. `docs/ECOSISTEMA.md` es el inventario que alimenta `DECISIONES.md` (ticket #11).

## Complexity Tracking

Sin violaciones que justificar.
