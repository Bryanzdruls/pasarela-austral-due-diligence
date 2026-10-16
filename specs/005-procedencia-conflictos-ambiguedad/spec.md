# Feature Specification: Procedencia, conflictos entre fuentes y ambigüedad

**Feature Branch**: `005-procedencia-conflictos-ambiguedad`

**Created**: 2026-10-16

**Status**: Draft

**Input**: Issue #5 de GitHub — "Procedencia, conflictos entre fuentes y ambigüedad". (1) Cada afirmación del informe enlazada a su fuente. (2) Datos contradictorios se muestran juntos con su origen, sin elegir uno (regla 4 del enunciado). (3) Varios comercios con nombre parecido: el coordinador pide el identificador en lugar de elegir.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cada afirmación del informe lleva la fuente que de verdad respondió (Priority: P1)

Quien lee un informe (el analista, y después un oficial de cumplimiento que no vio la conversación) puede comprobar de dónde sale cada dato: cada hallazgo del informe indica su fuente y la fecha de consulta, y esa fuente es una que realmente respondió durante la conversación. Un informe que atribuye un dato a una fuente que no se consultó, o que da un hallazgo sin fuente, no se registra.

**Why this priority**: Es la regla 4 del enunciado ("cada afirmación con su fuente") y la base de confianza del informe. Hoy el servidor ya devuelve fuente y fecha en cada respuesta y exige que el hallazgo de cada frente traiga una fuente, pero nada comprueba que esa fuente sea cierta: el modelo podría citar una fuente que no consultó.

**Independent Test**: Registrar informes cuyos hallazgos citan (a) la fuente que respondió, (b) una fuente que no se consultó, (c) la fuente de otro frente, (d) ninguna fuente; comprobar que solo (a) se acepta y que las demás se rechazan nombrando el frente y la fuente que sí consta.

**Acceptance Scenarios**:

