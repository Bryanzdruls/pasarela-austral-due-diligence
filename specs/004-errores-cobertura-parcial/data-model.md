# Data Model: Errores estructurados y cobertura parcial

Estado en memoria por conversación, dentro del `CaseBook` del #3. Nada persistente. Sin datos reales.

## Glosario

- **Fallo** (o frente caído): la última llamada a un sujeto devolvió error o algo ilegible. **Sin cubrir** es cómo se declara en el informe. **Cubierto**: el sujeto respondió con éxito. `FrontStatus.FALLIDO` (en `events.py`) es el estado de un resultado de subagente que reporta un fallo; no es el estado de cobertura.
- **Sujeto**: lo que identifica una consulta, normalizado (minúsculas y sin tildes). `listas`: tipo + referencia; `riesgo`: la categoría; `registro` y `noticias`: el propio frente (`*`), porque reescribir la consulta no la convierte en otra fuente.

## Frente

Uno de `registro`, `listas`, `noticias`, `riesgo` (nombres del servidor). Cada herramienta de fuente pertenece a uno:

| Herramienta | Frente | Sujeto |
|---|---|---|
| `consultar_registro_mercantil` | `registro` | el frente (`*`) |
| `consultar_listas_restrictivas` | `listas` | `tipo` + `referencia` |
| `buscar_noticias` | `noticias` | el frente (`*`) |
| `consultar_riesgo_categoria` | `riesgo` | `categoria` |

Alias en `cobertura` y en los subagentes: `registro_mercantil`, `listas_restrictivas`, `riesgo_categoria` (D10).

## Fallo (`FrontFailure`)

La última llamada fallida de un sujeto. Campos: `frente`, `sujeto`, `error_code` (`source_unavailable`, `invalid_input` o `ilegible`), `retryable` (bool; `false` si no se pudo interpretar), `obtenido` (el `partial` del error).

Reglas: un éxito del mismo `frente` + `sujeto` elimina el fallo (D2). Un `invalid_input` también es fallo: la fuente no dio resultado.

## Cobertura del comercio

Dentro de `CommerceCase` (por comercio identificado): `fallos: dict[(frente, sujeto), FrontFailure]`. Persiste entre solicitudes (D3). El frente está **sin cubrir** si tiene algún fallo.

Derivado de lo que ya guarda el caso: `listas` cubierto = existe resultado correcto para `comercio` y, si hay `representante_id`, para `persona` (D7); `registro` cubierto = el comercio fue identificado de forma unívoca.

## Fallos huérfanos de la solicitud

`CaseBook.orphan_failures`: fallos que no se pueden asociar a un comercio (p. ej. registro caído antes de identificar nada). Se limpian en `start_request`. Cuentan para cualquier informe de esa solicitud. Noticias y riesgo corren en paralelo con el registro, así que suelen fallar antes de que el comercio esté identificado: cuando el registro lo identifica, el comercio **adopta** los huérfanos de noticias y riesgo de la solicitud y pasan a persistir con él.

## Intentos de la solicitud

`CaseBook.attempts: dict[(frente, sujeto), (fallos_seguidos, ultimo_reintentable)]`. Se limpia en `start_request` y el sujeto se borra al primer éxito. Alimenta `check_fuente` (D4): se deniega si el último intento falló sin ser reintentable o si ya hay dos fallos seguidos.

## Declaración de cobertura (entrada de `registrar_informe` / `escalar_a_cumplimiento`)

`cobertura = {frente: {"estado": "cubierto" | "sin_cubrir", "motivo": texto}}`. Un frente caído debe constar con `sin_cubrir`. Ver [contracts/cobertura.md](contracts/cobertura.md).

## Resultado de frente (`FrontResult`, en `events.py`)

Gana el estado `fallido` (además de `completo`, `no_estructurado`, `no_completado`): contenido = lo obtenido y, en `metadatos`, `fuente` y `fecha`; el motivo y `reintentable` van en el contenido bajo `error`.

## Transiciones de un sujeto

```text
sin llamada ──éxito──▶ cubierto
sin llamada ──falla──▶ caído (intento 1)
caído ──éxito──▶ cubierto                 (reintento recuperado)
caído reintentable ──falla──▶ caído (intento 2) ──llamada──▶ denegada (declarar)
caído no reintentable ──llamada──▶ denegada (declarar)
solicitud nueva ──▶ intentos a cero (el fallo del comercio persiste)
```
