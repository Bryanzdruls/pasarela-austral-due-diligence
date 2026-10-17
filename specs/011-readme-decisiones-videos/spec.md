# Feature Specification: README, DECISIONES.md, guion de video y zip de entrega

**Feature Branch**: `011-readme-decisiones-videos`

**Created**: 2026-10-17

**Status**: Draft

**Input**: User description: "Ticket #11 «README, DECISIONES.md y videos»: README (correr sistema y pruebas en menos de 5 minutos, enlace al Project y al video de funcionamiento); DECISIONES.md (máx. 2 páginas, mecanismo elegido por necesidad y por qué); video de funcionamiento (máx. 5 min) y preparación del zip (sin .env ni dependencias, máx. 50 MB)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Un evaluador clona el repositorio y lo pone a funcionar (Priority: P1)

Un evaluador recibe el repositorio, no conoce el proyecto y quiere comprobar que el sistema funciona y que las pruebas pasan. Abre el README, sigue los pasos y en menos de cinco minutos tiene la interfaz de chat en marcha y las pruebas ejecutadas. El README también le dice dónde está el backlog (GitHub Project) y dónde está el video de funcionamiento.

**Why this priority**: es un requisito explícito del enunciado (README con instrucciones para correr el sistema y los tests en menos de 5 minutos, enlace al Project y enlace al video) y es lo primero que ve un evaluador. Un sistema que no se puede arrancar no se puede evaluar.

**Independent Test**: en una copia limpia del repositorio, una persona que solo tiene el README ejecuta los pasos y mide el tiempo hasta ver el chat respondiendo y las pruebas en verde.

**Acceptance Scenarios**:

1. **Given** una copia limpia del repositorio y las herramientas previas instaladas, **When** se siguen los pasos del README en orden, **Then** las pruebas pasan y la interfaz de chat abre en el navegador, todo en menos de cinco minutos.
2. **Given** que la persona no tiene clave de acceso al modelo, **When** sigue el README, **Then** sabe de antemano qué puede hacer sin ella (las pruebas) y qué necesita para conversar con el sistema, y dónde se define sin escribirla en el repositorio.
3. **Given** el README, **When** la persona busca el backlog y el video, **Then** encuentra el enlace al GitHub Project y el enlace al video de funcionamiento, o un aviso claro y visible de que el video aún no está publicado.
4. **Given** el README, **When** la persona quiere ver los siete casos obligatorios, **Then** sabe cómo recorrerlos en la interfaz y cómo ejecutarlos sin modelo.

---

### User Story 2 - Un evaluador entiende qué se decidió y por qué (Priority: P1)

El evaluador abre DECISIONES.md y, en dos páginas como máximo, ve para cada una de las once necesidades del ecosistema de Claude Code qué mecanismo se eligió, por qué es el adecuado y qué alternativa se descartó. Cada decisión apunta al archivo real donde vive, de modo que puede comprobarla en el código.

**Why this priority**: es un entregable obligatorio y la base de la sustentación (35 % de la nota): lo que no se puede justificar no puntúa. Debe describir este código, no consejos generales.

**Independent Test**: contar las necesidades cubiertas (11 de 11), medir la extensión (dos páginas como máximo) y comprobar que cada ruta citada existe en el repositorio.

**Acceptance Scenarios**:

1. **Given** DECISIONES.md, **When** se revisa cada una de las once necesidades del enunciado, **Then** cada una tiene mecanismo, motivo y alternativa descartada.
2. **Given** DECISIONES.md, **When** se comprueba cada archivo o carpeta que menciona, **Then** todos existen en el repositorio.
3. **Given** DECISIONES.md, **When** se mide su extensión, **Then** no supera dos páginas.
4. **Given** una decisión de DECISIONES.md, **When** se contrasta con `docs/ECOSISTEMA.md` y con la investigación del ticket correspondiente, **Then** no se contradicen.

---

### User Story 3 - La persona verifica el zip antes de entregarlo (Priority: P1)

Antes de subir el zip a la plataforma de entrega, la persona ejecuta una verificación que le dice, sin ambigüedad, si el archivo cumple las reglas del enunciado: incluye el historial (la carpeta `.git`), no lleva dependencias instaladas, no supera 50 MB y no contiene ningún archivo de variables de entorno ni credencial. Un `.env` o una credencial dentro del zip es una falta grave que invalida la entrega.

**Why this priority**: el error es irreversible una vez entregado y la sanción es máxima. Una comprobación repetible y automática es la única forma fiable de evitarlo.

**Independent Test**: generar un zip de prueba con cada condición prohibida (un archivo de entorno, una credencial de muestra construida en el momento, un entorno virtual, un tamaño excesivo, sin historial) y comprobar que la verificación falla indicando cuál; con el zip real, que pasa.

