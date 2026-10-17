# Feature Specification: Casos de prueba obligatorios automatizados

**Feature Branch**: `008-casos-obligatorios`

**Created**: 2026-10-17

**Status**: Draft

**Input**: Issue #8 de GitHub — "Casos de prueba obligatorios automatizados". Pruebas que pasan los 7 casos del enunciado: (1) Tienda Verde SAS (suplementos, alto riesgo) → oficial; (2) bajo riesgo sin hallazgos → habilitación; (3) representante legal con coincidencia en listas; (4) dos comercios con nombres casi idénticos; (5) consulta de listas sin identificación unívoca → bloqueada; (6) falla de noticias → informe con cobertura incompleta; (7) dos fuentes con fechas de constitución distintas.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cada caso obligatorio se ejecuta de extremo a extremo y pasa sin modelo ni clave (Priority: P1)

Quien revisa el repositorio puede ejecutar `pytest` y ver, uno por uno, los siete casos del enunciado: cada caso recorre los datos ficticios reales del servidor, los hooks de producción y el registro de los informes y escalamientos, y comprueba el resultado que el enunciado exige. La parte que decide el modelo (qué herramienta llamar) la reproduce un guion; todo lo demás es el código real del sistema.

**Why this priority**: El enunciado pide "casos de prueba que tu repositorio debe incluir y pasar". Hasta ahora estaban verificados a mano con el modelo real, sin pruebas que un evaluador pueda ejecutar.

**Independent Test**: `python -m pytest due_diligence/tests/test_casos_obligatorios.py` pasa sin `ANTHROPIC_API_KEY` y no llama al modelo; cada caso tiene su propia prueba con el nombre del caso.

**Acceptance Scenarios**:

1. **Given** Tienda Verde SAS (suplementos dietarios), **When** se recorre la investigación, **Then** `habilitar` se rechaza por alto riesgo, se permite recomendar y registrar el escalamiento, el escalamiento queda registrado con su resumen completo y la respuesta puede cerrarse.
2. **Given** un comercio de riesgo bajo sin hallazgos, **When** se recorre la investigación, **Then** `habilitar` se acepta y queda registrado, escalar se rechaza y la respuesta puede cerrarse sin escalar.
3. **Given** un representante legal con coincidencia en listas, **When** se recorre la investigación, **Then** `habilitar` se rechaza por la regla 2, se exige escalar antes de cerrar y el escalamiento registrado nombra la coincidencia.
4. **Given** dos comercios con nombres casi idénticos, **When** el registro devuelve ambos, **Then** no se identifica a ninguno, ni listas ni informe ni escalamiento se permiten a nombre de un candidato, y tras el identificador de uno la investigación sigue solo con él.
5. **Given** una consulta de listas sin identificación unívoca (sin registro previo y tras un resultado ambiguo), **When** se intenta, **Then** se bloquea con la regla 1 y no llega al servidor.
6. **Given** una falla de la fuente de noticias, **When** se registra el informe, **Then** se rechaza si no declara `noticias` sin cubrir, se acepta si lo declara con los demás hallazgos conservados, y el tope de reintentos se respeta.
7. **Given** dos fuentes con fechas de constitución distintas, **When** se registra el informe, **Then** se rechaza si presenta una sola fecha y se acepta si declara ambas con su origen.

---

### User Story 2 - Los casos pueden repetirse con el modelo real con un solo comando (Priority: P2)

Quien tiene una clave de la API puede ejecutar los mismos siete casos contra el sistema real, con el modelo de verdad, y ver cuáles pasan: el resultado se decide por lo que el sistema hizo (qué herramientas se llamaron, qué se registró, qué denegaron los hooks), no por el texto de la respuesta. Sin clave, el comando lo dice y no falla de forma confusa.

**Why this priority**: Las pruebas sin modelo demuestran que el código real hace lo correcto ante una conducta dada; la ejecución con el modelo demuestra que el modelo conduce el sistema a esa conducta. Son las dos mitades del criterio del enunciado.

**Independent Test**: El comando de la ejecución real, con clave, imprime una línea por caso (pasa o falla con el motivo) y un resumen; sin clave, termina con un mensaje claro y código distinto de cero.

**Acceptance Scenarios**:

1. **Given** una clave válida, **When** se ejecutan los casos con el modelo real, **Then** cada caso imprime su resultado y el motivo si falla, y se guarda un registro de las llamadas para revisarlo.
2. **Given** ninguna clave, **When** se ejecuta, **Then** termina diciendo qué falta, sin llamar al modelo.
3. **Given** un caso que falla, **When** se ejecuta de nuevo solo ese caso por su número, **Then** corre únicamente ese caso.

---

### User Story 3 - Los casos documentan el comportamiento y detectan romperlo (Priority: P2)

Cada caso explica en su prueba, en lenguaje llano, qué exige el enunciado y qué se comprueba; un documento resume los siete con el mensaje de ejemplo, lo esperado y dónde está la prueba. Y cada caso falla si se rompe a propósito la garantía que cubre.

