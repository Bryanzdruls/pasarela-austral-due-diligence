# Contrato: cobertura, errores de frente y reintentos

## Error estructurado del servidor (ya existe, #1)

```json
{"ok": false, "source": "noticias_ficticio", "error_code": "source_unavailable", "retryable": true, "partial": {}}
```

`error_code`: `source_unavailable` o `invalid_input`. `retryable` decide si el reintento tiene sentido. `partial` lleva lo que se alcanzó a obtener (puede ser `{}`).

## Respuesta de un subagente cuando su fuente falla (nueva forma)

```json
{"estado": "error", "frente": "noticias", "reintentable": true,
 "obtenido": {}, "metadatos": {"fuente": "noticias_ficticio", "fecha": "2026-10-16T12:00:00+00:00"}}
```

Con `estado` ausente o distinto de `error`, vale la forma del #2 (`contenido` y `metadatos`). Una respuesta que no cumple ninguna es `no_estructurado` y se trata como no cubierta.

## `cobertura` en `registrar_informe` y `escalar_a_cumplimiento`

```json
{
  "registro": {"estado": "cubierto"},
  "listas": {"estado": "cubierto"},
  "noticias": {"estado": "sin_cubrir", "motivo": "servicio de noticias no disponible tras un reintento"},
  "riesgo": {"estado": "cubierto"}
}
```

- Claves: `registro`, `listas`, `noticias`, `riesgo` (alias aceptados: `registro_mercantil`, `listas_restrictivas`, `riesgo_categoria`).
- `estado`: exactamente `cubierto` o `sin_cubrir`; `motivo` es texto y se pide cuando es `sin_cubrir`.
- Obligatorio: todo frente con un fallo vigente del comercio (o huérfano de la solicitud) debe constar como `sin_cubrir`. Declarar de más se acepta.
- Un informe sin fallos vigentes no está obligado a la forma completa (se conserva el comportamiento del #1: `cobertura` no vacía).

## `Decision` nuevas (`due_diligence/rules.py`)

| Regla (`Decision.rule`) | Cuándo deniega | Herramienta |
|---|---|---|
| `cobertura` | un frente fallido no consta como `sin_cubrir` | `registrar_informe`, `escalar_a_cumplimiento` |
| `cobertura_habilitar` | `habilitar` sin registro identificado o sin listas cubiertas (comercio y, si hay, representante legal) | `registrar_informe` |
| `reintento` | la fuente falló sin ser reintentable, o ya hubo dos fallos seguidos del mismo sujeto en la solicitud | las cuatro herramientas de fuentes |

Orden en `check_informe`: vocabulario → `cobertura` → (solo `habilitar`) identificación → regla 2 → regla 3 → `cobertura_habilitar`. Los motivos dicen qué falta y qué hacer, como los del #3.

## `CaseBook` (altas)

```text
observe(tool, tool_input, response)     # ahora también registra fallos y éxitos de las cuatro fuentes
check_fuente(tool: str, tool_input) -> Decision    # reintentos (D4)
failed_fronts(commerce_id) -> dict[str, FrontFailure]   # por frente, incluye huérfanos
```

`Stop` no cambia. `make_pre_tool_use` pasa a gobernar también las cuatro herramientas de fuentes con `check_fuente`; `make_post_tool_use_failure` observa llamadas que fallan sin sobre (D9).
