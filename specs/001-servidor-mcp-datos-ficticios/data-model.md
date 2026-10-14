# Data Model: Servidor de fuentes ficticias

Todos los valores son ficticios. Documentos y NIT usan el formato `FICT-000N`.

## Comercio (`data/comercios.json`)

| Campo | Tipo | Notas |
|---|---|---|
| `id` | str | `CO-XX-000N`, único |
| `razon_social` | str | |
| `nit` | str | `FICT-000N` |
| `estado` | str | `activo` \| `cancelado` \| `suspendido` |
| `categoria` | str | referencia a Categoría |
| `volumen_mensual_estimado` | int | pesos |
| `representante_legal_id` | str | referencia a Persona |
| `fuentes_registro` | lista | `[{source, fecha_constitucion}]`; una o más fuentes |

## Persona (`data/personas.json`)

`id` (`PE-000N`), `nombre`, `documento` (`FICT-000N`).

## Entrada de lista restrictiva (`data/listas_restrictivas.json`)

`id`, `tipo` (`persona` \| `comercio`), `referencia` (id de persona o comercio), `nombre_lista`, `fecha_inclusion`.

## Noticia (`data/noticias.json`)

`id`, `titular`, `fecha`, `fuente`, `menciona` (lista de ids de comercio o persona), `resumen`.

## Categoría (`data/categorias.json`)

`nombre`, `riesgo` (`alto` \| `bajo`). Alto: apuestas, criptoactivos, suplementos dietarios, venta de medicamentos. Bajo: p. ej. librería, cafetería, ferretería. Cualquier otra → `sin_clasificar`.

## Informe (runtime, `INF-000N.json`)

`id`, `registrado_en`, `comercio_id`, `recomendacion`, `hallazgos` (por frente, con `fuente`), `cobertura` (frentes cubiertos y no cubiertos), `conflictos`.

## Escalamiento (runtime, `ESC-000N.json`)

`id`, `registrado_en`, `comercio`, `hallazgos` (por frente con fuentes), `cobertura`, `causa`, `accion_recomendada`.

## Respuestas

- Éxito: `{ok:true, content:{...}, metadata:{source, fetched_at}}`
- Error: `{ok:false, source, error_code, retryable, partial}`; `error_code` ∈ `source_unavailable` \| `invalid_input`.

## Conjunto de datos sembrado (cubre los siete casos)

| Id | Razón social | Categoría | Particularidad |
|---|---|---|---|
| CO-TV-0001 | Tienda Verde SAS | suplementos dietarios (alto) | Caso del enunciado, ~$80.000.000 mensuales; noticia adversa |
| CO-LB-0002 | Libros del Faro SAS | librería (bajo) | Sin hallazgos en ninguna fuente |
| CO-DA-0003 | Distribuidora Andina Ficticia SAS | ferretería (bajo) | Representante legal presente en listas restrictivas |
| CO-CA-0004 | Cafetería Aurora SAS | cafetería (bajo) | Nombre casi idéntico a CO-CA-0005 |
| CO-CA-0005 | Cafeteria Aurora S.A.S. | cafetería (bajo) | Nombre casi idéntico a CO-CA-0004 |
| CO-FH-0006 | Ferretería Horizonte SAS | ferretería (bajo) | Dos fuentes con fechas de constitución distintas |