**Acceptance Scenarios**:

1. **Given** el repositorio en su estado final, **When** se prepara el zip y se ejecuta la verificación, **Then** informa que cumple (tamaño, historial incluido, sin dependencias, sin secretos).
2. **Given** un zip que contiene un archivo de variables de entorno o algo con forma de credencial, **When** se verifica, **Then** falla, nombra el archivo y no repite el valor.
3. **Given** un zip sin la carpeta de historial, con un entorno virtual o mayor de 50 MB, **When** se verifica, **Then** falla indicando la causa exacta.
4. **Given** el archivo de plantilla de variables de entorno (solo con nombres, sin valores), **When** se verifica, **Then** se permite.

---

### User Story 4 - La persona graba el video de funcionamiento con un guion (Priority: P2)

La persona va a grabar un video de como máximo cinco minutos que muestre el sistema funcionando en su interfaz de chat y los siete casos de prueba obligatorios con su resultado. Dispone de un guion que le dice qué preparar, qué mensaje enviar en cada caso, qué debe verse en pantalla y cuánto tiempo dedicarle, de modo que el video cabe en el límite y no expone secretos.

**Why this priority**: el video es un entregable obligatorio, pero lo graba y publica la persona; el ticket solo puede dejarle el camino allanado. El enlace del video lo añade ella al README cuando exista.

**Independent Test**: sumar los tiempos del guion (no más de cinco minutos para los siete casos), comprobar que cada caso cita su mensaje y el resultado esperado, y ensayarlo una vez con el sistema real.

**Acceptance Scenarios**:

1. **Given** el guion, **When** se suman los tiempos previstos, **Then** los siete casos y la introducción caben en cinco minutos.
2. **Given** el guion, **When** la persona prepara la grabación, **Then** una lista previa le indica qué dejar listo (clave en el entorno, servidor en marcha, ventana limpia) y qué no mostrar (secretos).
3. **Given** el guion, **When** se ensaya con el sistema real, **Then** cada caso produce en pantalla el resultado que el guion anuncia.
4. **Given** que el video ya está publicado, **When** la persona pega su enlace, **Then** el README lo muestra y la verificación final lo reconoce.

---

### Edge Cases

- Falta la clave de acceso al modelo: el README lo explica antes de que falle y distingue lo que funciona sin ella (pruebas) de lo que no (el chat y la ejecución con el modelo real).
- La herramienta de instalación de dependencias no está en el `PATH` del equipo: los pasos usan una forma que funciona igualmente (se usó `python -m uv` en todo el proyecto).
- El equipo del evaluador no tiene Node: las pruebas que lo necesitan se saltan y el README lo dice, sin presentarlo como fallo.
- El puerto de la interfaz está ocupado: el README indica cómo cambiarlo.
- El enlace del video aún no existe: el README lo declara pendiente de forma visible, nunca con un enlace falso, y la verificación final lo detecta.
- El zip se genera sobre un árbol con archivos sin versionar (cachés, entornos virtuales, un archivo de entorno local): no deben acabar dentro.
- El tamaño del historial por sí solo supera el límite: la verificación lo informa con el tamaño de cada parte.
- DECISIONES.md crece más allá de dos páginas al añadir una decisión: la medición lo detecta.
- Una decisión se escribe de memoria y la ruta citada no existe o cambió: la comprobación de rutas lo detecta.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El repositorio MUST tener un README en su raíz que explique qué es el proyecto, qué necesita instalado quien lo clona, cómo arrancar la interfaz de chat, cómo ejecutar las pruebas y cómo recorrer los siete casos obligatorios.
- **FR-002**: Los pasos del README MUST poder completarse en menos de cinco minutos en una copia limpia, y esa medida MUST comprobarse ejecutándolos de verdad en una copia limpia y registrando el resultado.
- **FR-003**: El README MUST declarar qué requiere la clave de acceso al modelo, que se define como variable de entorno y nunca en el repositorio, y qué funciona sin ella.
- **FR-004**: El README MUST llevar el enlace al GitHub Project y el enlace al video de funcionamiento. Mientras el video no exista, MUST mostrar un aviso visible de pendiente y nunca un enlace inventado.
- **FR-005**: El README MUST incluir un mapa breve de dónde está cada pieza (sistema, servidor de fuentes, ecosistema de Claude Code, especificaciones, trazabilidad) y los límites conocidos, sin presentar como completo lo que no lo está.
- **FR-006**: El repositorio MUST tener un DECISIONES.md de dos páginas como máximo que cubra las once necesidades del ecosistema del enunciado, cada una con el mecanismo elegido, el porqué y la alternativa descartada.
- **FR-007**: Todo archivo o carpeta que mencionen el README y DECISIONES.md MUST existir en el repositorio, y esa comprobación MUST ser automática.
- **FR-008**: DECISIONES.md MUST describir las decisiones de este código y mantenerse coherente con `docs/ECOSISTEMA.md` y con la investigación de los tickets; no MUST contener recomendaciones genéricas.
- **FR-009**: MUST existir una verificación automática del archivo de entrega que compruebe: historial incluido, sin dependencias ni cachés, tamaño de 50 MB como máximo, ningún archivo de variables de entorno (la plantilla sin valores está permitida) y ninguna credencial; MUST fallar con un código distinto de cero y un mensaje que nombre la causa, sin repetir nunca el valor de una credencial.
- **FR-010**: La verificación del archivo de entrega MUST probarse con casos prohibidos construidos en el momento de la prueba (nunca valores literales) y con el archivo real.
- **FR-011**: MUST existir un guion del video de funcionamiento con una lista previa de preparación, el mensaje y el resultado esperado de cada uno de los siete casos, y el tiempo asignado a cada uno, con un total de cinco minutos como máximo.
- **FR-012**: El guion MUST indicar qué no mostrar en pantalla (variables de entorno, claves) y cómo reducir el riesgo de que el modelo varíe entre corridas.
- **FR-013**: Una verificación final MUST comprobar que el enlace del video del README es real (no el aviso de pendiente) y que el resto de los requisitos de entrega se cumplen, de modo que la persona sepa si puede entregar.
- **FR-014**: Todo lo nuevo MUST usar datos ficticios, no contener credenciales ni valores con forma de datos reales y pasar los hooks del proyecto.
- **FR-015**: `docs/TRAZABILIDAD.md` MUST actualizarse con lo que este ticket cierra (README, DECISIONES.md, preparación del zip y del video) y con lo que queda en manos de la persona.

