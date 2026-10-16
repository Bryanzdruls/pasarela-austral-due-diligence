# Feature Specification: Errores estructurados y cobertura parcial

**Feature Branch**: `004-errores-cobertura-parcial`

**Created**: 2026-10-16

**Status**: Draft

**Input**: Issue #4 de GitHub — "Errores estructurados y cobertura parcial". Un subagente que falla devuelve error estructurado con lo obtenido y si es reintentable. El coordinador decide reintentar o entregar el informe declarando el frente sin cubrir. Criterio: nunca se presenta un informe parcial como completo (regla 5 del enunciado: si una fuente no responde, el informe indica qué frente quedó sin cubrir).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Un frente que falla se reporta con lo obtenido y si se puede reintentar (Priority: P1)

Cuando una fuente no responde, el subagente de ese frente no inventa ni calla: entrega al coordinador un resultado de error con el frente afectado, lo que alcanzó a obtener (puede ser nada) y si vale la pena reintentar. El coordinador distingue ese resultado de uno exitoso sin tener que interpretar texto libre.

**Why this priority**: Es la base de la regla 5: sin un error estructurado que llegue intacto al coordinador, nadie puede declarar el frente sin cubrir. El servidor de fuentes ya devuelve el error estructurado (#1); falta que el subagente lo trasmita y que el sistema lo reconozca.

**Independent Test**: Provocar la falla de cada una de las cuatro fuentes (reintentable y no reintentable) y comprobar que el resultado del subagente identifica el frente, conserva lo obtenido y marca si es reintentable, y que el sistema lo registra como frente fallido.

**Acceptance Scenarios**:

1. **Given** una falla reintentable de la fuente de noticias, **When** el subagente de noticias termina, **Then** su resultado indica que el frente falló, que es reintentable y qué alcanzó a obtener (nada).
2. **Given** una falla no reintentable de cualquiera de las cuatro fuentes, **When** el subagente termina, **Then** su resultado la marca como no reintentable.
3. **Given** una respuesta de un subagente que no se puede interpretar, **When** el sistema la recibe, **Then** el frente se trata como fallido y no como cubierto (ante la duda, no se da por cubierto).

---

### User Story 2 - El coordinador reintenta lo reintentable una vez y declara lo que no se pudo cubrir (Priority: P1)

Ante un frente fallido y reintentable, el coordinador lo reintenta una vez; si vuelve a fallar, o si la falla no es reintentable, no insiste: entrega el informe declarando ese frente como sin cubrir, con el motivo. Si el reintento tiene éxito, el frente queda cubierto y no se declara como fallido.

**Why this priority**: Es la decisión que pide el issue ("reintentar o declarar") y evita tanto el bucle de reintentos como el silencio.

**Independent Test**: Con una falla reintentable que persiste, una que se recupera al reintentar y una no reintentable, comprobar cuántas veces se intentó el frente y qué declara el informe en cada caso.

**Acceptance Scenarios**:

1. **Given** una falla reintentable que desaparece al reintentar, **When** el coordinador entrega el informe, **Then** el frente figura como cubierto y no hay declaración de cobertura incompleta.
2. **Given** una falla reintentable que persiste tras el reintento, **When** el coordinador entrega el informe, **Then** el frente figura como sin cubrir, con el motivo, y no se vuelve a intentar.
3. **Given** una falla no reintentable, **When** el coordinador decide, **Then** no la reintenta y declara el frente sin cubrir.
4. **Given** una falla de un frente, **When** los demás frentes tuvieron éxito, **Then** el informe conserva sus hallazgos: un frente caído no descarta los otros.

---

### User Story 3 - Un informe parcial nunca se presenta como completo (Priority: P1)

El informe que se registra y se muestra al analista dice qué frentes cubrió y cuáles no. Si algún frente falló, el sistema no permite registrar un informe que declare cobertura completa u omita ese frente: el registro se rechaza con un motivo que dice qué frente falta declarar. Además, sin registro mercantil o sin listas restrictivas cubiertos (los dos frentes que sostienen la identificación y la verificación del comercio) el sistema no permite recomendar la habilitación, tanto si el frente falló como si nunca se consultó: la decisión es no habilitar o escalar.

**Why this priority**: Es el criterio del issue y la regla 5 del enunciado. Una recomendación de habilitar apoyada en un frente que no respondió es una falta grave de la misma clase que las reglas 1 a 3, así que no puede depender de que el modelo se acuerde.

**Independent Test**: Provocar la falla de cada frente y comprobar que (a) un informe que no la declara se rechaza con el frente nombrado, (b) uno que la declara se acepta, (c) con registro o listas sin cubrir se rechaza `habilitar` y se acepta `no_habilitar` o `escalar_a_cumplimiento`, y (d) sin fallas, el informe con cobertura completa se acepta como antes.

**Acceptance Scenarios**:

1. **Given** que el frente de noticias falló, **When** se intenta registrar un informe que no lo declara sin cubrir, **Then** se rechaza y el motivo nombra el frente de noticias.
2. **Given** que el frente de noticias falló, **When** se registra un informe que lo declara sin cubrir, **Then** se acepta (con la recomendación que corresponda) y la declaración queda en el registro.
3. **Given** que el registro mercantil o las listas restrictivas no respondieron, **When** se intenta registrar un informe con recomendación `habilitar`, **Then** se rechaza y el motivo dice que ese frente es necesario para habilitar.
3b. **Given** un comercio identificado cuyas listas restrictivas nunca se consultaron (o solo se consultó una parte: el comercio pero no su representante legal), **When** se intenta registrar `habilitar`, **Then** se rechaza: habilitar exige listas consultadas.
4. **Given** que las listas no pudieron consultarse, **When** se registra un informe con `no_habilitar` o `escalar_a_cumplimiento`, **Then** se acepta, declarando el frente sin cubrir.
5. **Given** que ningún frente falló, **When** se registra un informe con cobertura completa, **Then** se acepta sin cambios respecto de antes.
6. **Given** un informe parcial aceptado, **When** el analista lo lee, **Then** ve de forma visible qué frentes quedaron sin cubrir, y el informe no usa un lenguaje de "completo" ni de "sin hallazgos" para ellos.

---

### Edge Cases

- Fallan los cuatro frentes: el informe se registra como no habilitado o escalado, con los cuatro declarados sin cubrir; nunca se inventan hallazgos.
- Falla la fuente de registro: las listas no se consultan (siguen sujetas a la regla 1) y ambos frentes quedan declarados sin cubrir.
- Falla solo la consulta del representante legal en listas pero no la del comercio: el frente de listas se considera sin cubrir en parte y así se declara; no se da por limpio.
- El reintento falla de otra manera que el primer intento: el prompt orienta a declarar el último error; el hook solo exige que el frente conste sin cubrir.
- El analista pregunta por un frente fallido en un turno de seguimiento: el coordinador lo reconoce como sin cubrir y ofrece reintentarlo; no responde con datos que no tiene.
- La falla es de un comercio y no se arrastra al siguiente que investigue el analista en la misma conversación.
- Un informe que declara sin cubrir un frente que sí respondió: no se rechaza (declarar de más es el lado seguro).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Cuando una fuente falla, el resultado del subagente MUST identificar el frente afectado, conservar lo que alcanzó a obtener y marcar si el error es reintentable.
- **FR-002**: El sistema MUST reconocer un resultado de error de un frente sin depender de interpretar texto libre, y MUST tratar como fallido cualquier resultado que no pueda interpretar.
- **FR-003**: El sistema MUST llevar por cada comercio de la conversación el estado de cada frente: cubierto, fallido reintentable, fallido no reintentable.
- **FR-004**: Ante un frente fallido y reintentable, el coordinador MUST reintentarlo como máximo una vez; ante uno no reintentable o tras el reintento fallido, MUST NOT insistir y MUST declararlo sin cubrir.
- **FR-005**: Los hallazgos de los frentes que sí respondieron MUST conservarse en el informe aunque otro frente haya fallado.
- **FR-006**: El sistema MUST rechazar el registro de un informe que no declare sin cubrir un frente fallido del comercio, y el motivo MUST nombrar los frentes que faltan por declarar.
- **FR-007**: El sistema MUST rechazar un informe con recomendación `habilitar` cuando el registro mercantil o las listas restrictivas del comercio no están cubiertos (por falla o porque nunca se consultaron, incluida la consulta del representante legal), con un motivo que lo explique; `no_habilitar` y `escalar_a_cumplimiento` siguen permitidos.
- **FR-008**: El informe registrado MUST declarar qué frentes quedaron sin cubrir y por qué (lo garantiza el hook, FR-006), y la respuesta al analista MUST mostrarlos de forma visible sin presentarlos como cubiertos, completos ni "sin hallazgos" (esto último lo orienta el prompt y se verifica con el modelo real, sin garantía de hook).
- **FR-009**: Todo escalamiento a cumplimiento MUST declarar los frentes sin cubrir, para que el oficial sepa qué falta verificar.
- **FR-010**: Estas comprobaciones MUST aplicarse de forma determinista, fuera del prompt, y fallar cerrado: si el estado de cobertura no puede evaluarse, el registro de un informe que recomienda habilitar se rechaza.
- **FR-011**: Un informe con todos los frentes cubiertos y las listas consultadas MUST aceptarse como antes; esta función no altera las reglas 1 a 3.
- **FR-012**: El estado de cobertura MUST aislarse por comercio y por solicitud: la falla de un comercio no se aplica a otro.

### Key Entities *(include if feature involves data)*

- **Frente**: cada una de las cuatro líneas de investigación (registro mercantil, listas restrictivas, noticias, riesgo de categoría).
- **Resultado de frente**: lo que un subagente entrega: éxito con contenido y metadatos, o error con frente, lo obtenido y si es reintentable.
- **Cobertura del comercio**: para cada frente del comercio, su estado (cubierto, fallido reintentable, fallido no reintentable) y cuántas veces se intentó.
- **Declaración de cobertura**: la parte del informe que dice qué frentes quedaron sin cubrir y el motivo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Para cada uno de los cuatro frentes y cada modo de falla (reintentable y no reintentable), el 100 % de los informes que no declaran el frente caído se rechazan, y el 100 % de los que lo declaran se aceptan.
- **SC-002**: Con el registro mercantil o las listas sin cubrir, el 100 % de los intentos de recomendar habilitar se rechazan.
- **SC-003**: Ningún frente se reintenta más de una vez por solicitud, ni se reintenta uno marcado como no reintentable.
- **SC-004**: En la verificación con el modelo real, el caso de falla del servicio de noticias termina con un informe que declara explícitamente "noticias" sin cubrir y conserva los hallazgos de los otros tres frentes.
- **SC-005**: Las pruebas existentes de las reglas 1 a 3 y del coordinador siguen pasando; solo se ajustan las que daban por válido habilitar sin haber consultado las listas, y cada ajuste queda justificado.
- **SC-006**: Cada comprobación de esta función tiene una prueba que se vio fallar antes de implementarla y una mutación que la rompe a propósito y es detectada.

## Assumptions

- Las cuatro fuentes y el formato del error estructurado ya existen en el servidor de fuentes (#1); este ticket no lo cambia.
- Un único reintento por frente y por solicitud es la política razonable para el alcance de la prueba: acota el coste y evita bucles, y está justificada en la decisión de diseño.
- Registro mercantil y listas restrictivas son los frentes necesarios para habilitar; noticias y riesgo de categoría pueden quedar declarados sin cubrir sin impedir una recomendación distinta de habilitar. Si falta el riesgo de categoría, la regla de alto riesgo (#3) se sigue evaluando con la categoría del registro y la del analista.
- La procedencia y los conflictos entre fuentes (#5) y el contenido del escalamiento (#6) son tickets aparte; aquí solo se exige que la cobertura incompleta llegue al informe y al escalamiento.
- La interfaz de chat (#7) mostrará lo que este ticket declare; aquí basta con que el informe y los eventos del sistema lo contengan.
