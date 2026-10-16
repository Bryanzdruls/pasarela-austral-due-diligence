# Feature Specification: Hooks del SDK para las reglas de negocio 1 a 3

**Feature Branch**: `003-hooks-reglas-negocio`

**Created**: 2026-10-16

**Status**: Draft

**Input**: Issue #3 de GitHub — "Hooks del SDK para reglas de negocio 1-3". Hacer cumplir con hooks del Agent SDK, y no con el prompt, tres reglas de la pasarela: (1) no consultar listas restrictivas sin que el comercio esté identificado de forma unívoca en el registro mercantil; (2) una coincidencia en listas impide recomendar la habilitación y escala el caso; (3) una categoría de alto riesgo nunca recibe habilitación automática. Criterio: pruebas que demuestran el bloqueo de cada regla.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Las listas restrictivas solo se consultan para un comercio identificado de forma unívoca (Priority: P1)

Cuando el sistema intenta consultar las listas restrictivas, la consulta solo se permite si en la misma conversación el registro mercantil ya identificó a ese comercio de forma unívoca (una única coincidencia, existente). La consulta de una persona solo se permite si es el representante legal de un comercio así identificado. Si no, la consulta se bloquea antes de ejecutarse y el motivo llega al modelo para que corrija el rumbo, sin que importe lo que el prompt o el modelo "crean".

**Why this priority**: Es la regla 1 del enunciado y una **falta grave** mientras dependa solo del prompt. Es también el caso de prueba obligatorio "consulta a listas sin identificación unívoca, bloqueada".

**Independent Test**: Intentar la consulta a listas (a) sin ninguna consulta previa al registro, (b) tras un registro ambiguo con varias coincidencias, (c) tras un registro sin resultados, (d) con un identificador distinto del identificado, y (e) tras un registro unívoco; comprobar que solo (e) se permite y que las demás se bloquean con un motivo claro.

**Acceptance Scenarios**:

1. **Given** una conversación sin ningún resultado del registro, **When** se intenta consultar las listas para un comercio, **Then** la consulta se bloquea y el motivo dice que falta identificarlo en el registro.
2. **Given** un registro que devolvió varias coincidencias, **When** se intenta consultar las listas con cualquiera de ellas, **Then** se bloquea: el comercio no está identificado de forma unívoca.
3. **Given** un registro que devolvió una única coincidencia existente, **When** se consultan las listas para ese comercio y para su representante legal, **Then** ambas consultas se permiten.
4. **Given** un comercio identificado, **When** se intenta consultar las listas para otro comercio o para una persona que no es su representante legal, **Then** se bloquea.
5. **Given** un resultado del registro que no se puede interpretar o que es un error, **When** se intenta consultar las listas, **Then** se bloquea (ante la duda, se deniega).

---

### User Story 2 - Una coincidencia en listas impide recomendar la habilitación y el caso se escala (Priority: P1)

Si las listas restrictivas devolvieron una coincidencia para el comercio o para su representante legal, el sistema no puede registrar un informe que recomiende habilitar. La única salida permitida es escalar el caso a un oficial de cumplimiento (o no habilitar). El bloqueo se decide con lo que las listas devolvieron, no con lo que el modelo diga.

**Why this priority**: Es la regla 2 del enunciado y falta grave si depende del prompt. Es el caso de prueba "representante legal con coincidencia en listas".

**Independent Test**: Simular una coincidencia (del comercio y, por separado, del representante legal) y comprobar que un informe con la recomendación de habilitar se rechaza con un motivo claro, mientras que escalar a cumplimiento se permite; sin coincidencia, habilitar no se bloquea por esta regla.

**Acceptance Scenarios**:

1. **Given** una coincidencia en listas para el comercio, **When** se intenta registrar un informe que recomienda habilitar, **Then** se rechaza y el motivo indica que corresponde escalar.
2. **Given** una coincidencia en listas solo para el representante legal, **When** se intenta registrar un informe que recomienda habilitar, **Then** se rechaza igual.
3. **Given** una coincidencia, **When** se escala el caso a un oficial de cumplimiento, **Then** la acción se permite.
3b. **Given** una coincidencia y un caso sin escalar, **When** el sistema intenta dar la respuesta por terminada, **Then** se le exige primero escalar el caso a un oficial de cumplimiento (se le pide una sola vez; si ya se pidió, no se vuelve a bloquear para no entrar en un bucle).
4. **Given** ninguna coincidencia y ninguna otra regla aplicable, **When** se registra un informe que recomienda habilitar, **Then** esta regla no lo bloquea.

---

### User Story 3 - Un comercio de alto riesgo nunca recibe habilitación automática (Priority: P1)

Si el comercio pertenece a una categoría de alto riesgo (apuestas, criptoactivos, suplementos dietarios, venta de medicamentos), el sistema no puede registrar una recomendación de habilitar: la decisión es de un oficial de cumplimiento. La categoría se determina por lo que consta en el registro, por la categoría consultada en el catálogo de riesgo y por la que el analista declaró en su solicitud, y la lista de categorías de alto riesgo es de la pasarela: no depende de que el catálogo la clasifique (si el catálogo devuelve "sin clasificar" para una categoría de alto riesgo, la regla se aplica igual).

**Why this priority**: Es la regla 3 del enunciado. En la verificación con el modelo real el catálogo devolvió "sin clasificar" para "suplementos dietarios (venta en línea)", y solo la lista propia de la pasarela habría detectado el riesgo.

**Independent Test**: Para cada una de las cuatro categorías, comprobar que la recomendación de habilitar se rechaza cuando la categoría consta en el registro, cuando el analista la declaró y cuando el catálogo la marca alta; y que, con una categoría de riesgo bajo y sin otras alertas, habilitar se permite.

**Acceptance Scenarios**:

1. **Given** un comercio cuya categoría en el registro es de alto riesgo, **When** se intenta registrar una recomendación de habilitar, **Then** se rechaza y el motivo indica que decide un oficial de cumplimiento.
2. **Given** que el analista declaró una categoría de alto riesgo en su solicitud, **When** se intenta habilitar, **Then** se rechaza aunque el registro diga otra categoría.
3. **Given** que el catálogo devolvió "sin clasificar" para una categoría de la lista de alto riesgo de la pasarela, **When** se intenta habilitar, **Then** se rechaza igual.
4. **Given** un comercio de riesgo bajo, sin coincidencias en listas, **When** se recomienda habilitar, **Then** se permite.
5. **Given** un comercio de alto riesgo, **When** se escala a un oficial de cumplimiento, **Then** se permite.
6. **Given** un comercio de alto riesgo sin escalar, **When** el sistema intenta dar la respuesta por terminada, **Then** se le exige primero escalar el caso (una sola vez).

---

### User Story 4 - Las reglas no se pueden eludir y se pueden demostrar (Priority: P2)

Las tres reglas se aplican siempre, también cuando el modelo o un subagente intentan otro camino (otro identificador, otra herramienta, una recomendación redactada de forma distinta). La recomendación de un informe se expresa con un vocabulario cerrado, de modo que se pueda verificar; una recomendación fuera del vocabulario se rechaza. Cada regla tiene pruebas que demuestran su bloqueo, y romper una regla a propósito hace fallar alguna prueba.

**Why this priority**: Un hook que se puede esquivar con otra redacción equivale a una instrucción de prompt. La demostración con pruebas es el criterio del issue.

**Independent Test**: Intentar recomendaciones con redacciones alternativas y fuera de vocabulario, e identificadores alternativos, y comprobar que no esquivan las reglas; romper cada regla en el código y comprobar que alguna prueba falla.

**Acceptance Scenarios**:

1. **Given** una recomendación que no pertenece al vocabulario cerrado, **When** se intenta registrar el informe, **Then** se rechaza y el motivo lista los valores permitidos.
2. **Given** un informe para un comercio que nunca se identificó en la conversación, **When** se recomienda habilitar, **Then** se rechaza.
3. **Given** cualquier regla, **When** se rompe a propósito en el código, **Then** al menos una prueba falla.
4. **Given** una conversación con dos comercios, **When** se investiga el segundo, **Then** las identificaciones, coincidencias y riesgos del primero no se mezclan con los del segundo.