### Key Entities *(include if feature involves data)*

- **README**: la puerta de entrada del repositorio para quien lo clona; contiene los pasos para correr, los enlaces y el mapa de piezas.
- **DECISIONES.md**: el registro breve de las decisiones del ecosistema, una por necesidad, con motivo y alternativa descartada.
- **Guion del video**: el orden, los mensajes, el resultado esperado y los tiempos de la grabación de funcionamiento.
- **Archivo de entrega**: el zip del repositorio completo con su historial, sin dependencias ni secretos, de tamaño acotado.
- **Verificación de entrega**: el comprobador que dice si el archivo de entrega y los documentos cumplen los requisitos antes de subirlos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una persona que parte de una copia limpia y solo tiene el README llega a ver la interfaz respondiendo y las pruebas en verde en menos de cinco minutos (medido y registrado una vez de punta a punta).
- **SC-002**: El 100 % de las rutas que citan el README y DECISIONES.md existen en el repositorio.
- **SC-003**: DECISIONES.md cubre 11 de 11 necesidades, cada una con mecanismo, motivo y alternativa, y no supera dos páginas.
- **SC-004**: La verificación del archivo de entrega detecta cada una de las cinco condiciones prohibidas (archivo de entorno, credencial, dependencias instaladas, tamaño excesivo y falta de historial) en el 100 % de los casos de prueba construidos.
- **SC-005**: El zip real que se entregue pasa la verificación: 0 archivos de entorno, 0 coincidencias de credenciales, 50 MB como máximo y con el historial incluido.
- **SC-006**: El guion del video suma cinco minutos como máximo para siete casos y la introducción, y cada caso del guion coincide con `docs/CASOS.md`.
- **SC-007**: Las pruebas existentes (1.528 al cierre del #7) siguen pasando sin modificarse.

## Assumptions

- Los destinatarios son los evaluadores de la prueba y la propia persona que entrega; el README se escribe en español, como el resto del proyecto.
- La persona graba y publica el video, sube el zip a la plataforma de entrega y añade a los evaluadores al repositorio; el ticket entrega el guion, las comprobaciones y los documentos, y no sustituye esas acciones.
- El video de defensa (hasta 15 minutos) y la revisión de autoría son de la persona y quedan fuera de este ticket.
- Las herramientas previas son Python 3.12 y la herramienta de dependencias del proyecto; Node es opcional y solo lo necesitan algunas pruebas de la página.
- El repositorio es privado y los evaluadores lo reciben por invitación o por el zip; el README no debe depender de ver el repositorio en línea para ser comprensible.
- Las decisiones ya están razonadas en `docs/ECOSISTEMA.md` y en los `research.md` de cada ticket; DECISIONES.md las condensa y no inventa otras nuevas.
- La verificación de credenciales usa los mismos patrones estrictos que el resto del proyecto (claves de Anthropic, tokens de GitHub, claves privadas).