1. **Given** que el registro mercantil respondió, **When** se registra un informe cuyo hallazgo de registro cita la fuente del registro y la fecha de su consulta, **Then** se acepta.
2. **Given** un frente que nunca se consultó con éxito, **When** se registra un informe con un hallazgo de ese frente que cita una fuente, **Then** se rechaza: no hay respuesta de esa fuente en la conversación.
3. **Given** un hallazgo que cita una fuente distinta de la que respondió para ese frente (p. ej. la de listas en el frente de noticias), **When** se registra el informe, **Then** se rechaza y el motivo indica la fuente que sí respondió.
4. **Given** un hallazgo sin fuente, **When** se registra el informe, **Then** se rechaza (como hoy) y el motivo lo dice.
5. **Given** un frente que falló y se declaró sin cubrir (#4), **When** se registra el informe sin hallazgo de ese frente, **Then** no se exige fuente para él.
6. **Given** un informe aceptado, **When** el analista lee la respuesta del coordinador, **Then** cada dato aparece junto a su fuente y la fecha de consulta.

---

### User Story 2 - Los datos contradictorios se muestran juntos, con su origen, sin elegir uno (Priority: P1)

Cuando dos fuentes dan valores distintos para el mismo dato de un comercio (el caso del enunciado: dos fechas de constitución), el informe y la respuesta muestran **todos** los valores con la fuente de cada uno, y no eligen uno. Si el servidor señaló una contradicción en lo que devolvió, el informe que se registra debe declararla con todos los valores y sus orígenes; un informe que presenta un único valor no se registra.

**Why this priority**: Es la regla 4 del enunciado y el caso de prueba obligatorio C7 ("dos fuentes con fechas de constitución distintas"). Un informe que elige una fecha entrega al oficial un dato falso con apariencia de certeza.

**Independent Test**: Con un comercio cuyo registro devuelve dos fechas de constitución de dos fuentes, registrar un informe (a) que declara el conflicto con las dos fechas y sus fuentes, (b) que da una sola fecha, (c) que declara el conflicto pero omite uno de los valores; comprobar que solo (a) se acepta; y con un comercio sin conflicto, que el informe de siempre se acepta.

**Acceptance Scenarios**:

1. **Given** un registro que devolvió dos fechas de constitución de dos fuentes distintas, **When** se registra un informe que declara el conflicto con ambas fechas y el origen de cada una, **Then** se acepta.
2. **Given** el mismo registro, **When** se registra un informe que presenta una sola fecha o que no declara el conflicto, **Then** se rechaza y el motivo nombra el dato en conflicto y los valores que faltan.
3. **Given** un conflicto declarado que omite uno de los valores o su origen, **When** se registra el informe, **Then** se rechaza.
4. **Given** un comercio sin contradicciones, **When** se registra el informe, **Then** no se exige ningún conflicto y se acepta como antes.
5. **Given** un conflicto sobre un comercio, **When** se investiga después a otro comercio sin conflicto, **Then** el conflicto del primero no se exige en el informe del segundo.
6. **Given** un conflicto en un informe aceptado, **When** el analista lee la respuesta del coordinador, **Then** ve ambos valores con su origen y ninguna frase que presente uno como el correcto.

---

### User Story 3 - Varios comercios con nombre parecido: se pide el identificador, no se elige (Priority: P1)

Cuando el registro mercantil devuelve varios comercios que coinciden con el nombre (caso del enunciado: dos "Cafetería Aurora" casi idénticas), el coordinador muestra los candidatos con lo que los distingue y pide al analista el identificador del que se investiga, en lugar de elegir uno. Mientras no haya un comercio identificado de forma unívoca, el sistema no registra ni escala un informe a nombre de uno de los candidatos ni atribuye datos de un candidato al comercio buscado.

**Why this priority**: Es el caso de prueba obligatorio C4 y evita el error más caro: investigar y habilitar al comercio equivocado. Las reglas 1 a 3 ya impiden consultar listas o habilitar sin identificación unívoca (#3), pero nada impide que un informe se registre a nombre de un candidato elegido por el modelo.

**Independent Test**: Con la consulta de un nombre que coincide con dos comercios, comprobar que el sistema muestra los dos candidatos y pide el identificador; que un informe o escalamiento a nombre de cualquiera de los dos se rechaza; y que, cuando el analista da el identificador de uno, la investigación continúa solo con ese comercio.

**Acceptance Scenarios**:

1. **Given** un nombre que coincide con dos comercios, **When** el coordinador responde, **Then** lista ambos candidatos con su identificador y lo que los distingue, y pide el identificador sin lanzar más frentes sobre ninguno.
2. **Given** un resultado ambiguo del registro, **When** se intenta registrar un informe o escalar a nombre de uno de los candidatos, **Then** se rechaza y el motivo dice que hay que pedir el identificador al analista.
3. **Given** un resultado ambiguo, **When** el analista responde con el identificador de uno de los candidatos, **Then** el registro lo identifica de forma unívoca y la investigación sigue solo con ese comercio, sin datos del otro.
4. **Given** un nombre que coincide con un solo comercio, **When** se investiga, **Then** no se pide identificador y todo sigue como antes.
5. **Given** un resultado ambiguo y la respuesta del analista con un identificador que no corresponde a ningún candidato, **When** el coordinador lo procesa, **Then** vuelve a pedir un identificador válido y no elige por su cuenta.

---

### Edge Cases

- Los dos valores en conflicto coinciden en realidad (la misma fecha en dos fuentes): no hay conflicto y no se exige declararlo.
- Más de dos fuentes con valores distintos para el mismo dato: se muestran todos.
- Una fuente cuyo hallazgo se omite por haber fallado (#4): la procedencia no se exige para lo que no hay.
- Una contradicción que solo aparece entre dos frentes distintos (p. ej. una noticia que contradice el registro): el servidor no la señala; la declara el coordinador por orientación del prompt y se verifica con el modelo real, sin garantía de hook (declarado).
- Un nombre parecido que no coincide por palabras completas con ningún comercio: no es ambiguo, es "no encontrado" y se trata como tal (comportamiento del servidor de fuentes, #1; este ticket no lo cambia).
- El analista da el identificador de un comercio que no estaba entre los candidatos: se consulta el registro y se identifica o no por sí mismo.
- Una pregunta de seguimiento sobre un dato en conflicto: se responde con ambos valores y sus orígenes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Cada hallazgo de un informe registrado MUST indicar su fuente y la fecha de su consulta.
- **FR-002**: El sistema MUST rechazar un informe cuyo hallazgo de un frente cite una fuente que no respondió en la conversación para ese frente, nombrando el frente y la fuente que sí consta.
- **FR-003**: El sistema MUST NOT exigir fuente para un frente declarado sin cubrir (#4) ni para uno sin hallazgo.
- **FR-004**: Cuando una fuente devuelve valores contradictorios para un mismo dato de un comercio, el sistema MUST llevar la cuenta de cada contradicción con todos sus valores y el origen de cada uno.
- **FR-005**: El sistema MUST rechazar el informe de un comercio con una contradicción señalada que no la declare en `conflictos` con todos los valores y el origen de cada uno, y el motivo MUST nombrar el dato y lo que falta.
- **FR-006**: Un informe sin contradicciones señaladas MUST aceptarse sin exigir conflictos, y el conflicto de un comercio MUST NOT exigirse en el informe de otro.
- **FR-007**: El sistema MUST NOT elegir un valor entre los contradictorios: ni el informe ni la respuesta pueden presentar uno como el correcto.
- **FR-008**: Cuando el registro devuelve varios comercios que coinciden, el coordinador MUST mostrar los candidatos con su identificador y lo que los distingue, y pedir el identificador al analista sin lanzar más frentes sobre ninguno.
- **FR-009**: Mientras un comercio candidato de un resultado ambiguo no haya sido identificado de forma unívoca, el sistema MUST rechazar registrar un informe o escalar a su nombre, con un motivo que mande pedir el identificador.
- **FR-010**: Cuando el analista da el identificador de un candidato y el registro lo identifica de forma unívoca, la investigación MUST continuar solo con ese comercio, sin datos de los otros candidatos.
- **FR-011**: Estas comprobaciones MUST aplicarse de forma determinista, fuera del prompt, y fallar cerrado, salvo la presentación de la respuesta al analista (FR-007 en el texto), que se orienta por prompt y se verifica con el modelo real.
- **FR-012**: Esta función MUST NOT alterar las reglas 1 a 3 ni la cobertura del #4: los informes y escalamientos que ya se aceptaban sin contradicciones ni ambigüedad se siguen aceptando.

### Key Entities *(include if feature involves data)*

- **Afirmación con fuente**: un hallazgo del informe con el frente al que pertenece, la fuente que respondió y la fecha de la consulta.
- **Contradicción**: un dato de un comercio sobre el que dos o más fuentes dan valores distintos; lleva el nombre del dato y la lista de pares (valor, fuente).
- **Conflicto declarado**: la entrada del informe que reproduce una contradicción con todos sus valores y su origen.
- **Candidato ambiguo**: cada comercio que coincide con un nombre cuando el registro devuelve varios; no está identificado hasta que el analista da su identificador.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100 % de los informes que atribuyen un hallazgo a una fuente que no respondió, o a la de otro frente, se rechazan nombrando el frente; el 100 % de los que citan la fuente real se aceptan.
- **SC-002**: En el caso de las dos fechas de constitución distintas, el 100 % de los informes que dan una sola fecha o que omiten una de las fuentes se rechazan, y el que declara ambas con su origen se acepta.
- **SC-003**: En el caso de los dos comercios de nombre casi idéntico, el 100 % de los informes y escalamientos a nombre de un candidato sin identificar se rechazan, y tras el identificador del analista la investigación sigue solo con ese comercio.
- **SC-004**: En la verificación con el modelo real, los casos C4 (nombres casi idénticos) y C7 (fechas distintas) terminan con una respuesta que pide el identificador, o que muestra ambas fechas con su origen, respectivamente, sin elegir.
- **SC-005**: Las pruebas existentes de las reglas 1 a 3, de la cobertura y del coordinador siguen pasando; solo se ajustan las que registraban informes con fuentes sin consulta previa, y cada ajuste queda justificado.
- **SC-006**: Cada comprobación de esta función tiene una prueba que se vio fallar antes de implementarla y una mutación que la rompe a propósito y es detectada.

## Assumptions

- El servidor de fuentes ya devuelve en cada respuesta su fuente y su fecha, todas las coincidencias de un nombre ambiguo con `ambiguous: true`, y las fechas de constitución contradictorias con su origen y una marca de `conflicts` (#1); este ticket no cambia el servidor.
- Solo la contradicción que el servidor señala se garantiza por hook. Una contradicción entre frentes distintos (p. ej. una noticia frente al registro) la orienta el prompt y se verifica con el modelo real, y así se declara.
- La fuente que un hallazgo debe citar para cada frente es la que el servidor reportó en los metadatos de su respuesta en la conversación; no se valida el contenido de cada afirmación, solo que su fuente sea real.
- Un hallazgo cuyo frente se declaró sin cubrir (#4) no se vuelve a exigir con fuente.
- El criterio de qué escalar y el contenido del resumen para el oficial son del ticket #6; la interfaz de chat que muestra las fuentes y los conflictos es del #7; la automatización de C4 y C7 de extremo a extremo es del #8.
