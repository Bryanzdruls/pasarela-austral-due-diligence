# Data Model: Automatización del GitHub Project y plugin reutilizable

## Ticket y su estado (Project nº 4, campo `Status`)

| Dato | Origen |
|---|---|
| Número, título, contenido | issue de GitHub |
| Estado | opción del campo `Status` del Project: `Todo`, `In Progress`, `In review`, `Done` |
| Pull request asociado | el que tiene una rama que empieza por el número del ticket o `Closes #N` en el cuerpo |
| Fusionado | el pull request asociado tiene fecha de fusión |

### Transiciones permitidas

| Desde | Hacia | Disparador |
|---|---|---|
| `Todo` | `In Progress` | `siguiente-ticket` arranca el ticket |
| `In Progress` | `In review` | `/abrir-pr` abre el pull request |
| `In review` | `Done` | `sincronizar-tickets` detecta el pull request fusionado |
| `In Progress` | `Done` | `sincronizar-tickets` detecta un pull request fusionado que nunca pasó por In review (fusión fuera del flujo) |

Cualquier otra combinación se informa y no se modifica. Un pull request cerrado sin fusionar nunca produce `Done`.

### Orden de los tickets

1. Tickets de configuración del entorno de Claude Code: #9 y #10 (principio VIII de la constitución).
2. El resto, por número ascendente.
3. Se excluyen los tickets ya `In review` o `Done`; si hay uno `In Progress`, se avisa antes de tomar otro.

## Comentario de avance

Tres secciones fijas, en este orden, publicadas en el issue:

| Sección | Contenido | Fuente |
|---|---|---|
| Especificado | qué cubre la especificación y cuántas tareas están hechas | `spec.md`, `tasks.md` |
| Decidido | decisiones relevantes y veredictos de las revisiones | `research.md`, `verification.md`, PR |
| Pendiente | lo que queda abierto o sin verificar | `tasks.md`, `verification.md` |

## Plugin

| Campo | Notas |
|---|---|
| `name` | `pasarela-revision` |
| `version` | semántica, empieza en `0.1.0` |
| `description` | una línea |
| Subagente | `agents/compliance-reviewer.md`, herramientas Read, Grep, Glob |
| Skill | `skills/revisar-cumplimiento/SKILL.md`, con `context: fork`, `allowed-tools` y `argument-hint` |
| Hook | `hooks/hooks.json` → `hooks/real_data_guard.py`, evento `PreToolUse` |

Reglas: ninguna pieza referencia rutas fuera del plugin; ningún archivo contiene credenciales ni datos con apariencia de reales.

## Catálogo (marketplace)

| Campo | Notas |
|---|---|
| `name` | `pasarela-austral` |
| `owner` | nombre del equipo (sin datos personales) |
| `plugins[]` | una entrada con `name`, `source` relativa (`./plugins/pasarela-revision`) y `description` |

## Inventario del ecosistema

Se amplía `docs/ECOSISTEMA.md` con una fila por pieza nueva (`Pieza`, `Tipo`, `Necesidad`, `Ubicación`, `Por qué ahí`, `Alternativa descartada`); la verificación automática falla si hay una pieza en disco sin fila o una fila cuya ruta no existe.
