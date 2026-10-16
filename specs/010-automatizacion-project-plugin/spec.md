# Feature Specification: Automatización del GitHub Project y plugin reutilizable

**Feature Branch**: `010-automatizacion-project-plugin`

**Created**: 2026-10-16

**Status**: Draft

**Input**: Issue #10 de GitHub — "Automatización del GitHub Project y plugin reutilizable". (1) Un flujo que toma el siguiente ticket, lo mueve a In progress, abre el pull request (In review) y lo pasa a Done al fusionar, con comentarios de avance, vía el servidor MCP de GitHub con el toolset `projects`. (2) Un plugin que empaqueta un subagente, una skill y un hook reutilizables, instalable desde un marketplace. Cubre las necesidades 10 y 11 del enunciado.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tomar el siguiente ticket y arrancarlo sin pasos manuales (Priority: P1)

Quien desarrolla pide "el siguiente ticket" y el flujo lo elige del Project según el orden del backlog y las reglas del proyecto, lo marca como en progreso y entrega el contenido del issue como insumo de la especificación, sin que la persona tenga que mover tarjetas ni copiar texto.

**Why this priority**: El enunciado exige que el asistente lea y actualice el backlog "por sí mismo". Es el primer eslabón del ciclo y el que más se nota en la defensa. Sin él, el estado del Project depende de la memoria de quien trabaja.

**Independent Test**: Con un Project que tenga varios tickets en Todo, ejecutar el flujo y comprobar que el elegido es el que corresponde al orden, que pasó a In progress en el Project y que su contenido quedó disponible para especificar; repetirlo con un ticket ya en progreso y comprobar que no toma otro en silencio.

**Acceptance Scenarios**:

1. **Given** un Project con tickets en Todo, **When** se pide el siguiente ticket, **Then** se elige el primero según el orden definido (los tickets de configuración del entorno antes que los de funcionalidad, y por número dentro de cada grupo) y se indica cuál es y por qué.
2. **Given** el ticket elegido, **When** se arranca, **Then** su estado en el Project pasa a In progress y se muestra su título y contenido como insumo para la especificación.
3. **Given** que ya hay un ticket en In progress, **When** se pide el siguiente, **Then** el flujo lo informa y pide confirmación antes de tomar otro.
4. **Given** que no quedan tickets en Todo, **When** se pide el siguiente, **Then** se informa claramente que no hay trabajo pendiente y no se modifica nada.

---

### User Story 2 - El estado del ticket refleja el avance real hasta Done (Priority: P1)

Al terminar el trabajo de un ticket, el flujo abre el pull request que referencia y cierra el issue, deja el ticket en In review, publica en el issue un comentario de avance (qué se especificó, qué se decidió y qué quedó pendiente) y, una vez el pull request se fusiona, el ticket queda en Done sin que nadie lo mueva a mano.

**Why this priority**: Es la necesidad 10 del enunciado: el estado en GitHub sincronizado con el avance real, sin intervención manual. Quien evalúa debe poder reconstruir el avance solo mirando GitHub.

**Independent Test**: Abrir un pull request de prueba de un ticket y comprobar el cambio a In review y el comentario en el issue; fusionarlo y ejecutar el flujo de sincronización para comprobar que el ticket queda en Done; ejecutarlo de nuevo y comprobar que no cambia nada.

**Acceptance Scenarios**:

1. **Given** una rama de ticket lista, **When** se abre el pull request, **Then** su descripción referencia y cierra el issue y el ticket pasa a In review.
2. **Given** un ticket que pasa a In review, **When** se publica el avance, **Then** el issue recibe un comentario con tres partes: lo especificado, lo decidido y lo pendiente.
3. **Given** un pull request ya fusionado cuyo ticket sigue en In review, **When** se ejecuta la sincronización, **Then** el ticket pasa a Done.
4. **Given** un Project cuyo estado ya coincide con la realidad, **When** se ejecuta la sincronización, **Then** no se hace ningún cambio y se informa de que todo está al día.
5. **Given** tickets cuyo estado no coincide con el de sus pull requests (por ejemplo, fusionados pero aún en progreso), **When** se ejecuta la sincronización, **Then** se corrigen todos y se informa de cada cambio.

---

### User Story 3 - Otro equipo instala las piezas reutilizables en su repositorio (Priority: P2)

Un equipo de la pasarela que no tiene este repositorio añade un catálogo de plugins, instala el plugin y obtiene un subagente de revisión, una skill y un hook que funcionan en su propio repositorio sin copiar archivos a mano.

**Why this priority**: Es la necesidad 11 y un mínimo del ecosistema (peso del 25 % de la evaluación). Depende menos del resto: puede entregarse y defenderse por separado.

