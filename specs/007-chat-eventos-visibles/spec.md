# Feature Specification: Interfaz de chat con eventos visibles

**Feature Branch**: `007-chat-eventos-visibles`

**Created**: 2026-10-17

**Status**: Draft

**Input**: Issue #7 de GitHub — "Interfaz de chat con eventos visibles". Interfaz tipo chat (FastAPI + HTML con SSE): mensajes del analista y del coordinador turno a turno, y eventos visibles cuando se delega a un subagente, se bloquea una llamada, se registra el informe o se escala. Criterio: alguien que no conoce el código entiende qué pasó. (Enunciado, comportamiento 12: "No se califica el diseño visual, sino que alguien que no conoce el código entienda qué pasó en la conversación".)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Conversar con el coordinador en el navegador y ver qué pasa turno a turno (Priority: P1)

El analista abre una página, escribe un mensaje y ve aparecer, en orden, su mensaje y la respuesta del coordinador. Mientras el coordinador trabaja ve que está trabajando y cuándo termina el turno; puede seguir con otro turno en la misma conversación (el coordinador conserva el contexto).

**Why this priority**: Es el comportamiento 12 del enunciado y lo que se mostrará en el video de funcionamiento: los casos obligatorios "en la interfaz de chat".

**Independent Test**: Con un cliente falso del SDK (sin modelo), enviar dos mensajes seguidos a una conversación y comprobar que el flujo de eventos trae, en orden, el mensaje del analista, la respuesta del coordinador y el fin de cada turno, y que el segundo turno usa la misma sesión.

**Acceptance Scenarios**:

1. **Given** la página abierta, **When** el analista envía un mensaje, **Then** aparece como mensaje del analista, seguido de un indicador de trabajo y de la respuesta del coordinador.
2. **Given** un turno en curso, **When** el analista intenta enviar otro mensaje, **Then** se le dice que espere a que termine; no se pierde ni se mezcla.
3. **Given** un turno terminado, **When** el analista envía otro mensaje, **Then** el coordinador responde con el contexto de la conversación (misma sesión).
4. **Given** que la página se recarga a mitad de conversación, **When** vuelve a abrirse la conversación, **Then** se reconstruye el historial de eventos desde el principio.
5. **Given** un turno que falla (el modelo no responde), **When** termina, **Then** se muestra un error claro y la conversación sigue utilizable.

---

### User Story 2 - Los eventos del sistema son visibles y se entienden sin conocer el código (Priority: P1)

Cuando el coordinador delega en un subagente, cuando un subagente responde (o falla), cuando el sistema bloquea una llamada porque incumpliría una regla, cuando se registra un informe y cuando se escala a un oficial de cumplimiento, la interfaz lo muestra como un evento propio, distinto de los mensajes, con lenguaje llano: quién hizo qué y por qué.

**Why this priority**: Es el criterio del issue: "alguien que no conoce el código entiende qué pasó". Sin los eventos, la conversación parece una caja negra: el bloqueo de una regla o el escalamiento no se verían.

**Independent Test**: Con un cliente falso que reproduce una delegación, y con las observaciones del sistema (un bloqueo de la regla 1, un informe y un escalamiento), comprobar que cada hecho produce un evento visible con su tipo y su texto, sin términos internos (nombres de herramientas, identificadores de hooks).

**Acceptance Scenarios**:

1. **Given** que el coordinador delega en un frente, **When** ocurre, **Then** se ve "Delegó en <frente>" con el encargo, y cuando responde se ve su resultado (completo, falló o sin estructura).
2. **Given** una llamada que un hook bloquea (por ejemplo, consultar listas sin identificar al comercio), **When** se bloquea, **Then** se ve un evento "Llamada bloqueada" con la regla en palabras y el motivo, quién lo intentó y qué se le pidió hacer.
3. **Given** un informe registrado, **When** se guarda, **Then** se ve "Informe registrado" con su número, el comercio y la recomendación.
4. **Given** un escalamiento registrado, **When** se guarda, **Then** se ve "Escalado a cumplimiento" con su número, el comercio y la causa.
5. **Given** un frente que falló, **When** el coordinador lo declara sin cubrir, **Then** el evento de resultado lo marca como fallido y el informe muestra qué quedó sin cubrir.
6. **Given** cualquier evento, **When** se muestra, **Then** lleva su hora y un icono o etiqueta que lo distingue de los mensajes.

---

### User Story 3 - Arranque simple, local y seguro (Priority: P2)

Quien revisa el repositorio arranca la interfaz con un solo comando, la abre en el navegador y usa el mismo coordinador y los mismos hooks que la consola. La interfaz solo escucha en la máquina local y no deja inyectar HTML en la página.

**Why this priority**: El revisor debe poder ejecutarla en menos de cinco minutos (README) y la interfaz muestra texto generado por un modelo y por fuentes: no debe ejecutarlo como código.

**Independent Test**: El comando de arranque escucha solo en 127.0.0.1; una respuesta con etiquetas HTML se muestra como texto; el estado de la aplicación responde sin modelo.

**Acceptance Scenarios**:

1. **Given** el comando de arranque, **When** se ejecuta, **Then** la interfaz queda disponible en una dirección local indicada en la salida.
2. **Given** un mensaje del modelo o de una fuente con etiquetas HTML o scripts, **When** se muestra, **Then** se ve como texto y no se interpreta.
3. **Given** que falta la autenticación del modelo, **When** se envía un mensaje, **Then** el turno termina con un error legible y no se cuelga la página.

---

### Edge Cases

- Varias pestañas abiertas sobre la misma conversación ven los mismos eventos.
- Un bloqueo de un subagente no aparece en el flujo de mensajes del SDK: se observa con la misma decisión que toma el hook.
- Una conversación inexistente responde con un error claro, no con una página en blanco.
- Un mensaje vacío o demasiado largo se rechaza con un motivo.
- El analista cierra la página: el turno en curso termina y su resultado queda en el historial.
- Un informe o escalamiento rechazado por un hook se muestra como bloqueo, no como registro.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La interfaz MUST permitir crear una conversación, enviar mensajes y recibir, en tiempo real, los eventos de cada turno en orden.
- **FR-002**: Cada mensaje del analista y cada respuesta del coordinador MUST mostrarse como mensaje distinto de los eventos del sistema.
- **FR-003**: Cuando el coordinador delega en un subagente, la interfaz MUST mostrar la delegación (frente y encargo) y, al terminar, su resultado (completo, fallido o sin estructura).
- **FR-004**: Cuando un hook bloquea una llamada, la interfaz MUST mostrar un evento de bloqueo con la regla en palabras, el motivo y quién lo intentó, decidido por la misma decisión del hook y no por el texto del modelo.
- **FR-005**: Cuando se registra un informe o un escalamiento, la interfaz MUST mostrar un evento con su número, el comercio y la recomendación o la causa; solo si el servidor confirmó el registro.
- **FR-006**: Cada turno MUST cerrarse con un evento de fin (o de error) y la conversación MUST seguir utilizable.
- **FR-007**: La conversación MUST conservar el contexto entre turnos y reconstruir el historial de eventos para quien se conecte o recargue.
- **FR-008**: Un segundo mensaje mientras hay un turno en curso MUST rechazarse con un mensaje claro.
- **FR-009**: Los eventos MUST estar escritos en lenguaje llano, sin nombres de herramientas ni identificadores internos como único texto, y cada uno con su hora y su tipo.
- **FR-010**: El texto mostrado MUST tratarse como texto, nunca como HTML ejecutable; la interfaz MUST escuchar solo en la máquina local y validar la entrada (mensaje no vacío, tamaño máximo).
- **FR-011**: La interfaz MUST usar el mismo coordinador, los mismos hooks y las mismas reglas que la consola, sin duplicar lógica de negocio; MUST NOT cambiar el comportamiento del sistema.
- **FR-012**: Un comando MUST arrancar la interfaz e indicar la dirección local; sin autenticación del modelo, el error MUST ser legible.

### Key Entities *(include if feature involves data)*

- **Conversación**: una sesión con el coordinador, con su historial de eventos y los navegadores conectados.
- **Evento visible**: un hecho de la conversación con tipo (analista, coordinador, delegación, resultado de un frente, bloqueo, informe, escalamiento, fin, error), título, detalle y hora.
- **Observación del sistema**: un hecho que no viaja en el flujo de mensajes del SDK (un bloqueo de un hook, un informe o un escalamiento registrado) y que la interfaz recoge del propio sistema.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Con un cliente falso, dos turnos seguidos producen el flujo completo de eventos en orden y el segundo reutiliza la sesión.
- **SC-002**: Los cinco hechos del issue (delegación, resultado de un frente, bloqueo, informe y escalamiento) producen cada uno un evento visible con su tipo, y el 100 % de los textos de muestra se escapan como texto.
- **SC-003**: Los siete casos obligatorios se pueden recorrer en la interfaz con el modelo real y el evento correspondiente (bloqueo, informe o escalamiento) aparece en cada uno donde ocurre.
- **SC-004**: Una persona que no conoce el código entiende, mirando solo la interfaz, qué hizo el sistema en cada caso (verificado con una captura o una descripción literal de los eventos del caso).
- **SC-005**: Las 1344 pruebas anteriores siguen pasando sin modificarse, salvo lo que justifique el nuevo tipo de eventos.

## Assumptions

- "FastAPI + HTML con SSE" del issue se cumple con Starlette (la base de FastAPI, ya instalada con el SDK de MCP), `uvicorn` y `sse-starlette`, declarados en las dependencias: no se añade un framework solo para enrutar tres rutas. Se declara como decisión en el plan.
- La interfaz es una demostración local: sin autenticación de usuarios ni persistencia; el historial vive en memoria mientras corre el proceso.
- El diseño visual no se califica: basta que cada evento se distinga y se entienda.
- Los bloqueos de las llamadas de los subagentes no viajan en el flujo de mensajes del SDK: se recogen de la decisión del hook de reglas.
- La interfaz no cambia las reglas: solo muestra lo que el sistema decide.
