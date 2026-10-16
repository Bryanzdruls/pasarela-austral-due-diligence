# Feature Specification: Ecosistema de Claude Code del equipo

**Feature Branch**: `009-ecosistema-claude-code`

**Created**: 2026-10-16

**Status**: Draft

**Input**: Issue #9 de GitHub — "Ecosistema de Claude Code". Parametrizar Claude Code en el repositorio como lo haría un equipo profesional, antes de seguir con funcionalidad (constitución v1.1.0, principio VIII): convenciones compartidas, protecciones automáticas que impiden los errores graves, revisiones independientes y piezas verificables y justificables.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Las protecciones impiden los errores graves antes de que ocurran (Priority: P1)

Quien desarrolla con Claude Code no puede, ni por descuido ni por indicación del propio asistente, escribir código de un ticket sin su especificación, escribir datos con forma de documento, NIT o tarjeta reales, ni leer o modificar archivos de secretos y variables de entorno. Cada bloqueo explica el motivo y qué hacer.

**Why this priority**: Son las "faltas graves" del enunciado (credenciales, datos que parezcan reales) y la regla del proceso (spec primero). Deben existir antes de seguir construyendo.

**Independent Test**: Intentar, con entradas de prueba, cada una de las tres acciones prohibidas y comprobar que se bloquean con un mensaje claro; intentar las acciones permitidas equivalentes y comprobar que pasan.

**Acceptance Scenarios**:

1. **Given** una rama de ticket cuya carpeta de especificación no existe o está incompleta, **When** se intenta escribir código de producción, **Then** la escritura se bloquea indicando qué artefacto falta.
2. **Given** una rama de ticket con especificación, plan y tareas, **When** se escribe código de producción, **Then** la escritura se permite.
3. **Given** un texto con un número con forma de tarjeta real, de documento de identidad o de NIT reales, **When** se intenta escribirlo en cualquier archivo del repositorio, **Then** la escritura se bloquea indicando qué se detectó.
4. **Given** los identificadores ficticios del proyecto (`CO-XX-000N`, `FICT-000N`), **When** se escriben, **Then** no se bloquean.
5. **Given** un archivo de secretos o de variables de entorno, **When** se intenta leerlo o modificarlo, **Then** se bloquea; **Given** la plantilla de ejemplo sin valores, **Then** se permite leerla y modificarla.

---

### User Story 2 - Quien clona el repositorio recibe las convenciones sin configurar nada (Priority: P1)

Un desarrollador nuevo clona el repositorio y Claude Code ya conoce las convenciones del equipo: cómo se estructura el código, cómo se escriben los tests y dónde viven. Lo que es propio de cada persona no se comparte ni afecta a los demás.

**Why this priority**: Es la base de un ecosistema de equipo y lo primero que se revisa en la defensa.

**Independent Test**: En un clon limpio del repositorio, comprobar que las convenciones de equipo están cargadas y que los archivos personales están excluidos del control de versiones.

**Acceptance Scenarios**:

1. **Given** un clon limpio, **When** se abre Claude Code en el proyecto, **Then** las convenciones del equipo están disponibles sin ningún paso de configuración.
2. **Given** convenciones que solo aplican a una zona (por ejemplo, los tests o el servidor de fuentes), **When** se trabaja en esa zona, **Then** se aplican las convenciones específicas de esa zona y no las de otras.
3. **Given** preferencias personales de un desarrollador, **When** las guarda, **Then** quedan fuera del control de versiones y no afectan a sus compañeros.
4. **Given** tests repartidos en muchas carpetas, **When** se escribe o edita un test en cualquiera de ellas, **Then** se aplican las mismas convenciones de tests.

---

### User Story 3 - El código queda formateado tras cada edición (Priority: P1)

Después de cada edición de un archivo de código, el archivo queda formateado según el estilo del equipo sin que nadie lo pida.

**Why this priority**: Evita ruido en las revisiones y cumple una necesidad explícita del enunciado; es barato y se prueba fácilmente.

**Independent Test**: Editar un archivo con formato incorrecto y comprobar que queda formateado; editar un archivo que no es código y comprobar que no se toca.

**Acceptance Scenarios**:

1. **Given** una edición que deja un archivo de código mal formateado, **When** termina la edición, **Then** el archivo queda formateado.
2. **Given** una edición de un archivo que no es de código (documento, datos), **When** termina, **Then** no se modifica por formateo.
3. **Given** que la herramienta de formateo no está disponible, **When** se edita código, **Then** el desarrollador recibe un aviso claro y la edición no se pierde.

---

### User Story 4 - Revisión independiente y de cumplimiento antes del pull request (Priority: P2)

Antes de abrir un pull request, el código pasa por una revisión hecha por un agente independiente de la sesión que lo generó, que solo puede leer. Una revisión de cumplimiento, también independiente y de solo lectura, comprueba que las reglas de negocio de la pasarela están implementadas como se especificaron.

**Why this priority**: Cubre dos necesidades del enunciado y respalda la calidad, pero depende de que las protecciones y convenciones ya existan.

