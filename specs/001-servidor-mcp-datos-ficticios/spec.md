# Feature Specification: Servidor de fuentes ficticias de la pasarela

**Feature Branch**: `001-servidor-mcp-datos-ficticios`

**Created**: 2026-10-14

**Status**: Draft

**Input**: Issue #1 de GitHub — "Servidor MCP y datos ficticios". Servidor propio de Pasarela Austral con seis herramientas que simulan las fuentes de la investigación de due diligence (registro mercantil, listas restrictivas, noticias, riesgo de categoría) y las dos acciones de salida (registrar informe, escalar a cumplimiento), con datos completamente ficticios.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar el registro mercantil (Priority: P1)

El sistema de due diligence necesita identificar a un comercio de forma unívoca antes de investigarlo. Busca por nombre o por identificador y recibe existencia, fecha de constitución, representante legal y estado. Si el nombre es ambiguo, recibe todas las coincidencias y no una elegida por el servidor.

**Why this priority**: Es la puerta de entrada de toda la investigación; la regla 1 de la pasarela depende de poder distinguir "una coincidencia" de "varias" o "ninguna".

**Independent Test**: Buscar "CO-TV-0001" devuelve exactamente un comercio con sus datos; buscar un nombre compartido por dos comercios devuelve ambos con una indicación explícita de ambigüedad; buscar algo inexistente devuelve cero coincidencias.

**Acceptance Scenarios**:

1. **Given** un comercio con identificador único en los datos, **When** se consulta por ese identificador, **Then** se devuelve una sola coincidencia con existencia, fecha de constitución, representante legal y estado, más la fuente y la fecha de consulta.
2. **Given** dos comercios con nombres casi idénticos, **When** se consulta por ese nombre, **Then** se devuelven ambos, marcados como coincidencias múltiples, sin elegir ninguno.
3. **Given** un nombre o identificador que no existe, **When** se consulta, **Then** se informa cero coincidencias de forma explícita (no es un error).

---

### User Story 2 - Consultar listas restrictivas, noticias y riesgo de categoría (Priority: P1)

El sistema verifica a un comercio o a una persona (p. ej. el representante legal) contra listas restrictivas ficticias, busca menciones en un corpus de noticias ficticias y consulta el nivel de riesgo de una categoría de negocio. Cada herramienta describe con claridad qué significa su resultado.

**Why this priority**: Son los tres frentes restantes de la investigación; sin ellos no hay informe.

**Independent Test**: Consultar a una persona sembrada en las listas devuelve coincidencia; consultar un comercio limpio no devuelve coincidencia; una noticia que menciona a un comercio se devuelve como mención y nunca como coincidencia en listas; "suplementos dietarios" devuelve riesgo alto y una categoría de bajo riesgo devuelve riesgo bajo.

**Acceptance Scenarios**:

1. **Given** un representante legal sembrado en las listas ficticias, **When** se consulta como persona, **Then** se devuelve coincidencia con la lista de origen y la fecha.
2. **Given** un comercio con una noticia adversa en el corpus, **When** se buscan noticias, **Then** se devuelven las menciones con su fuente y fecha, y la respuesta aclara que una mención no equivale a coincidencia en listas.
3. **Given** las categorías apuestas, criptoactivos, suplementos dietarios y venta de medicamentos, **When** se consulta su riesgo, **Then** todas se devuelven como riesgo alto.
4. **Given** una categoría desconocida, **When** se consulta su riesgo, **Then** se informa que no está clasificada, sin asumir un nivel.

---

### User Story 3 - Registrar el informe y escalar a cumplimiento (Priority: P2)

Al terminar, el sistema registra el informe de due diligence con su recomendación, o escala el caso a un oficial de cumplimiento con un resumen estructurado. Ambas acciones quedan guardadas y se pueden consultar después.

**Why this priority**: Cierran el ciclo de la investigación, pero dependen de que las consultas existan primero.

