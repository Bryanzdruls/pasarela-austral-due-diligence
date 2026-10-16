# Feature Specification: Coordinador y subagentes de due diligence

**Feature Branch**: `002-coordinador-subagentes`

**Created**: 2026-10-14

**Status**: Draft

**Input**: Issue #2 de GitHub — "Coordinador y subagentes (Agent SDK)". Un agente coordinador recibe la solicitud de un analista de Pasarela Austral, la descompone y delega cada frente de la investigación en cuatro subagentes especializados (registro mercantil, listas restrictivas, noticias y riesgo de categoría), y sintetiza un informe con su recomendación.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pedir un due diligence y recibir un informe sintetizado (Priority: P1)

Un analista interno escribe una solicitud en lenguaje natural, por ejemplo: "Necesito el due diligence de Tienda Verde SAS, identificador CO-TV-0001. Quieren procesar ventas en línea de suplementos dietarios y estiman unos $80.000.000 mensuales. ¿Lo podemos habilitar esta semana?". El coordinador entiende qué comercio, qué categoría y qué volumen se mencionan, reparte la investigación entre los cuatro frentes y entrega un informe con lo encontrado en cada frente y una recomendación.

**Why this priority**: Es el flujo principal del sistema; sin él no hay producto que demostrar.

**Independent Test**: Enviar la solicitud de ejemplo y verificar que se consultan los cuatro frentes y que la respuesta contiene una sección por frente y una recomendación.

**Acceptance Scenarios**:

1. **Given** una solicitud con un comercio identificable, **When** el analista la envía, **Then** el coordinador delega los cuatro frentes y responde con un informe que resume cada frente y da una recomendación.
2. **Given** una solicitud que no menciona ningún comercio, **When** el analista la envía, **Then** el coordinador pide el comercio o su identificador en lugar de investigar.
3. **Given** un informe ya entregado, **When** el analista hace una pregunta de seguimiento sobre un frente, **Then** el coordinador responde con lo ya investigado sin repetir toda la investigación.

---

### User Story 2 - Cada subagente ve solo lo suyo (Priority: P1)

Cada subagente recibe únicamente el contexto que necesita (el comercio, su identificador, el representante legal cuando aplique) y puede usar únicamente las herramientas de su frente. No ve la conversación del analista ni lo que hacen los otros subagentes. Cada subagente devuelve su resultado separando el contenido hallado de los metadatos (fuente y fecha de consulta).

**Why this priority**: Garantiza especialización, evita fugas de contexto y hace verificable la procedencia de cada dato.

**Independent Test**: Inspeccionar la definición de cada subagente: lista de herramientas permitidas y contexto recibido; ejecutar un caso y confirmar que ningún subagente usó una herramienta ajena a su frente.

**Acceptance Scenarios**:

1. **Given** el subagente de noticias, **When** intenta usar una herramienta de otro frente, **Then** no está disponible para él.
2. **Given** una conversación larga con el analista, **When** el coordinador delega un frente, **Then** el subagente recibe solo el encargo explícito, sin el historial de la conversación.
3. **Given** un frente que termina, **When** devuelve su resultado, **Then** el contenido y los metadatos (fuente, fecha) vienen separados.

---

### User Story 3 - Investigar en paralelo lo independiente y esperar lo dependiente (Priority: P2)

Los frentes que no dependen entre sí (registro mercantil, noticias, riesgo de categoría) se investigan al mismo tiempo. El frente de listas restrictivas depende del registro mercantil, porque necesita el comercio identificado y su representante legal, así que espera a que el registro termine.

**Why this priority**: Reduce el tiempo de respuesta y refleja las dependencias reales del negocio, pero el sistema es funcional sin ello.

**Independent Test**: Medir el orden de ejecución con frentes simulados de duración conocida: los tres independientes coinciden en el tiempo y listas empieza después de que registro termina.

**Acceptance Scenarios**:

1. **Given** una solicitud válida, **When** el coordinador delega, **Then** registro, noticias y riesgo se inician sin esperarse entre sí.
2. **Given** que el registro aún no termina, **When** el coordinador planifica, **Then** el frente de listas no se inicia hasta que el registro devuelva su resultado.
3. **Given** que el registro no identifica un único comercio, **When** el coordinador evalúa el siguiente paso, **Then** el frente de listas no se inicia y el coordinador lo informa (orientación del coordinador en este ticket; garantía determinista con el hook del ticket #3).

---

### User Story 4 - El ciclo termina cuando el modelo termina (Priority: P2)

El coordinador y cada subagente siguen trabajando mientras el modelo indique que necesita usar herramientas, y terminan cuando el modelo indique que ya concluyó. No terminan por un número fijo de vueltas ni por encontrar ciertas palabras en el texto de la respuesta.

**Why this priority**: Evita cortes prematuros (informes incompletos) y bucles sin fin, y es un comportamiento que se defiende explícitamente.

**Independent Test**: Con respuestas simuladas del modelo, verificar que el ciclo continúa mientras se solicita una herramienta, termina al concluir el modelo, y que una respuesta cuyo texto contiene "listo" o "terminado" pero que pide una herramienta no corta el ciclo.

**Acceptance Scenarios**:

1. **Given** un modelo que solicita herramientas varias veces seguidas, **When** corre el ciclo, **Then** continúa hasta que el modelo concluye, sin un tope fijo de iteraciones como criterio de salida normal.
2. **Given** un texto de respuesta que contiene la palabra "terminado" mientras el modelo aún solicita una herramienta, **When** se evalúa el ciclo, **Then** el ciclo continúa.
3. **Given** un modelo que concluye, **When** se evalúa el ciclo, **Then** termina y se entrega el resultado.

---

### Edge Cases

- La solicitud menciona más de un comercio: el coordinador pide aclarar cuál investigar (el manejo fino de ambigüedad se completa en el ticket #5).
- Un subagente no devuelve resultado utilizable: el coordinador lo registra como frente no completado (el manejo estructurado y la cobertura parcial se completan en el ticket #4).
- El analista cambia de comercio a mitad de la conversación: el coordinador inicia una investigación nueva sin arrastrar datos del comercio anterior.
- El volumen mensual estimado o la categoría vienen en la solicitud: se pasan al frente de riesgo y se citan en el informe como dato aportado por el analista, no como dato de una fuente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST aceptar una solicitud de due diligence en lenguaje natural y extraer de ella el comercio (nombre o identificador), la categoría de negocio y el volumen estimado cuando estén presentes.
- **FR-002**: El coordinador MUST descomponer la solicitud y delegar en cuatro subagentes: registro mercantil, listas restrictivas, noticias y riesgo de categoría.
- **FR-003**: Cada subagente MUST tener acceso únicamente a las herramientas de su frente (registro → consultar registro mercantil; listas → consultar listas restrictivas; noticias → buscar noticias; riesgo → consultar riesgo de categoría) y a ninguna otra.
- **FR-004**: Los subagentes MUST NOT heredar la conversación del coordinador; el coordinador MUST pasarles de forma explícita el encargo y los datos que necesitan.
- **FR-005**: Cada subagente MUST devolver su resultado separando el contenido de los metadatos (fuente y fecha de consulta).
- **FR-006**: Los frentes independientes (registro mercantil, noticias y riesgo de categoría) MUST investigarse en paralelo.
- **FR-007**: El coordinador MUST orientar el frente de listas restrictivas para que espere a que el registro mercantil termine, use el comercio y el representante legal que este identifique y no se inicie si el registro no identificó un único comercio. En este ticket esa condición es **orientación del coordinador** (instrucciones y verificación de la secuencia de eventos); su **garantía determinista** es un hook del SDK del ticket #3 (regla de negocio 1). Este requisito no se da por cumplido ante terceros hasta que el ticket #3 esté fusionado.
- **FR-008**: El ciclo del coordinador y el de cada subagente MUST continuar o terminar según la razón de parada del modelo; MUST NOT usar un número fijo de iteraciones ni la búsqueda de palabras en el texto como criterio de continuación o terminación.
- **FR-009**: Una vez completados los frentes, el coordinador MUST sintetizar un informe con una sección por frente y una recomendación.
- **FR-010**: Si falta información imprescindible en la solicitud (sin comercio identificable), el coordinador MUST pedirla al analista antes de delegar.
- **FR-011**: Los datos aportados por el analista (categoría declarada, volumen estimado) MUST distinguirse en el informe de los datos obtenidos de las fuentes.
- **FR-012**: Cuando el analista pasa a investigar otro comercio dentro de la misma conversación, el coordinador MUST iniciar una investigación nueva: los encargos a los subagentes contienen solo datos del comercio actual y ninguno del anterior.
- **FR-013**: El sistema MUST mantener la conversación entre turnos del analista (sesión multi-turno) de modo que una pregunta de seguimiento sobre un frente ya investigado se responda con lo ya obtenido, sin lanzar de nuevo los subagentes de ese frente.

### Key Entities *(include if feature involves data)*

- **Solicitud**: mensaje del analista; contiene comercio (nombre o identificador), categoría declarada y volumen estimado cuando existen.
- **Encargo de frente**: instrucción explícita del coordinador a un subagente con los datos que necesita y nada más.
- **Resultado de frente**: contenido hallado más metadatos (fuente, fecha de consulta), o la indicación de que el frente no se completó.
- **Informe de due diligence**: una sección por frente, datos aportados por el analista diferenciados, y una recomendación.
- **Dependencia entre frentes**: relación "listas depende de registro".
- **Sesión de conversación**: hilo multi-turno entre el analista y el coordinador; conserva lo investigado para responder seguimientos y se reinicia al comenzar una conversación nueva.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En la matriz de verificación con modelo real (al menos 3 solicitudes: una válida, una sin comercio identificable y una con comercio ambiguo), cada solicitud válida produce una respuesta con una sección por cada uno de los cuatro frentes y una recomendación, y cada solicitud no válida no dispara consultas a las fuentes; los resultados se anotan uno por uno.
- **SC-002**: En una revisión de la configuración, el 100 % de los subagentes tiene exactamente las herramientas de su frente y ninguna más.
- **SC-003**: Ningún subagente recibe en su encargo texto de la conversación del analista distinto del encargo explícito (verificable inspeccionando los encargos enviados).
- **SC-004**: En la secuencia de eventos de una investigación, los tres frentes independientes se inician antes de que termine cualquiera de ellos, y el frente de listas nunca se inicia antes de que termine el registro. Verificable por orden de eventos, con marcas de tiempo en cada evento.
- **SC-005**: En pruebas con respuestas simuladas del modelo, el 100 % de los ciclos continúa mientras se solicita una herramienta y termina cuando el modelo concluye, incluida la prueba en que el texto contiene una palabra de cierre.
- **SC-006**: Una solicitud sin comercio identificable no dispara ninguna consulta a las fuentes.
- **SC-007**: En la verificación con modelo real, una pregunta de seguimiento sobre un frente ya investigado no lanza ningún subagente nuevo, y un cambio de comercio genera encargos que no contienen datos del comercio anterior.

## Assumptions

- El analista conversa por texto en una sesión multi-turno (decisión del usuario para el seguimiento de preguntas); la interfaz de chat que la usa se construye en el ticket #7.
- Los comportamientos que decide el modelo (extraer el comercio, pedir datos faltantes, separar los datos del analista, no relanzar subagentes en un seguimiento) no se pueden demostrar solo offline: se verifican con pruebas del texto de las instrucciones y con la matriz manual con modelo real.
- Las fuentes son las seis herramientas del servidor MCP del ticket #1; este ticket no las modifica.
- La recomendación de este ticket es preliminar y se redacta con base en los hallazgos; las reglas de negocio 1-3 (consultar listas solo con comercio identificado, coincidencia en listas impide habilitar, alto riesgo nunca habilita automáticamente) se hacen cumplir con hooks en el ticket #3. Hasta entonces el sistema no debe usarse para decisiones reales.
- Los errores de fuente, la cobertura parcial, la procedencia, los conflictos entre fuentes, la ambigüedad del registro, el escalamiento y el handoff se completan en los tickets #4, #5 y #6; aquí se prevé solo el comportamiento mínimo descrito en los casos límite.
- Los casos de prueba obligatorios completos se automatizan en el ticket #8.
- La implementación usa el Claude Agent SDK en Python, decisión heredada de la constitución y del ticket; el plan la detalla.