**Independent Test**: Verificar que los dos revisores existen, que sus herramientas se limitan a leer y que se pueden invocar de forma repetible mediante las piezas de flujo del equipo.

**Acceptance Scenarios**:

1. **Given** una rama lista para PR, **When** se lanza la revisión independiente, **Then** la hace un agente sin acceso a la conversación de desarrollo y sin poder editar archivos.
2. **Given** una rama con reglas de negocio implementadas, **When** se lanza la revisión de cumplimiento, **Then** devuelve, para cada regla, si está cumplida, parcial o ausente, con evidencia del código y de la especificación.
3. **Given** que la revisión de cumplimiento encuentra una regla de negocio que solo depende de instrucciones de un prompt, **When** informa, **Then** lo reporta como incumplimiento grave.
4. **Given** una rama lista para abrir el pull request con el comando del equipo, **When** se ejecuta, **Then** lanza las dos revisiones, no abre el pull request si alguna reporta un incumplimiento grave y deja ambos veredictos en la descripción.

---

### User Story 5 - Cada pieza se puede verificar y justificar (Priority: P2)

El equipo puede comprobar de forma automática que se cumplen los mínimos de configuración del enunciado, y cada pieza tiene su justificación (dónde vive, por qué ahí y qué alternativa se descartó) lista para la defensa.

**Why this priority**: La sustentación pesa más que cualquier otra área; una pieza que no se puede justificar pierde su puntaje.

**Independent Test**: Ejecutar la verificación automática de mínimos y comprobar que pasa; contar las piezas y las justificaciones y comprobar que coinciden.

**Acceptance Scenarios**:

1. **Given** el repositorio terminado, **When** se ejecuta la verificación de mínimos, **Then** confirma el número requerido de cada pieza y que se cumplen sus condiciones (alcance por ruta, herramientas restringidas, opciones de las skills, tipos de hook).
2. **Given** que falta una pieza o incumple una condición, **When** se ejecuta la verificación, **Then** falla indicando cuál.
3. **Given** una pieza del ecosistema, **When** se consulta su justificación, **Then** existe e indica ubicación, motivo y alternativa descartada.

---

### Edge Cases

- Rama sin ticket (por ejemplo, `main`): escribir código de producción se bloquea porque no hay especificación activa.
- Especificación presente pero sin plan o sin tareas: se bloquea la escritura de código de producción e indica qué falta.
- Editar documentos, especificaciones, configuración del ecosistema o datos ficticios no exige especificación previa.
- Un test que necesita un ejemplo de número con forma de tarjeta: lo construye en tiempo de ejecución, sin escribir el valor literal en ningún archivo.
- Un fallo del propio mecanismo de bloqueo (error al evaluar): el bloqueo falla de forma segura (se deniega) y explica el motivo, nunca permite por defecto.
- Rutas con barras de Windows o de Linux: los bloqueos y el formateo funcionan igual.
- Código escrito desde la terminal (redirecciones, `tee`, `Set-Content`, `Out-File`, `sed -i`, copiar o mover hacia una ruta de producción): se somete a las mismas comprobaciones que las herramientas de edición. Una orden que construya el nombre del archivo en tiempo de ejecución puede eludir la inspección del texto; es un límite conocido y documentado, no una garantía.
- Un archivo de secretos referenciado por una ruta relativa, absoluta o con mayúsculas distintas: se reconoce igualmente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El repositorio MUST entregar las convenciones del equipo a quien lo clone, sin pasos de configuración, mediante una memoria de proyecto con jerarquía (nivel proyecto y al menos una importación o un archivo por subdirectorio, con su justificación).
- **FR-002**: Las preferencias personales MUST quedar fuera del control de versiones y no afectar a otros desarrolladores.
- **FR-003**: MUST existir al menos dos reglas con alcance por ruta mediante patrones glob, una de ellas con las convenciones de los tests que viven junto al código en distintas carpetas.
- **FR-004**: Escribir código de producción —con las herramientas de edición o con una orden de terminal que escriba un archivo— MUST bloquearse cuando la feature activa no tenga especificación, plan y tareas en `specs/`, indicando qué falta.
- **FR-005**: Escribir en cualquier archivo del repositorio (con las herramientas de edición o con una orden de terminal) contenido con forma de número de tarjeta, de documento de identidad o de NIT reales MUST bloquearse, indicando qué se detectó; los identificadores ficticios del proyecto MUST NOT bloquearse.
- **FR-006**: Leer o modificar archivos de secretos y de variables de entorno MUST bloquearse; la plantilla de ejemplo sin valores MUST poder leerse y modificarse.
- **FR-007**: Tras cada edición de un archivo de código, el archivo MUST quedar formateado; los archivos que no son de código MUST NOT modificarse por formateo.
- **FR-008**: MUST existir una revisión independiente previa al pull request, a cargo de un agente de solo lectura sin acceso a la conversación de desarrollo.
- **FR-009**: MUST existir una revisión de cumplimiento, a cargo de un agente de solo lectura, que contraste cada regla de negocio de la pasarela con la especificación y el código, y que reporte como falta grave cualquier regla que dependa solo de instrucciones de un prompt.
- **FR-010**: MUST existir al menos dos skills que, entre todas, usen contexto aislado, herramientas permitidas restringidas y una indicación del argumento esperado.
- **FR-011**: MUST existir al menos un comando propio compartido mediante control de versiones.
- **FR-012**: Los dos servidores de fuentes (GitHub con el toolset de projects y el propio del escenario) MUST estar declarados en el proyecto sin credenciales.
- **FR-013**: Cada bloqueo MUST fallar de forma segura (denegar ante un error propio), explicar su motivo al desarrollador y poder verificarse con pruebas automáticas que no necesiten el modelo.
- **FR-014**: MUST existir una verificación automática de los mínimos del enunciado que falle indicando qué pieza falta o incumple.
- **FR-015**: Cada pieza MUST tener registrada su justificación: dónde vive, por qué ahí y qué alternativa se descartó.
- **FR-016**: Ningún archivo de configuración del ecosistema MUST contener credenciales ni datos con apariencia de reales.
- **FR-017**: El comando propio que abre el pull request MUST lanzar la revisión independiente y la revisión de cumplimiento antes de abrirlo, y dejar sus veredictos en la descripción del pull request.

