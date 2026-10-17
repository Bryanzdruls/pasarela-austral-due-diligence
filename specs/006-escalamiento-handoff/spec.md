# Feature Specification: Escalamiento con criterio y handoff a cumplimiento

**Feature Branch**: `006-escalamiento-handoff`

**Created**: 2026-10-16

**Status**: Draft

**Input**: Issue #6 de GitHub — "Escalamiento y handoff a cumplimiento". Escalar cuando hay coincidencia en listas o categoría de alto riesgo; no escalar bajo riesgo sin hallazgos. Criterio: resumen estructurado con comercio, hallazgos por frente con fuentes, cobertura, causa del escalamiento y acción recomendada; el oficial no tiene la conversación. (Enunciado, comportamientos 10 y 11.)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Se escala cuando hay un motivo y no se escala sin él (Priority: P1)

El sistema pasa un caso a un oficial de cumplimiento solo cuando hay un hallazgo que lo justifica: una coincidencia en listas restrictivas (del comercio o de su representante legal), una categoría de alto riesgo, una contradicción entre fuentes o menciones en noticias. Un comercio de riesgo bajo sin hallazgos no se escala: se habilita. Lo mismo vale para recomendar `escalar_a_cumplimiento` en el informe, que es escalar.

**Why this priority**: Es el comportamiento 10 del enunciado ("escala cuando hay coincidencia en listas y cuando la categoría es de alto riesgo; no escala comercios de bajo riesgo sin hallazgos") y el caso de prueba C2. Con el modelo real se observó el defecto contrario: un comercio de riesgo bajo, sin ningún hallazgo, se escaló solo porque una fuente falló.

**Independent Test**: Para cada motivo (coincidencia del comercio, coincidencia del representante, alto riesgo, contradicción, menciones en noticias) comprobar que escalar se permite; para un comercio de riesgo bajo sin hallazgos, con y sin frentes sin cubrir, que escalar y recomendar escalar se rechazan con un motivo claro y que habilitar sigue permitido.

**Acceptance Scenarios**:

1. **Given** una coincidencia en listas del comercio o de su representante legal, **When** se escala, **Then** se permite.
2. **Given** un comercio de alto riesgo, **When** se escala, **Then** se permite.
3. **Given** una contradicción entre fuentes del comercio o menciones en noticias, **When** se escala, **Then** se permite (el motivo es un hallazgo).
4. **Given** un comercio de riesgo bajo, sin coincidencias, contradicciones ni menciones, **When** se intenta escalar o registrar un informe con la recomendación `escalar_a_cumplimiento`, **Then** se rechaza y el motivo dice que no hay hallazgo que lo justifique y que corresponde habilitar o no habilitar.
5. **Given** un comercio de riesgo bajo sin hallazgos y con un frente sin cubrir, **When** se intenta escalar, **Then** se rechaza: la falta de cobertura no es un hallazgo; se registra `no_habilitar` declarando el frente sin cubrir.
6. **Given** un comercio de riesgo bajo sin hallazgos y con la cobertura completa, **When** se registra el informe con `habilitar`, **Then** se acepta y no se pide escalar.
7. **Given** una categoría de alto riesgo declarada por el analista y un comercio que no se pudo identificar, **When** se escala, **Then** se permite: el alto riesgo declarado es un motivo aunque falte el registro.
8. **Given** un comercio de riesgo bajo, sin hallazgos y sin identificar, **When** se intenta escalar, **Then** se rechaza.

---

### User Story 2 - El resumen al oficial se basta solo (Priority: P1)

El oficial de cumplimiento no tiene la conversación. El escalamiento incluye el comercio, los hallazgos por frente con su fuente (en particular el hallazgo del frente que motiva el escalamiento), la cobertura alcanzada, la causa y la acción recomendada, y si las fuentes se contradicen, todos los valores con su origen. Un escalamiento al que le falta algo de esto se rechaza diciendo qué falta.