---

### Edge Cases

- El registro devuelve un error o un resultado que no se puede interpretar: el comercio no queda identificado.
- El registro devuelve una única coincidencia pero el comercio no existe o no está activo: no queda identificado de forma unívoca.
- Las listas devuelven coincidencia para el representante legal pero no para el comercio: la regla 2 aplica igual.
- Una consulta a listas que falla (fuente caída) no equivale a "sin coincidencias": el tratamiento completo de la falla es del ticket #4; aquí no se puede deducir de ella una ausencia de coincidencias.
- La categoría de alto riesgo aparece solo en la solicitud del analista, solo en el registro o solo en el catálogo: cualquiera basta.
- Una categoría que contiene una de las de alto riesgo con matices ("venta en línea de suplementos dietarios"): cuenta como alto riesgo.
- El analista pide registrar un informe de un comercio distinto del identificado.
- El modelo intenta registrar el informe antes de haber consultado las listas: el orden de las consultas no lo decide esta regla; lo que se verifica es lo ya consultado.
- Una misma conversación investiga varios comercios seguidos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST bloquear, antes de ejecutarla, toda consulta a las listas restrictivas de un comercio que no haya sido identificado de forma unívoca por el registro mercantil en la misma conversación.
- **FR-002**: Un comercio MUST considerarse identificado de forma unívoca solo si el registro devolvió una única coincidencia, existente, para él; una respuesta ambigua, vacía, con error o ininterpretable MUST NOT identificarlo.
- **FR-003**: El sistema MUST permitir la consulta a listas de una persona solo cuando es el representante legal de un comercio identificado de forma unívoca.
- **FR-004**: El sistema MUST registrar lo que cada fuente devolvió (identificación, coincidencias en listas y riesgo de categoría) por comercio, y MUST NOT mezclar lo de un comercio con lo de otro.
- **FR-005**: El sistema MUST rechazar el registro de un informe cuya recomendación sea habilitar si las listas devolvieron una coincidencia para el comercio o para su representante legal.
- **FR-006**: El sistema MUST permitir escalar a un oficial de cumplimiento en cualquier caso en que la regla 2 o la 3 impidan habilitar.
- **FR-015**: Cuando la regla 2 o la 3 aplica a un comercio y el caso no ha sido escalado, el sistema MUST exigir el escalamiento antes de dar la respuesta por terminada. La exigencia se hace una sola vez por respuesta: si ya se pidió y el modelo cierra igualmente, no se vuelve a bloquear, para no entrar en un bucle. El contenido y el criterio del resumen para el oficial son del ticket #6.
- **FR-007**: El sistema MUST rechazar el registro de un informe que recomiende habilitar si el comercio es de alto riesgo, determinado por cualquiera de estas fuentes: la categoría en el registro, la categoría consultada en el catálogo de riesgo y la categoría declarada por el analista en su solicitud.
- **FR-008**: La lista de categorías de alto riesgo (apuestas, criptoactivos, suplementos dietarios y venta de medicamentos) MUST ser propia de la pasarela y aplicarse aunque el catálogo no la clasifique; una categoría que contenga una de ellas con matices MUST contar como alto riesgo.
- **FR-009**: La recomendación de un informe MUST expresarse con un vocabulario cerrado (habilitar, no habilitar, escalar a un oficial de cumplimiento); una recomendación fuera del vocabulario MUST rechazarse indicando los valores permitidos.
- **FR-010**: El sistema MUST rechazar una recomendación de habilitar para un comercio que no se haya identificado de forma unívoca en la conversación.
- **FR-011**: Todo bloqueo MUST devolver al modelo un motivo claro que diga qué regla se incumplió y qué hacer, y MUST ser visible para quien depura la conversación.
- **FR-012**: Ante un resultado que no se pueda interpretar o un error del propio mecanismo, el sistema MUST denegar la acción (falla cerrado) y nunca permitirla por defecto.
- **FR-013**: Las decisiones MUST tomarse con lo devuelto por las fuentes y lo declarado por el analista, y MUST NOT depender de lo que el modelo afirme en su texto.
- **FR-014**: Cada regla MUST tener pruebas que demuestren su bloqueo y su caso permitido, y las instrucciones del prompt MUST NOT ser la única garantía de ninguna.

