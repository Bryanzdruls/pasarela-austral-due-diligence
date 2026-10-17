# Verification: Casos de prueba obligatorios automatizados

Fecha: 2026-10-17 (UTC). Rama `008-casos-obligatorios`. Datos ficticios.

## 1. Pruebas automáticas (sin modelo ni clave)

- `python -m pytest -q`: **1341 pruebas en verde** (1267 en `main` antes del ticket). `ruff check` y `ruff format --check` limpios; `scripts/verify_ecosystem.py` en verde.
- **Los siete casos** (`due_diligence/tests/test_casos_obligatorios.py`): 10 pruebas (el caso 5 en tres formas, el caso 6 con falla reintentable y no reintentable), en menos de dos segundos y sin clave. Cada una recorre los datos reales de `mcp_server/data/`, las herramientas reales del servidor y los hooks de producción (`build_options`); solo el guion de llamadas reproduce lo que haría el modelo.
- **Arnés** (`tests/escenario.py`, `test_escenario.py`, 11 pruebas): comprueba que se comporta como el SDK (hooks en orden, `tool_response` como texto JSON, aislamiento por rol, registros guardados, fallas inyectadas y escenarios independientes).
- **Comprobaciones de la ejecución real** (`test_casos_reales.py`, 53 pruebas) y **documento** (`scripts/tests/test_casos_doc.py`, 4 pruebas).
- **Pruebas primero:** el arnés y las comprobaciones reales se escribieron antes de implementarlos (el arnés falló por ImportError; las comprobaciones, que se escribieron antes del módulo, no se ejecutaron antes de crearlo; las pruebas añadidas por la revisión y por el caso 5 sí se vieron fallar). Los siete casos **pasaron al escribirlos** porque el comportamiento ya existe (#1 a #6): su valor se demuestra con las mutaciones de sistema (sección 2). Ninguna prueba anterior se modificó (SC-004).

## 2. Verificación por mutación

`python scripts/mutate_rules.py`: **89 de 89 detectadas** (las 85 de #6 y 4 de sistema). Las 4 nuevas rompen el cableado de producción y las detectan **solo los casos obligatorios** (se ejecutan solo `test_casos_obligatorios.py`): desconectar el hook de reglas (`PreToolUse`) de `options.py`, desconectar el hook de parada, no observar los resultados (`PostToolUse`) e ignorar la inyección de fallas del servidor.

## 3. Con el modelo real (`python scripts/run_casos.py`)

Con `ANTHROPIC_API_KEY` del entorno, una corrida de los siete casos. Evidencia: `verification-casos-reales.txt` (salida del comando), `verification-llamadas.jsonl` (cada herramienta ejecutada con su turno y el resumen de denegaciones) y `verification-conversaciones.txt`.

| Caso | Resultado | Lo que se observó |
|---|---|---|
| 1 | PASA | Escalamiento de `CO-TV-0001` registrado (informe `escalar_a_cumplimiento` y escalamiento), sin ningún informe `habilitar`; la causa nombra el alto riesgo |
| 2 | PASA | Informe `habilitar` de `CO-LB-0002`; ningún escalamiento |
| 3 | PASA | Escalamiento de `CO-DA-0003` con una causa que nombra la coincidencia en listas; ningún `habilitar` |
| 4 | PASA | Turno 1: el registro devolvió dos comercios y no se ejecutó ni listas, ni informe, ni escalamiento; turno 2 (`CO-CA-0004`): investigación solo de ese comercio e informe `habilitar` a su nombre |
| 5 | **FALLA** en la primera corrida; **PASA** tras corregir la comprobación | Ver abajo |
| 6 | PASA | `PASARELA_FAULTS=noticias`: dos llamadas a noticias (un reintento), informe `no_habilitar` que declara `noticias` sin cubrir; no se escaló |
| 7 | PASA | El modelo escaló `CO-FH-0006` (la contradicción es un motivo válido) y el escalamiento declara ambas fechas con su origen |

**Un error de mi comprobación, no del sistema (caso 5):** el modelo se negó a saltarse el registro ("no puedo consultar las listas restrictivas de CO-TV-0001 sin pasar antes por el registro mercantil") y no ejecutó ninguna herramienta. Mi comprobación exigía que hubiera investigación y lo marcó como fallo, aunque es el resultado que el enunciado pide ("bloqueada"). Se corrigió (con pruebas que se vieron fallar): en el caso 5, no ejecutar ninguna herramienta es válido; solo falla una consulta de listas sin identificación previa. Repetido solo ese caso con `--caso 5`: pasa (el modelo se volvió a negar).

**Límite que esto muestra:** con el modelo real el hook de la regla 1 **no llegó a ejercerse** en el caso 5 (el modelo no lo intentó; `denegaciones: []`). Que el sistema lo bloquea se prueba sin modelo (`test_case_5_*`, con el arnés) y con el modelo real en #3, donde un prompt de prueba le ordenaba violarla (`specs/003-hooks-reglas-negocio/verification-forzado.txt`). Tampoco se ejerció ninguna denegación en los otros seis casos (`denegaciones: []` en todos): un modelo que respeta el flujo no recibe ninguna.

Una corrida por caso (más la repetición del 5). El modelo varía entre corridas; el comando permite repetir un caso.

## 4. Revisión independiente

**Modelo de amenaza:** son pruebas y un comando; deben detectar si se rompe el sistema y no dar falsos aprobados. No protegen contra un adversario que controle el servidor, el proceso o el SDK.

- `code-reviewer`: `aprobar`, sin bloqueantes ni importantes y 6 menores. **Corregidos:** (3) una clave de API vacía contaba como presente; (4) el caso 7 fallaba si el modelo escalaba en vez de registrar un informe, y los casos 1, 2 y 3 comparaban el identificador sin la normalización de los hooks; (2) la lectura de la respuesta de las herramientas ignoraba formas que las reglas sí aceptan (ahora reutiliza `parse_envelope`); (1) y (5) la redacción del documento, del módulo y del contrato decía que las denegaciones deciden el resultado, y no lo hacen: ahora se anotan como dato informativo; el contrato refleja los campos reales. Cada corrección de comportamiento lleva su prueba.
- `compliance-reviewer`: ver la sección siguiente.

## 5. Lo que NO se verificó, y límites

- Las denegaciones con el modelo real (sección 3): en ninguno de los siete casos el modelo tocó un hook.
- Una sola corrida por caso; la conducta del modelo varía y un caso puede fallar por ella y no por el código.
- Lo único simulado en `pytest` es la elección de herramientas del modelo; el texto de la respuesta al analista no se comprueba ni en `pytest` ni con el modelo.
- Los casos usan los datos de `mcp_server/data/`: si se cambian, fallan (es intencional).
- El caso 7 con el modelo real pasó por la vía del escalamiento (la contradicción es motivo de escalar, #6); la vía del informe `no_habilitar` está en la prueba sin modelo.
- La interfaz de chat (ticket #7) no se ejerce: los casos corren contra el coordinador y los hooks.