**Why this priority**: Alguien que no conoce el código debe entender qué se prueba (criterio de la defensa) y las pruebas deben probar algo (principio de la constitución).

**Independent Test**: Quitar el hook de reglas o el de parada del sistema hace fallar varios casos.

**Acceptance Scenarios**:

1. **Given** el documento de los casos, **When** se abre, **Then** lista los siete con su mensaje, resultado esperado, prueba y cómo repetirlos con el modelo.
2. **Given** una mutación que desconecta el hook de reglas o el de parada, **When** se ejecutan las pruebas, **Then** fallan los casos que dependen de él.

---

### Edge Cases

- El caso 5 se prueba en las dos formas del enunciado: sin ningún registro previo y tras un resultado ambiguo.
- El caso 6 cubre la falla reintentable y la no reintentable.
- El caso 3 cubre también que, si el modelo no escala, la parada lo exige una vez.
- Un caso que dependa de datos ficticios del servidor (identificadores y nombres) usa los reales de `mcp_server/data/`, para detectar si alguien cambia los datos.
- La ejecución con el modelo no es determinista: un caso puede fallar por la conducta del modelo y no por el código; el resultado lo dice y permite repetirlo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El repositorio MUST incluir una prueba por cada uno de los siete casos del enunciado, ejecutable sin modelo y sin clave.
- **FR-002**: Cada prueba MUST recorrer los datos ficticios reales del servidor y las herramientas reales del servidor, con los hooks de producción cableados como en la aplicación, y reproducir con un guion solo la elección de herramientas que haría el modelo.
- **FR-003**: Cada prueba MUST comprobar el resultado que exige el enunciado: lo que se permite, lo que se rechaza con su regla, lo que queda registrado (informes y escalamientos) y si la respuesta puede cerrarse.
- **FR-004**: Los casos MUST incluir las dos formas del caso 5 (sin registro previo y tras un resultado ambiguo) y las dos fallas del caso 6 (reintentable y no reintentable).
- **FR-005**: Un comando MUST ejecutar los siete casos con el modelo real y decidir cada resultado por lo que el sistema hizo, no por el texto; sin clave MUST terminar con un mensaje claro y sin llamar al modelo.
- **FR-006**: El comando MUST poder ejecutar un solo caso por su número y guardar el registro de llamadas y denegaciones.
- **FR-007**: Un documento MUST resumir los siete casos: mensaje de ejemplo, resultado esperado, prueba y cómo repetirlos con el modelo.
- **FR-008**: Las pruebas MUST fallar si se desconecta el hook de reglas o el de parada, o si se rompen las garantías que cada caso cubre (comprobado con mutaciones).
- **FR-009**: Las pruebas MUST NOT llamar al modelo real ni exigir credenciales; los valores con forma de tarjeta, NIT o documento no se escriben como literales.
- **FR-010**: Esta función MUST NOT cambiar el comportamiento del sistema: añade pruebas, un comando y documentación.

### Key Entities *(include if feature involves data)*

- **Caso obligatorio**: uno de los siete del enunciado, con su mensaje de ejemplo, los datos que usa y el resultado exigido.
- **Guion**: la secuencia de llamadas a herramientas que representa lo que haría el modelo en un caso.
- **Resultado de una llamada**: si el hook la permitió, la regla y el motivo si la rechazó, y lo que devolvió el servidor si se ejecutó.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Los siete casos pasan con `pytest` sin clave ni red, en menos de un minuto en total.
- **SC-002**: Con una clave válida, el comando de la ejecución real termina con un resultado por caso; los casos que pasan se deciden por llamadas y registros, y los que fallan dicen el motivo.
- **SC-003**: Desconectar el hook de reglas o el de parada, o ignorar la inyección de fallas, hace fallar al menos un caso cada vez (3 de 3 mutaciones de sistema detectadas).
- **SC-004**: Las 1267 pruebas anteriores siguen pasando sin modificarse.
- **SC-005**: Una persona que no conoce el código entiende, leyendo `docs/CASOS.md`, qué prueba cada caso y cómo repetirlo.

## Assumptions

- El comportamiento de los siete casos ya existe (tickets #1 a #6); este ticket lo demuestra, no lo cambia. Por eso las pruebas de extremo a extremo pasan al escribirlas; su valor se comprueba con mutaciones.
- La parte que decide el modelo (qué herramienta llamar y con qué datos) se reproduce con un guion: es la única parte simulada. El texto de la respuesta al analista no se comprueba en las pruebas sin modelo.
- La ejecución con el modelo real necesita `ANTHROPIC_API_KEY` y puede variar entre corridas; sus resultados se registran en la verificación, y no son parte de `pytest`.
- La interfaz de chat es del ticket #7; los casos se ejecutan contra el coordinador y los hooks, no contra la interfaz.
