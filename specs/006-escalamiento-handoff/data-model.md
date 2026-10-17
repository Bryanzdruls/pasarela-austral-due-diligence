# Data Model: Escalamiento con criterio y handoff a cumplimiento

Estado en memoria por conversación, dentro del `CaseBook`. Nada persistente. Sin datos reales.

## Motivo de escalamiento

Uno de `listas`, `riesgo`, `conflicto`, `noticias`. Se calcula por comercio con `CaseBook.escalation_grounds(comercio_id)` → `dict[str, Ground]`:

| Motivo | Cuándo existe | Frente que lo respalda en `hallazgos` | Palabras clave de la `causa` |
|---|---|---|---|
| `listas` | alguna consulta de listas del comercio o de su representante con coincidencia | `listas` | `lista` |
| `riesgo` | el comercio es de alto riesgo (registro, catálogo o solicitud, #3); o, sin identificar, la solicitud declara alto riesgo | `riesgo` o `registro` (ninguno si solo lo declaró el analista) | `riesgo` |
| `conflicto` | el registro señaló una contradicción del comercio (#5) | los `conflictos` completos | `contradic`, `conflict`, `discrep` |
| `noticias` | una respuesta de noticias con menciones | `noticias` | `noticia`, `mencion` |

`Ground`: `(clave, descripción, frentes que lo respaldan, palabras clave)`.

## Menciones (`CommerceCase.menciones`)

`bool`. Se marca cuando una respuesta correcta de noticias trae `content.menciones` no vacío: a los comercios de la solicitud en curso (o el único conocido); si aún no hay comercio identificado, queda como `CaseBook._orphan_mentions` y lo adopta el primero que se identifique (como las fallas huérfanas del #4). Persiste entre solicitudes.

## Resumen al oficial (entrada de `escalar_a_cumplimiento`)

`{comercio_id, hallazgos, cobertura, conflictos, causa, accion_recomendada}`. Ver [contracts/escalamiento.md](contracts/escalamiento.md).

## Decisiones nuevas (`Decision.rule`)

| Regla | Deniega cuando |
|---|---|
| `escalamiento` | el comercio no tiene ningún motivo y se escala o se recomienda escalar |
| `handoff_hallazgos` | falta el hallazgo, en `hallazgos`, de un frente que respalda un motivo |
| `handoff_causa` | la `causa` no contiene una palabra clave de un motivo existente |

## Transiciones

```text
lista con coincidencia ──▶ motivo `listas`           ──┐
categoría de alto riesgo ──▶ motivo `riesgo`          ├──▶ escalar permitido
contradicción del registro ──▶ motivo `conflicto`     │    (si el resumen está completo)
menciones en noticias ──▶ motivo `noticias`          ──┘
sin motivos (riesgo bajo sin hallazgos) ──▶ escalar denegado; habilitar o no habilitar
```
