# Data Model: Coordinador y subagentes

Todos los datos de ejemplo son ficticios.

## Solicitud
Texto del analista. El coordinador extrae: `comercio` (nombre o identificador), `categoria_declarada` (opcional), `volumen_estimado` (opcional). Sin comercio identificable no se delega (FR-010).

## Frente (`FrontName`)
Enumeración: `registro_mercantil` · `listas_restrictivas` · `noticias` · `riesgo_categoria`.

| Frente | Herramienta MCP permitida (única) | Depende de |
|---|---|---|
| registro_mercantil | `mcp__pasarela-fuentes__consultar_registro_mercantil` | — |
| noticias | `mcp__pasarela-fuentes__buscar_noticias` | — |
| riesgo_categoria | `mcp__pasarela-fuentes__consultar_riesgo_categoria` | — |
| listas_restrictivas | `mcp__pasarela-fuentes__consultar_listas_restrictivas` | registro_mercantil (comercio e id del representante) |

El coordinador no tiene herramientas de fuentes propias; solo `Agent`. (Las dos herramientas de salida, `registrar_informe` y `escalar_a_cumplimiento`, se asignan al coordinador en los tickets #5 y #6.)

## Encargo de frente
Texto que el coordinador pasa al subagente: el frente, los datos mínimos que necesita (identificador del comercio, nombre, representante legal solo para listas, categoría solo para riesgo) y la forma de respuesta. No incluye la conversación.

## FrontResult
| Campo | Notas |
|---|---|
| `frente` | `FrontName` |
| `contenido` | lo hallado (objeto JSON) |
| `metadatos` | `{fuente, fecha}`; obligatorios |
| `estado` | `completo` \| `no_estructurado` \| `no_completado` |

`no_estructurado`: la respuesta del subagente no se pudo parsear a este formato. `no_completado`: no hubo resultado (se desarrolla en #4).

## Eventos de dominio
- `SubagentStarted(frente, tool_use_id)`
- `SubagentFinished(frente, result: FrontResult | None)`
- `CoordinatorText(text)` — texto del coordinador (no decide el ciclo)
- `RunFinished(subtype, stop_reason, terminal_reason)` — último evento; proviene de `ResultMessage`

## Informe de due diligence (salida del coordinador)
Texto con una sección por frente, una sección de "Datos aportados por el analista" (categoría declarada y volumen, FR-011) y una recomendación. El registro estructurado del informe y su procedencia completa son los tickets #5 y #6.

## Transiciones
`Solicitud → (comercio identificable?) → [registro ‖ noticias ‖ riesgo] → listas (si registro identificó un único comercio) → informe`