**Independent Test**: Registrar un informe devuelve un identificador y queda guardado; escalar un caso con resumen completo devuelve un identificador de escalamiento y queda guardado; un resumen al que le falta algún campo obligatorio es rechazado indicando qué falta.

**Acceptance Scenarios**:

1. **Given** un informe con comercio, recomendación, hallazgos con fuente y cobertura, **When** se registra, **Then** se devuelve un identificador y el informe queda almacenado tal cual.
2. **Given** un resumen de escalamiento con comercio, hallazgos por frente con fuentes, cobertura, causa y acción recomendada, **When** se escala, **Then** se devuelve un identificador y el resumen queda almacenado.
3. **Given** un resumen de escalamiento sin causa o sin acción recomendada, **When** se intenta escalar, **Then** se rechaza indicando los campos faltantes.

---

### User Story 4 - Simular fallas de una fuente (Priority: P2)

Quien prueba el sistema puede configurar que una fuente concreta (p. ej. noticias) falle, para verificar que el informe se entrega declarando la cobertura incompleta.

**Why this priority**: Es necesaria para el caso de prueba de falla de noticias, pero no bloquea las consultas normales.

**Independent Test**: Con la falla de noticias activada, buscar noticias devuelve un error estructurado que indica la fuente, si se puede reintentar y que no se obtuvo contenido; con la falla desactivada, el comportamiento es normal.

**Acceptance Scenarios**:

1. **Given** la falla de noticias activada, **When** se buscan noticias, **Then** se devuelve un error estructurado (fuente, causa, reintentable sí/no) en lugar de resultados.
2. **Given** ninguna falla configurada, **When** se consulta cualquier fuente, **Then** responde normalmente.
3. **Given** una falla configurada solo para noticias, **When** se consulta el registro mercantil, **Then** responde normalmente.

---

### Edge Cases

- Consulta con texto vacío o solo espacios: se rechaza con un mensaje claro, no devuelve todo el registro.
- Diferencias de mayúsculas, tildes o razón social abreviada ("SAS", "S.A.S."): el comercio se encuentra igual.
- Una persona de nombre parecido pero distinta a alguien en listas: la consulta de listas se hace por identificador de persona o comercio, no por nombre, así que un parecido de nombre nunca produce coincidencia por sí solo.
- Dos fuentes con fechas de constitución distintas para el mismo comercio: ambas se devuelven, cada una con su origen; el servidor no elige.
- Informe registrado dos veces para el mismo comercio: se guardan como registros separados con identificadores distintos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El servidor MUST exponer exactamente seis herramientas: consultar registro mercantil, consultar listas restrictivas, buscar noticias, consultar riesgo de categoría, registrar informe y escalar a cumplimiento.
- **FR-002**: La consulta al registro mercantil MUST aceptar nombre o identificador y devolver, por cada coincidencia: existencia, fecha de constitución, representante legal y estado.
- **FR-003**: Cuando el registro encuentre más de una coincidencia, MUST devolverlas todas con una marca explícita de ambigüedad y MUST NOT seleccionar una.
- **FR-004**: La consulta a listas restrictivas MUST aceptar un comercio o una persona e indicar si hay coincidencia, con la lista de origen y la fecha.
- **FR-005**: La búsqueda de noticias MUST devolver las menciones de un comercio o persona con fuente y fecha, y su descripción MUST dejar claro que una mención no es una coincidencia en listas restrictivas.
- **FR-006**: La descripción de la consulta al registro MUST indicar qué hacer cuando hay varias coincidencias (no elegir; pedir el identificador).
- **FR-007**: La consulta de riesgo MUST devolver riesgo alto para apuestas, criptoactivos, suplementos dietarios y venta de medicamentos, y MUST indicar "sin clasificar" para categorías desconocidas.
- **FR-008**: Toda respuesta MUST separar el contenido de los metadatos (fuente y fecha de consulta).
- **FR-009**: Registrar informe MUST almacenar el informe y devolver un identificador; escalar a cumplimiento MUST exigir comercio, hallazgos por frente con fuentes, cobertura, causa y acción recomendada, y rechazar lo incompleto indicando los campos faltantes.
- **FR-010**: El servidor MUST permitir configurar fallas por fuente; una fuente fallida MUST devolver un error estructurado con la fuente, la causa y si es reintentable.
- **FR-011**: Los datos MUST ser exclusivamente ficticios, residir en archivos locales y usar identificadores con formato `CO-XX-000N`; NIT, cédulas y nombres MUST ser claramente inventados.
- **FR-012**: Los datos MUST permitir reproducir los casos obligatorios: Tienda Verde SAS (CO-TV-0001, suplementos dietarios, ~$80.000.000 mensuales), un comercio de bajo riesgo sin hallazgos, un representante legal con coincidencia en listas, dos comercios con nombres casi idénticos y un comercio cuya fecha de constitución difiere entre dos fuentes.
- **FR-013**: El servidor MUST NOT aplicar las reglas de negocio de decisión (bloqueo de listas sin identificación unívoca, no habilitar con coincidencia o alto riesgo); esas reglas las hacen cumplir los hooks del coordinador en otra feature. Las herramientas solo informan.