**Independent Test**: En un repositorio vacío distinto de este, registrar el catálogo, instalar el plugin y comprobar que aparecen el subagente, la skill y el hook y que cada uno funciona; desinstalarlo y comprobar que desaparecen.

**Acceptance Scenarios**:

1. **Given** un repositorio ajeno, **When** se registra el catálogo y se instala el plugin, **Then** quedan disponibles al menos un subagente, una skill y un hook del plugin.
2. **Given** el plugin instalado, **When** se usa su skill y su subagente, **Then** funcionan sin depender de rutas ni archivos propios de este repositorio.
3. **Given** el plugin instalado, **When** el hook detecta la acción que protege, **Then** la bloquea con un mensaje claro, igual que en este repositorio.
4. **Given** el contenido del plugin y del catálogo, **When** se revisa, **Then** no contiene credenciales ni datos con apariencia de reales.
5. **Given** el plugin instalado, **When** se desinstala, **Then** sus piezas dejan de estar disponibles y no queda configuración residual.

---

### User Story 4 - Se sabe dónde vive cada pieza y por qué (Priority: P3)

Quien revisa el repositorio, o prepara la defensa, encuentra documentado para la automatización y para el plugin dónde vive cada pieza, qué necesidad resuelve y qué alternativa se descartó, y la verificación automática del ecosistema comprueba que existen.

**Why this priority**: La defensa vale el 35 % y exige justificar cada mecanismo. Es documentación y comprobación sobre lo anterior, de bajo coste.

**Independent Test**: Ejecutar la verificación automática del ecosistema y comprobar que reconoce la automatización y el plugin; quitar una de las piezas y comprobar que la verificación falla nombrándola.

**Acceptance Scenarios**:

1. **Given** el inventario del ecosistema, **When** se revisa, **Then** incluye una fila por cada pieza nueva con su necesidad, su ubicación, el porqué y la alternativa descartada.
2. **Given** el plugin o la automatización incompletos, **When** se ejecuta la verificación, **Then** falla indicando qué falta.
3. **Given** la trazabilidad contra el enunciado, **When** se actualiza al cerrar el ticket, **Then** las necesidades 10 y 11 y el mínimo del plugin reflejan su estado real con evidencia.

---

### Edge Cases

- El servidor de GitHub no está conectado o no tiene habilitado el toolset de projects: el flujo falla de forma visible, explica qué falta y no hace cambios parciales ni finge haberlos hecho.
- Un issue no está en el Project: se informa y no se inventa una tarjeta sin confirmación.
- Dos tickets en progreso a la vez: se informa y se pide decidir cuál continúa.
- Un pull request cerrado sin fusionar: el ticket no pasa a Done; se informa y se deja el estado como está.
- Un pull request que no referencia ningún issue: el flujo lo señala antes de abrirlo.
- Una fusión hecha fuera del flujo (a mano en GitHub): la sincronización la detecta igualmente.
- El ticket tomado está bloqueado por otro que aún no se fusionó (por ejemplo, un ticket de funcionalidad mientras la configuración del entorno sigue abierta): el flujo lo advierte y propone el correcto.
- El plugin se instala en un repositorio sin las carpetas esperadas: sus piezas siguen funcionando o fallan con un mensaje claro.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El flujo MUST poder elegir el siguiente ticket del Project aplicando un orden explícito y documentado, e indicar cuál elige y por qué.
- **FR-002**: Al arrancar un ticket el flujo MUST pasarlo a In progress en el Project y MUST entregar el título y el contenido del issue como insumo de la especificación.
- **FR-003**: El flujo MUST advertir y pedir confirmación si ya hay un ticket en progreso o si el elegido depende de otro aún abierto.
- **FR-004**: Al abrir el pull request el flujo MUST asegurar que referencia y cierra su issue y MUST pasar el ticket a In review.
- **FR-005**: El flujo MUST publicar en el issue un comentario de avance con tres partes: lo especificado, lo decidido y lo pendiente, a partir de la información real de la rama (especificación, tareas, verificación).
- **FR-006**: El flujo MUST disponer de una sincronización que compare el estado de cada ticket con el de su pull request y MUST pasar a Done los tickets cuyo pull request está fusionado.
- **FR-007**: La sincronización MUST ser repetible: ejecutarla varias veces sin cambios en la realidad no produce modificaciones, y cada cambio realizado se informa.
- **FR-008**: Toda lectura y escritura del backlog MUST hacerse a través del servidor oficial de GitHub con el toolset de projects, no con la interfaz web ni con comandos manuales.
- **FR-009**: Si el servidor o el toolset no están disponibles, el flujo MUST detenerse con un mensaje que diga qué falta y MUST NOT modificar nada.
- **FR-010**: Ningún paso del flujo MUST requerir que la persona mueva tarjetas ni edite el estado a mano; las acciones que afectan a terceros (abrir el pull request, comentar, cambiar estados) se muestran antes de ejecutarse o están autorizadas de forma expresa y duradera por la persona.
- **FR-011**: El plugin MUST empaquetar al menos un subagente de solo lectura, una skill y un hook, todos reutilizables en un repositorio ajeno.
- **FR-012**: El plugin MUST poder instalarse desde un catálogo (marketplace) publicado en este repositorio, y MUST poder desinstalarse sin dejar residuos.
- **FR-013**: Las piezas del plugin MUST NOT depender de rutas, archivos o datos propios de este repositorio, ni contener credenciales ni datos con apariencia de reales.
- **FR-014**: El plugin y el catálogo MUST incluir instrucciones de instalación y de uso verificables por una persona ajena al proyecto.
- **FR-015**: La verificación automática del ecosistema MUST comprobar que existen el plugin (con subagente, skill y hook), el catálogo y la automatización del flujo, y MUST fallar nombrando la pieza que falte.
- **FR-016**: El inventario del ecosistema MUST documentar cada pieza nueva con su necesidad, su ubicación, por qué vive ahí y la alternativa descartada, incluidas las limitaciones conocidas.
- **FR-017**: La trazabilidad contra el enunciado MUST actualizarse al cerrar el ticket con el estado real y la evidencia de las necesidades 10 y 11 y del mínimo del plugin.

