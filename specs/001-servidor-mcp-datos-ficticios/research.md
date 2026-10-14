# Research: Servidor de fuentes ficticias

No quedaron `NEEDS CLARIFICATION` en el contexto técnico; este documento deja constancia de las decisiones y las alternativas descartadas.

## D1. SDK y transporte
- **Decisión**: SDK oficial `mcp` con `FastMCP`, transporte stdio.
- **Razón**: Es lo que el Agent SDK conecta de forma nativa como servidor MCP; las descripciones de las herramientas salen del docstring y el esquema de entrada de las anotaciones de tipo.
- **Alternativas**: servidor HTTP/SSE (más piezas, sin beneficio local); herramientas SDK en proceso (`create_sdk_mcp_server`) — válidas, pero el enunciado pide un servidor MCP propio y separado del coordinador.

## D2. Sobre de respuesta y errores
- **Decisión**: éxito `{ok:true, content, metadata:{source, fetched_at}}`; fallo `{ok:false, source, error_code, retryable, partial}`. Las fallas de fuente se devuelven como resultado de la herramienta (no como excepción del protocolo) para que el modelo las lea y decida.
- **Razón**: Cumple el comportamiento 7 del enunciado y la regla 5; separa contenido de metadatos (comportamiento 2).
- **Alternativas**: lanzar excepciones (el cliente solo ve un texto de error, sin `retryable` ni `partial`).

## D3. Coincidencias del registro
- **Decisión**: la búsqueda normaliza (minúsculas, sin tildes, sin puntuación, sufijo societario SAS/S.A.S. ignorado). Un comercio coincide si la consulta es exactamente su identificador, o si la consulta normalizada está contenida en su razón social normalizada (por tanto "Cafetería Aurora" y "Cafeteria Aurora S.A.S." coinciden entre sí). No se usa distancia de edición. La respuesta incluye `match_count` y `ambiguous: true` cuando hay más de una. El servidor nunca elige.
- **Razón**: FR-003 y el caso de nombres casi idénticos.
- **Alternativas**: distancia de edición con umbral (más difícil de explicar y de reproducir en pruebas); coincidencia exacta (no reproduce el caso).

## D4. Dos fuentes con fechas distintas
- **Decisión**: cada comercio lleva `fuentes_registro: [{source, fecha_constitucion}]`. La herramienta devuelve la lista completa por coincidencia y marca `conflicts: ["fecha_constitucion"]` si difieren.
- **Razón**: Regla 4: se muestran ambas con origen, sin elegir.

## D5. Inyección de fallas
- **Decisión**: `PASARELA_FAULTS` con una lista separada por comas de fuentes (`noticias`, `registro`, `listas`, `riesgo`). Se lee en cada llamada, no solo al arrancar, para poder activarla por proceso de prueba. Valor `noticias:no_reintentable` fija `retryable=false`; por defecto `retryable=true`.
- **Razón**: Permite el caso "falla de noticias" sin tocar código ni datos.
- **Alternativas**: herramienta MCP de control de fallas (ampliaría la superficie de seis herramientas que pide el enunciado).

## D6. Persistencia de informes y escalamientos
- **Decisión**: un JSON por registro en `PASARELA_RUNTIME_DIR` (por defecto `data/runtime/`), id `INF-000N` / `ESC-000N` generado por contador de archivos existentes.
- **Razón**: Sin base de datos, inspeccionable por un evaluador, ignorado por git.
- **Alternativas**: memoria del proceso (se pierde al cerrar y no queda evidencia para la demostración).

## D7. Validación del escalamiento
- **Decisión**: modelo `pydantic` con campos obligatorios `comercio`, `hallazgos` (por frente, con fuente), `cobertura`, `causa`, `accion_recomendada`; si falta alguno, la herramienta devuelve error `invalid_input` con la lista de campos faltantes.
- **Razón**: Comportamiento 11 (handoff útil) y FR-009.

## D8. Datos ficticios seguros
- **Decisión**: documentos y NIT con forma `FICT-000N`, nombres evidentemente inventados, nombres de fuente terminados en `_ficticio/a`. Un test recorre `data/` y falla si encuentra algo con forma de documento, NIT o tarjeta numéricos.
- **Razón**: Constitución II y necesidad 5 del ecosistema; evita datos que "parezcan reales".

## D9. Descripciones como contrato
- **Decisión**: las descripciones se redactan en español, con "Cuándo usar", "Cuándo NO usar" y "Qué hacer con el resultado", y se prueban (cada descripción contiene los términos clave: p. ej. la de noticias dice que una mención no es coincidencia en listas).
- **Razón**: Comportamiento 6 y SC-006.