**Why this priority**: Es el comportamiento 11 del enunciado ("handoff útil"). Hasta ahora el servidor solo comprobaba que los campos existieran y que cada frente trajera una fuente: un escalamiento con la causa "revisar" o sin el hallazgo de las listas cuando el motivo eran las listas pasaba.

**Independent Test**: Para cada motivo, escalar (a) con un resumen completo, (b) sin el hallazgo del frente que lo motiva, (c) con una causa que no nombra el motivo, (d) con una contradicción sin declarar; comprobar que solo (a) se acepta y que las demás se rechazan con el motivo.

**Acceptance Scenarios**:

1. **Given** una coincidencia en listas, **When** se escala con el hallazgo de listas (con su fuente), la cobertura, una causa que nombra la coincidencia y una acción recomendada, **Then** se acepta.
2. **Given** una coincidencia en listas, **When** el resumen no trae el hallazgo del frente de listas, **Then** se rechaza nombrando el frente.
3. **Given** un alto riesgo, **When** la causa no menciona el riesgo, **Then** se rechaza y el motivo dice qué debe nombrar la causa.
4. **Given** varios motivos a la vez (coincidencia y alto riesgo), **When** la causa nombra solo uno, **Then** se rechaza pidiendo el otro.
5. **Given** una contradicción entre fuentes del comercio, **When** el escalamiento no la declara con todos los valores y su origen, **Then** se rechaza.
6. **Given** un resumen completo, **When** la acción recomendada o la cobertura faltan, **Then** se rechaza (como hoy) y el motivo lo dice.

---

### User Story 3 - Lo que ya funcionaba sigue funcionando (Priority: P2)

Un caso con coincidencia en listas o alto riesgo sigue exigiendo el escalamiento antes de cerrar la respuesta (una sola vez), `habilitar` sigue rechazado en esos casos, y los casos de las reglas 1 a 5 se comportan como antes.