### Key Entities

- **Ticket**: unidad de trabajo del backlog. Tiene número, título, contenido, estado (Todo, In progress, In review, Done), orden y, si existe, un pull request asociado.
- **Estado del ticket**: posición del ticket en el ciclo. Cambia solo por las transiciones definidas: arrancar (a In progress), abrir el pull request (a In review) y fusionar (a Done).
- **Comentario de avance**: mensaje en el issue con lo especificado, lo decidido y lo pendiente.
- **Plugin**: paquete reutilizable con un subagente, una skill y un hook, con su versión y sus instrucciones.
- **Catálogo (marketplace)**: lista de plugins instalables, publicada en el repositorio.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En un Project con tickets en cada estado, tras ejecutar el ciclo completo de un ticket (arrancar, abrir el pull request, fusionar, sincronizar), el estado del ticket coincide con la realidad en el 100 % de las transiciones sin que nadie lo mueva a mano.
- **SC-002**: Quien evalúa puede reconstruir el avance de un ticket (cuándo empezó, qué se especificó, decidió y quedó pendiente, cuándo se revisó y cuándo se cerró) solo mirando el Project, el issue y el pull request.
- **SC-003**: Ejecutar la sincronización dos veces seguidas sin cambios en la realidad produce cero modificaciones la segunda vez.
- **SC-004**: Un equipo ajeno instala el plugin desde cero y tiene el subagente, la skill y el hook funcionando en menos de 5 minutos siguiendo solo las instrucciones.
- **SC-005**: El 100 % de las veces que el servidor o el toolset no están disponibles, el flujo se detiene sin modificar el Project y dice qué falta.
- **SC-006**: Quitar cualquiera de las piezas requeridas (plugin, subagente, skill, hook, catálogo o automatización) hace fallar la verificación del ecosistema nombrando la pieza.
- **SC-007**: 0 credenciales y 0 datos con apariencia de reales en el plugin, el catálogo y la configuración del flujo.

## Assumptions

- La fusión del pull request la hace una persona en GitHub; la transición a Done se registra al ejecutar la sincronización (al tomar el siguiente ticket o bajo demanda), no en el instante de la fusión. Si se quisiera inmediatez, habría que añadir un disparador del lado de GitHub, fuera del alcance de este ticket.
- El orden de los tickets es: los de configuración del entorno de Claude Code antes que los de funcionalidad (principio VIII de la constitución), y por número dentro de cada grupo.
- El Project existente (nº 4) tiene el campo de estado con las opciones Todo, In progress, In review y Done, y el servidor de GitHub se configuró con el toolset de projects en el ticket #9.
- Reutilizar piezas del ticket #9 para el plugin está permitido por el enunciado: el subagente de cumplimiento, la skill de revisión de cumplimiento y uno de los hooks.
- El catálogo se publica en este mismo repositorio; no hace falta un repositorio aparte.
- Los hooks del plugin son una barrera contra descuidos del asistente, no contra ofuscación deliberada (mismo modelo de amenaza que el ticket #9).
- La interfaz de instalación del plugin y el formato del catálogo son los que ofrece Claude Code en esta versión.
- Los datos y nombres de ejemplo son ficticios; el plugin no incluye datos reales de ningún comercio.
- Fuera de alcance: crear tickets nuevos, reordenar el backlog, y automatizar la fusión de los pull requests.
