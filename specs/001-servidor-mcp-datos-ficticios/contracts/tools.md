# Contrato de herramientas MCP

Servidor: `pasarela-fuentes`, transporte stdio (`python -m mcp_server`).
Toda respuesta es el sobre de éxito o de error descrito en [data-model.md](../data-model.md). Las descripciones de abajo son el texto que ve el modelo y se verifican en pruebas.

## consultar_registro_mercantil
- **Entrada**: `consulta: str` (nombre o identificador del comercio).
- **Éxito (`content`)**: `match_count`, `ambiguous`, `matches: [{id, razon_social, nit, existe, estado, representante_legal:{id,nombre,documento}, categoria, volumen_mensual_estimado, fuentes_registro:[{source,fecha_constitucion}], conflicts:[...]}]`.
- **Descripción**: Busca un comercio en el registro mercantil por nombre o identificador. Úsala primero: es la única forma de identificar al comercio. Si devuelve varias coincidencias (`ambiguous=true`) NO elijas una: pide al analista el identificador. Si no devuelve ninguna, informa que no existe. Si las fuentes del registro reportan fechas distintas, muestra todas con su origen.

## consultar_listas_restrictivas
- **Entrada**: `tipo: "comercio"|"persona"`, `referencia: str` (id del comercio o de la persona).
- **Éxito**: `match: bool`, `entradas:[{nombre_lista, fecha_inclusion}]`.
- **Descripción**: Verifica a un comercio o a una persona (p. ej. el representante legal) contra las listas restrictivas. Úsala solo con un comercio ya identificado de forma unívoca en el registro. Un identificador desconocido se rechaza con `invalid_input` (no se informa como "sin coincidencia"). Una coincidencia aquí es la única que cuenta como coincidencia en listas; una noticia que menciona a alguien NO lo es.

## buscar_noticias
- **Entrada**: `consulta: str` (nombre o id de comercio o persona).
- **Éxito**: `menciones:[{titular, fecha, fuente, resumen}]`.
- **Descripción**: Busca menciones de un comercio o persona en el corpus de noticias. Una mención en noticias NO es una coincidencia en listas restrictivas: reporta la noticia con su fuente y no la trates como hallazgo de listas. Para listas usa consultar_listas_restrictivas.

## consultar_riesgo_categoria
- **Entrada**: `categoria: str`.
- **Éxito**: `categoria`, `riesgo: "alto"|"bajo"|"sin_clasificar"`.
- **Descripción**: Devuelve el nivel de riesgo de una categoría de negocio. Alto riesgo: apuestas, criptoactivos, suplementos dietarios y venta de medicamentos. Si es `sin_clasificar` no asumas un nivel; indícalo en el informe.

## registrar_informe
- **Entrada**: `comercio_id: str`, `recomendacion: str`, `hallazgos: objeto` (por frente, con `fuente`), `cobertura: objeto`, `conflictos: lista`.
- **Éxito**: `informe_id`.
- **Descripción**: Registra el informe de due diligence con su recomendación. Cada afirmación debe llevar su fuente; si hay frentes sin cubrir, decláralos en `cobertura`. Este servidor solo guarda: no valida la recomendación.

## escalar_a_cumplimiento
- **Entrada**: `comercio_id`, `hallazgos` (por frente con fuentes), `cobertura`, `causa`, `accion_recomendada`.
- **Éxito**: `escalamiento_id`. **Error `invalid_input`** con `partial.campos_faltantes` si falta algún campo (texto en blanco cuenta como faltante) y `partial.hallazgos_sin_fuente` si algún frente de `hallazgos` no es un objeto con `fuente`. `registrar_informe` aplica la misma validación.
- **Descripción**: Pasa el caso a un oficial de cumplimiento. El oficial no ve la conversación: el resumen debe bastarse solo (comercio, hallazgos por frente con fuentes, cobertura, causa del escalamiento y acción recomendada).

## Fallas (`PASARELA_FAULTS`)
Con una fuente en `PASARELA_FAULTS` (`registro`, `listas`, `noticias`, `riesgo`), su herramienta devuelve `{ok:false, source:"noticias_ficticias", error_code:"source_unavailable", retryable:true, partial:{}}`. Las demás herramientas no se ven afectadas. Con `noticias:no_reintentable` el error trae `retryable:false`.