### Key Entities *(include if feature involves data)*

- **Comercio**: negocio ficticio con identificador `CO-XX-000N`, razón social, NIT ficticio, fecha de constitución, estado, categoría, volumen mensual estimado y representante legal.
- **Persona**: representante legal ficticio con nombre y documento ficticio.
- **Entrada de lista restrictiva**: persona o comercio ficticio presente en una lista, con nombre de la lista y fecha de inclusión.
- **Noticia**: artículo ficticio con titular, fecha, fuente y las personas o comercios que menciona.
- **Categoría de negocio**: nombre y nivel de riesgo (alto, bajo o sin clasificar).
- **Informe de due diligence**: comercio, recomendación, hallazgos con fuente, cobertura, fecha de registro e identificador.
- **Escalamiento**: caso enviado a un oficial de cumplimiento con su resumen estructurado e identificador.
- **Respuesta de fuente**: contenido más metadatos (fuente, fecha de consulta), o un error estructurado (fuente, causa, reintentable).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Los seis casos obligatorios del enunciado que dependen de datos pueden reproducirse únicamente con los datos incluidos, sin preparar nada adicional. El séptimo (consulta de listas sin identificación unívoca, bloqueada) lo impone un hook del coordinador y se demuestra en el ticket #3.
- **SC-002**: El 100 % de las respuestas de las fuentes separa contenido y metadatos (fuente, fecha) de forma verificable.
- **SC-003**: Una búsqueda ambigua en el registro devuelve el 100 % de las coincidencias y ninguna se presenta como elegida.
- **SC-004**: Con una falla configurada, la fuente afectada devuelve un error estructurado en el 100 % de las consultas y las demás fuentes no se ven afectadas.
- **SC-005**: Una revisión de todo el contenido de datos del repositorio no encuentra ningún dato con apariencia de real (documentos, NIT, tarjetas, personas o empresas reales).
- **SC-006**: Un evaluador puede leer la descripción de cada herramienta y distinguir sin ambigüedad cuándo usar noticias frente a listas restrictivas.

## Assumptions

- Los consumidores del servidor son el coordinador y los subagentes del sistema de due diligence (otra feature); no hay usuarios humanos directos.
- Los datos viven en archivos locales y el servidor los carga al iniciar; no se necesita base de datos real.
- Los informes y escalamientos registrados se guardan localmente (archivos o memoria de la sesión) con fines de demostración y pruebas.
- La configuración de fallas se hace al arrancar el servidor o antes de cada prueba, no por usuarios finales.
- Las reglas de negocio de decisión no se aplican en este servidor (ver FR-013); aquí solo se garantiza que las fuentes informen correctamente.
- Lenguaje de implementación: Python, decidido en la constitución; se detalla en el plan, no en esta especificación.
