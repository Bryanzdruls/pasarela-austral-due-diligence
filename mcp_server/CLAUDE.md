# Servidor de fuentes ficticias (`mcp_server/`)

Servidor MCP por stdio con las seis herramientas de la pasarela. Es un **servicio de fuentes**: informa, no decide. Las reglas de negocio de decisión (listas solo con comercio identificado, coincidencia que impide habilitar, alto riesgo) las garantizan hooks del Agent SDK en el coordinador, nunca este servidor.

## Convenciones

- **Sobre de respuesta**: toda herramienta devuelve `{ok: true, content, metadata: {source, fetched_at}}` o un error estructurado `{ok: false, source, error_code, retryable, partial}`. Contenido y metadatos nunca se mezclan.
- **Una constante `SOURCE` por herramienta** (`registro_mercantil_ficticio`, `listas_restrictivas_ficticias`, …). El coordinador valida contra ella: no se renombra sin actualizar `due_diligence/events.py`.
- **Las descripciones son contrato.** Las ve el modelo y dicen cuándo usar la herramienta y qué hacer con el resultado; tienen pruebas en `tests/test_server.py`. Una mención en noticias no es una coincidencia en listas: la descripción lo dice.
- **Datos**: solo en `mcp_server/data/*.json`, siempre ficticios (`CO-XX-000N`, `FICT-000N`). La regla `datos-ficticios` se carga al editarlos.
- **Fallas inyectables** con `PASARELA_FAULTS` (`registro`, `listas`, `noticias`, `riesgo`, con `:no_reintentable` opcional); un valor desconocido falla de forma visible.
- **Registros de salida** (informes y escalamientos) en `PASARELA_RUNTIME_DIR` (por defecto `data/runtime/`, ignorado por git); el id es consecutivo y nunca pisa un archivo.
- Errores de entrada → `invalid_input` con el detalle en `partial`; nunca una excepción cruda hacia el cliente.

## Antes de tocar nada

Mira `specs/001-servidor-mcp-datos-ficticios/` (spec, plan, contrato en `contracts/tools.md`). Las pruebas viven en `tests/` y en `tools/tests/`.
