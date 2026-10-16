# Data Model: Procedencia, conflictos entre fuentes y ambigüedad

Estado en memoria por conversación, dentro del `CaseBook`. Nada persistente. Sin datos reales.

## Glosario

- **Fuente respondida**: la `metadata.source` de una respuesta correcta del servidor para un frente, o el `source` de una entrada de `fuentes_registro` del registro. Se compara normalizada (minúsculas, sin tildes).
- **Contradicción**: un dato de un comercio con más de un valor distinto entre sus fuentes, señalado por el servidor en `conflicts`.
- **Hallazgo con fuente** y **afirmación con fuente** son lo mismo en este ticket: cada entrada de `hallazgos` de un frente. **Candidato** y **candidato ambiguo** también.
- **Candidato**: un comercio que coincide con un nombre cuando el registro devuelve varios (`ambiguous: true`).

## Fuentes respondidas (`CaseBook.responded`)

`responded: dict[str, dict[str, str]]`: frente → {fuente normalizada → fecha de consulta}. Se alimenta en `observe` con cada respuesta `ok: true` de las cuatro fuentes (`metadata.source`, `metadata.fetched_at`) y, para `registro`, con el `source` de cada entrada de `fuentes_registro` de las coincidencias. Persiste en la conversación; no se borra al cambiar de solicitud ni de comercio (la fuente es la misma para todos).

## Contradicciones del comercio (`CommerceCase.conflictos`)

`conflictos: dict[str, tuple[tuple[str, str], ...]]`: dato → pares (valor, fuente) con más de un valor distinto. Se calcula al identificar al comercio de forma unívoca: para cada dato de `conflicts`, los pares de `fuentes_registro` que lo traen. Se vuelve a calcular en cada identificación (el último registro manda). Persiste entre solicitudes.

## Candidatos (`CaseBook.candidates`)

`candidates: set[str]`: identificadores de los comercios devueltos por un resultado ambiguo del registro. Un identificador sale del conjunto cuando el registro lo identifica de forma unívoca (queda en `commerces`). Persiste entre solicitudes.

## Hallazgo con fuente (entrada de `hallazgos`)

`hallazgos[frente] = {"contenido": ..., "fuente": texto | [texto], "fecha": texto}`. La fecha puede llamarse `fecha`, `fecha_consulta` o `fetched_at`. Ver [contracts/procedencia.md](contracts/procedencia.md).

## Conflicto declarado (entrada de `conflictos`)

`{"dato": texto, "valores": [{"valor": texto, "fuente": texto}, ...]}`. Debe contener todos los pares de la contradicción del comercio.

## Decisiones nuevas (`Decision.rule`)

| Regla | Deniega cuando |
|---|---|
| `ambiguedad` | el `comercio_id` es un candidato sin identificar |
| `procedencia` | un hallazgo de un frente cita una fuente que no respondió, no tiene fuente o no tiene fecha |
| `conflicto` | el comercio tiene una contradicción y el informe no la declara completa |

## Transiciones

```text
registro ambiguo ──▶ candidatos {A, B}
candidato A ──registro por id, unívoco──▶ identificado (sale de candidatos; entra en commerces)
registro unívoco con conflicts ──▶ comercio con contradicciones
informe del comercio ──declara todos los pares──▶ aceptado
```