### Key Entities

- **Caso de comercio**: lo que se sabe de un comercio durante la conversación: si fue identificado de forma unívoca, quién es su representante legal, su categoría registrada, si las listas devolvieron coincidencia (del comercio o del representante) y si es de alto riesgo.
- **Recomendación**: valor del vocabulario cerrado con el que un informe concluye: habilitar, no habilitar o escalar a un oficial de cumplimiento.
- **Decisión de una regla**: permitir o bloquear, con el motivo y la regla (1, 2 o 3) que la originó.
- **Categoría de alto riesgo**: apuestas, criptoactivos, suplementos dietarios y venta de medicamentos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100 % de los intentos de consultar las listas sin identificación unívoca previa (sin registro, registro ambiguo, vacío, con error, ininterpretable, o con un identificador distinto) se bloquea antes de ejecutarse.
- **SC-002**: El 100 % de los informes que recomiendan habilitar tras una coincidencia en listas (del comercio o del representante legal) se rechaza.
- **SC-003**: El 100 % de las recomendaciones de habilitar para cada una de las cuatro categorías de alto riesgo se rechaza, venga la categoría del registro, de la solicitud del analista o del catálogo, y también cuando el catálogo responde "sin clasificar".
- **SC-008**: El 100 % de los comercios con coincidencia en listas o de alto riesgo cuya respuesta intenta cerrarse sin escalar reciben la exigencia de escalar, y la exigencia no se repite en el mismo cierre.
- **SC-004**: Los flujos legítimos no se bloquean: un comercio identificado de forma unívoca, de riesgo bajo y sin coincidencias puede consultar las listas y recibir una recomendación de habilitar, y cualquier comercio puede escalarse.
- **SC-005**: Para cada regla, romperla a propósito en el código hace fallar al menos una prueba (verificación por mutación).
- **SC-006**: En una ejecución con el modelo real, un intento de consultar las listas sin identificación previa queda bloqueado y el modelo lo comunica; los casos de la verificación del ticket #2 (habilitación de un comercio de riesgo bajo y derivación de uno de alto riesgo) siguen funcionando.
- **SC-007**: Ninguna de las tres reglas depende solo de una instrucción de prompt: el repositorio muestra, para cada una, el mecanismo que la impone y la prueba que lo demuestra.

## Assumptions

- La recomendación de un informe se expresa con tres valores cerrados (habilitar, no habilitar, escalar a un oficial de cumplimiento); el nombre exacto de cada valor se fija en el plan.
- "La misma conversación" es la sesión del analista: lo identificado, consultado y declarado en ella es la base de las decisiones.
- Para que las reglas 2 y 3 sean aplicables, el coordinador debe poder registrar el informe y escalar: se le permiten esas dos acciones **solo bajo estas reglas**. El contenido y el criterio del escalamiento y del resumen para el oficial son del ticket #6.
- La categoría declarada por el analista se toma del texto de su solicitud en la misma conversación, buscando las categorías de la lista de alto riesgo de la pasarela; ante la duda, se aplica el criterio más conservador (no habilitar).
- Fuera de alcance: errores estructurados y cobertura parcial (#4), procedencia y conflictos entre fuentes y ambigüedad (#5), contenido del escalamiento y del resumen para el oficial (#6), interfaz de chat (#7), casos automatizados de extremo a extremo (#8).
- Las pruebas de este ticket no llaman al modelo real; la comprobación con el modelo real queda documentada aparte.
- Datos y ejemplos son ficticios; los identificadores usan el formato `CO-XX-000N` y `PE-000N`.