**Why this priority**: Protege lo ya fusionado (#3, #4 y #5) de regresiones de este ticket.

**Independent Test**: Repetir las pruebas de las reglas 1 a 5 sin modificarlas, salvo los ajustes justificados por el criterio nuevo.

**Acceptance Scenarios**:

1. **Given** una coincidencia en listas sin escalar, **When** el sistema intenta cerrar la respuesta, **Then** se le exige escalar una sola vez, como antes.
2. **Given** un escalamiento con motivo y resumen completo, **When** se registra, **Then** se acepta sin otras condiciones.

---

### Edge Cases

- Un comercio con coincidencia en listas pero cobertura incompleta de noticias: se escala (hay motivo) declarando el frente sin cubrir.
- Un comercio con varios motivos: la causa los nombra todos y el resumen trae el hallazgo de cada frente que los motiva.
- Una coincidencia en listas solo del representante legal: el hallazgo de listas debe dejar claro que es del representante; el sistema exige el frente de listas, no el texto.
- Un escalamiento ya registrado para el comercio: otro intento no se rechaza por esta regla (no se impide escalar de nuevo si el motivo existe).
- El analista pide expresamente escalar un comercio sin hallazgos: el sistema lo rechaza con el motivo; la decisión de forzarlo es del oficial y no de este sistema.
- Un comercio de riesgo bajo con menciones en noticias que no son adversas: cuenta como hallazgo (se permite escalar, no se obliga): el sistema no clasifica el contenido de las noticias.
- El informe del comercio con `escalar_a_cumplimiento` y sin escalamiento posterior: se sigue exigiendo escalar antes de cerrar solo si hay motivo (regla 2 o 3), como hoy.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST permitir escalar un caso solo si el comercio tiene al menos un motivo: coincidencia en listas del comercio o del representante legal, categoría de alto riesgo, contradicción entre fuentes o menciones en noticias.
- **FR-002**: El sistema MUST aplicar el mismo criterio a un informe con la recomendación `escalar_a_cumplimiento`.
- **FR-003**: Una cobertura incompleta MUST NOT ser por sí sola un motivo para escalar.
- **FR-004**: Para un comercio sin identificar, el único motivo admitido MUST ser el alto riesgo declarado por el analista en la solicitud.
- **FR-005**: El resumen al oficial MUST incluir el hallazgo, con su fuente, de cada frente que motiva el escalamiento: listas para una coincidencia, riesgo o registro para un alto riesgo, noticias para las menciones.
- **FR-006**: La causa del escalamiento MUST nombrar cada motivo que existe: una causa que no menciona uno de ellos se rechaza diciendo cuál.
- **FR-007**: Si el comercio tiene una contradicción entre fuentes, el escalamiento MUST declararla con todos los valores y su origen, igual que el informe.
- **FR-008**: La acción recomendada y la cobertura MUST seguir siendo obligatorias, y la cobertura MUST declarar los frentes sin cubrir (#4).
- **FR-009**: Cada rechazo MUST decir qué falta o por qué no corresponde escalar y qué hacer.
- **FR-010**: Estas comprobaciones MUST aplicarse de forma determinista, fuera del prompt, y fallar cerrado.
- **FR-011**: Un caso con motivo y resumen completo MUST aceptarse; el hook de parada que exige escalar una sola vez ante una coincidencia o un alto riesgo MUST seguir igual; `habilitar` MUST seguir permitido para un riesgo bajo sin hallazgos y con las listas y el registro cubiertos.
- **FR-012**: El prompt del coordinador MUST describir el criterio de escalamiento y el contenido del resumen, recordando que el oficial no tiene la conversación; esta orientación no sustituye a las comprobaciones.

### Key Entities *(include if feature involves data)*

- **Motivo de escalamiento**: un hallazgo que justifica pasar el caso a un oficial: coincidencia en listas, alto riesgo, contradicción entre fuentes, menciones en noticias.
- **Resumen al oficial (handoff)**: el escalamiento registrado: comercio, hallazgos por frente con fuente y fecha, cobertura, conflictos, causa y acción recomendada.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100 % de los intentos de escalar, o de recomendar escalar, un comercio de riesgo bajo sin hallazgos se rechazan, con y sin frentes sin cubrir; el 100 % de los de un comercio con motivo se aceptan si el resumen está completo.
- **SC-002**: El 100 % de los resúmenes que omiten el hallazgo del frente que motiva el escalamiento, o cuya causa no nombra un motivo existente, o que no declaran una contradicción del comercio, se rechazan.
- **SC-003**: En la verificación con el modelo real, C1 (alto riesgo) y C3 (coincidencia del representante) terminan con un escalamiento completo y C2 (riesgo bajo sin hallazgos) con `habilitar` y sin escalar.
- **SC-004**: Las pruebas existentes de las reglas 1 a 5 siguen pasando; solo se ajustan las que escalaban o recomendaban escalar sin motivo, y cada ajuste queda justificado.
- **SC-005**: Cada comprobación de esta función tiene una prueba que se vio fallar antes de implementarla y una mutación que la rompe a propósito y es detectada.

## Assumptions

- "Hallazgo" se interpreta como un dato que justifica revisión humana: coincidencia en listas, alto riesgo, contradicción entre fuentes o menciones en noticias. El sistema no clasifica el contenido de las noticias; una mención permite escalar, no lo obliga.
- Una cobertura incompleta sin otros hallazgos no justifica escalar (el enunciado dice "no escala comercios de bajo riesgo sin hallazgos"): corresponde `no_habilitar` declarando el frente sin cubrir. Es una lectura literal del enunciado, declarada como decisión en el plan.
- El alto riesgo, la coincidencia en listas, las contradicciones y las menciones se toman de lo que las fuentes devolvieron y de la solicitud del analista, como en #3 a #5.
- La causa se comprueba por la presencia de palabras clave de cada motivo (p. ej. "lista", "riesgo"); no se valora su calidad redactada. La calidad del resumen la verifica la revisión y el modelo real.
- La interfaz que muestra el escalamiento es del ticket #7 y la automatización de C1, C2 y C3 de extremo a extremo, del #8.