### Key Entities *(include if feature involves data)*

- **Memoria de proyecto**: convenciones del equipo organizadas en jerarquía; se complementa con la memoria personal, que no se versiona.
- **Regla con alcance por ruta**: convención que solo se aplica cuando se trabaja en archivos que coinciden con un patrón.
- **Bloqueo**: comprobación automática previa a una acción que la permite o la deniega con un motivo.
- **Acción posterior a la edición**: comprobación o transformación automática que se ejecuta después de editar un archivo.
- **Agente revisor**: agente independiente de solo lectura con una misión de revisión (código o cumplimiento).
- **Skill**: capacidad reutilizable con contexto aislado, herramientas restringidas e indicación de argumento.
- **Justificación de pieza**: ubicación, motivo y alternativa descartada de cada pieza del ecosistema.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En un clon limpio, el número de pasos de configuración manual necesarios para que las convenciones del equipo estén activas es 0: la memoria de proyecto, las reglas y los hooks están versionados.
- **SC-002**: El 100 % de los intentos de escribir código de producción sin especificación, plan y tareas de la feature activa se bloquea, y el 100 % de las escrituras con los tres artefactos presentes se permite (matriz de pruebas con todas las combinaciones, tanto por las herramientas de edición como por órdenes de terminal con redirección).
- **SC-003**: El 100 % de los valores de muestra con forma de tarjeta, documento de identidad o NIT reales se bloquea, y el 0 % de los archivos ya versionados del proyecto (datos ficticios incluidos) se bloquea al reescribirse.
- **SC-004**: El 100 % de los intentos de leer o modificar los archivos de secretos y de variables de entorno de muestra se bloquea, y la plantilla de ejemplo sigue accesible.
- **SC-005**: Tras editar un archivo de código de muestra con formato incorrecto, el archivo pasa la comprobación de formato sin ninguna acción manual.
- **SC-006**: La verificación automática de mínimos pasa en el repositorio terminado y falla al eliminar cualquiera de las piezas requeridas (comprobado quitando cada una).
- **SC-007**: El número de piezas del ecosistema es igual al número de justificaciones registradas (cobertura del 100 %).
- **SC-008**: Una búsqueda de credenciales y de valores con apariencia de reales en los archivos de configuración del ecosistema devuelve 0 coincidencias.

## Assumptions

- Las capacidades de Claude Code que se usan (memoria de proyecto, reglas por ruta, agentes, skills, hooks, comandos y servidores de herramientas) son las que ofrece el producto; el plan concreta cómo se configura cada una.
- La feature activa se determina por el prefijo numérico de la rama (`NNN-…` → `specs/NNN-*`) y, si la rama no lo tiene, por el puntero de feature de Spec Kit; sin feature activa no hay especificación y se bloquea el código de producción. La rama va primero porque el puntero no se versiona y apunta a la última especificación creada, que puede no ser la del ticket actual.
- "Código de producción" es todo archivo de código del repositorio salvo los de pruebas, scripts de utilidad, configuración del ecosistema y entorno virtual (criterio por exclusión: un directorio de código nuevo queda protegido por defecto y no hay que acordarse de añadirlo a ninguna lista). Los documentos, las especificaciones y los datos no exigen especificación previa.
- Para cumplir las reglas de la constitución, la especificación previa significa tener especificación, plan y tareas de la feature.
- La verificación de formato usa el formateador que ya adopta el proyecto.
- El plugin reutilizable y la automatización del flujo de tickets del Project son el ticket #10, que se ejecuta inmediatamente después de este y **antes** de cualquier ticket de funcionalidad (constitución v1.1.1: el #9 se implementa antes que el plugin por ser configuración del entorno y porque el plugin empaqueta piezas que este crea; la excepción no se repite). El documento `DECISIONES.md` es el ticket #11 (aquí solo se registran las justificaciones como insumo).
- Los hooks del ecosistema de desarrollo (Claude Code) son distintos de los hooks del sistema multi-agente (Agent SDK, ticket #3) y no los sustituyen.
