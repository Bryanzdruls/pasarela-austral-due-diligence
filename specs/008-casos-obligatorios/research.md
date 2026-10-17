# Research: Casos de prueba obligatorios automatizados

Cada decisión lleva su alternativa descartada: alimentan `DECISIONES.md`.

## D1. Pruebas sin modelo con un guion y todo lo demás real
- **Decisión**: el arnés ejecuta un guion de llamadas a herramientas con las piezas reales: hooks de `build_options(book)`, funciones reales de `mcp_server/tools` con sus datos e inyección de fallas, y archivos reales en un directorio temporal. Solo se simula qué herramienta llama el modelo.
- **Por qué**: la convención del proyecto es que ninguna prueba llama al modelo real (no es determinista, cuesta dinero y exige credencial). Y lo que el enunciado exige de los siete casos (bloquear, escalar, registrar, declarar cobertura, mostrar conflictos) lo decide el código, no el modelo.
- **Alternativas descartadas**: (a) llamar al modelo real en `pytest`: contradice la convención y un evaluador sin clave no podría ejecutarlas; (b) probar solo las reglas puras (`CaseBook`): ya existe y no demuestra el cableado de producción ni el servidor.

## D2. El cableado de producción se toma de `build_options`
Los hooks se obtienen de `build_options(book).hooks` y se ejecutan en el orden del SDK (`tool_guard` y luego las reglas). Así, si alguien desconecta un hook de `options.py`, los casos fallan. Se comprueba con mutaciones de sistema (D5).

## D3. La ejecución real decide por llamadas, no por texto
- **Decisión**: `casos_reales.py` corre cada caso con el coordinador real, observa las llamadas y las denegaciones con hooks de observación añadidos a los de producción (como las verificaciones de #3 a #6) y evalúa invariantes: qué herramientas se llamaron, qué se registró, qué regla denegó.
- **Por qué**: el texto de la respuesta varía; las llamadas y los registros son lo que el enunciado exige ("el coordinador escala", "el informe declara la cobertura").
- **Alternativas descartadas**: (a) comprobar frases de la respuesta: frágil; (b) un segundo modelo que juzgue: no determinista y más caro.
- **Límite declarado**: un caso puede fallar por la conducta del modelo y no por el código; el resultado lo dice y el comando permite repetir un solo caso.

## D4. Los casos usan los datos reales del servidor
Identificadores y nombres salen de `mcp_server/data/`: si alguien los cambia, los casos fallan. No se duplican datos en las pruebas.

## D5. Las pruebas pasan al escribirlas; su valor se prueba con mutaciones
El comportamiento ya existe (#1 a #6), así que las pruebas de extremo a extremo pasan al escribirlas. Para demostrar que prueban algo se añaden mutaciones de sistema: desconectar el hook de reglas, el de parada o la inyección de fallas debe hacer fallar casos concretos. Es la misma práctica que en #5 y #6 con las pruebas de extremo a extremo de los hooks.

## D6. Los casos del enunciado y sus datos

| Caso | Mensaje de ejemplo | Datos | Lo que se exige |
|---|---|---|---|
| 1 | "Tienda Verde SAS, suplementos dietarios" | `CO-TV-0001` | no se habilita; se escala con resumen completo |
| 2 | "Libros del Faro SAS" | `CO-LB-0002` | se habilita; no se escala |
| 3 | "Distribuidora Andina Ficticia SAS" | `CO-DA-0003`, representante `PE-0003` en listas | no se habilita; se escala |
| 4 | "Cafetería Aurora" | `CO-CA-0004` y `CO-CA-0005` | se pide el identificador; no se elige |
| 5 | listas sin registro previo, y tras un resultado ambiguo | cualquiera | bloqueada por la regla 1 |
| 6 | `PASARELA_FAULTS=noticias` | `CO-LB-0002` | informe con `noticias` sin cubrir |
| 7 | "Ferretería Horizonte SAS" | `CO-FH-0006` | ambas fechas con su origen |
