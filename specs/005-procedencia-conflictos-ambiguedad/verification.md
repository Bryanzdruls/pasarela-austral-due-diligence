# Verification: Procedencia, conflictos entre fuentes y ambigüedad

Fecha: 2026-10-16. Rama `005-procedencia-conflictos-ambiguedad`. Datos ficticios.

## 1. Pruebas automáticas (sin modelo)

- `python -m pytest -q`: **1170 pruebas en verde** (1021 en `main` antes del ticket). `ruff check` y `ruff format --check` limpios; `scripts/verify_ecosystem.py` en verde.
- Pruebas nuevas: `due_diligence/tests/test_rules_procedencia.py` (observación de fuentes, contradicciones y candidatos; las tres reglas), más ampliaciones en `test_rule_hooks.py`, `test_prompts.py` y `mcp_server/tests/test_server.py`.
- **Pruebas primero:** las de `test_rules_procedencia.py` se ejecutaron antes de implementar y fallaron por la razón esperada (49 fallos de la fase fundacional y de `conflicto`; después 35 de `ambiguedad` y `procedencia`; después 10 de la revisión). Las de `test_prompts.py` y la de la descripción del servidor fallaron antes del cambio. Excepción declarada: las pruebas de extremo a extremo de los hooks (`test_rule_hooks.py`) son protección contra regresiones; pasaron al escribirlas porque `PreToolUse` ya llamaba a `check_informe` y `check_escalar`, y no cuentan como "vistas fallar".
- **Ajustes de pruebas del #3 y del #4: ninguno.** D10 preveía pocos y no hizo falta ninguno: las pruebas existentes usan `hallazgos` vacíos, así que las reglas nuevas no los tocan.

## 2. Verificación por mutación

`python scripts/mutate_rules.py`: **60 de 60 detectadas** (las 39 del #4 y 21 nuevas: fuentes no observadas, fuente no respondida aceptada, fuente de otro frente, fecha no exigida, fuente ilegible, frente declarado sin cubrir no eximido, todo frente eximido, contradicciones no registradas, un valor ignorado, la fuente de un valor ignorada, informe sin conflictos aceptado, conflicto de un comercio exigido en otro, `dato` sin normalizar, candidatos no registrados, candidato identificado que sigue bloqueado, candidatos que no persisten, ambigüedad solo para `habilitar`, escalamiento sin ambigüedad ni procedencia, clave del hallazgo solo con el nombre exacto, identificador sensible a mayúsculas).

Una mutación sobrevivió en la primera pasada ("no se exige una fuente legible"): el mensaje era lo único que cambiaba; la prueba ahora comprueba que el motivo dice `legible`. La mutación de #4 sobre `check_escalar` se reancló porque el cambio movió su ancla.

## 3. Con el modelo real

Con `ANTHROPIC_API_KEY` del entorno, una corrida por caso. Evidencia: `verification-casos.txt` (transcripciones), `verification-llamadas.jsonl` (cada llamada a una fuente y cada informe con sus `hallazgos` y `conflictos`), `verification-forzado.txt` y `verification-forzado-rastro.jsonl`.

| Caso | Resultado observado |
|---|---|
| 1 (C7): `CO-FH-0006`, dos fechas | El informe registrado declara `conflictos` con `2016-03-14` (`registro_mercantil_ficticio`) y `2017-03-14` (`camara_comercio_alterna_ficticia`); los cuatro hallazgos traen la fuente exacta y la fecha; ninguna denegación |
| 2 (C4): "Cafetería Aurora" | El registro devolvió dos comercios; el coordinador mostró una tabla de candidatos (identificador, razón social, NIT, estado, fecha) y pidió el identificador; no consultó listas ni riesgo ni registró informe. Las noticias ya se habían lanzado en paralelo con el registro, antes de saber que era ambiguo (inevitable con frentes paralelos) |
| 3: tras el caso 2, "CO-CA-0004" | El registro lo identificó por su identificador y la investigación siguió solo con ese comercio; informe `habilitar` con los cuatro hallazgos con fuente y fecha |
| 3b: un identificador que no es de ningún candidato (`CO-ZZ-9999`) | El coordinador dijo que no es ninguno de los dos, volvió a listar los candidatos y a pedir uno válido; no lanzó consultas nuevas ni registró nada |
| 7: `CO-LB-0002` sin fallas | Informe `habilitar` con fuente y fecha por hallazgo; ninguna denegación |

**Denegaciones antes de la primera aceptación (A9 del análisis):** cero en los cuatro casos normales; el modelo cita las fuentes con sus nombres exactos (el prompt los lista) y las fechas.

### Denegaciones forzadas con el modelo real

`cov_forced5` y `cov_forced5b` sustituyen solo el prompt del sistema por instrucciones de prueba; los hooks son los de producción.

- **Primera pasada** (procedencia, conflicto, ambigüedad): se vieron **`vocabulario` ×2** (el modelo usó una recomendación fuera del vocabulario) y **`procedencia` ×1 sobre `escalar_a_cumplimiento`**; el modelo corrigió y el escalamiento se registró. En los casos de `conflicto` y `ambiguedad` el modelo **no obedeció** la orden de violar la regla: registró el informe con el conflicto declarado en un caso, y en el otro pidió el identificador.
- **Segunda pasada** (instrucciones reforzadas para `conflicto` y `ambiguedad`): el modelo **se negó** a registrar un informe con una sola fecha ("dejaría un registro de cumplimiento falso") y a elegir un candidato ("todavía no registré el informe"). El hook no tuvo que actuar.

**Conclusión honesta:** con el modelo real **solo se vio denegar a los hooks la procedencia (una vez)**; las denegaciones `conflicto` y `ambiguedad` están probadas por pruebas unitarias y de extremo a extremo de los hooks con la forma real de la entrada, pero **no se ejercieron con el modelo real** porque el modelo no las violó ni siquiera con instrucciones explícitas.

## 4. Revisión independiente

**Modelo de amenaza:** los hooks protegen contra descuidos del modelo y de los subagentes (citar una fuente que no consultó, dar una sola de dos fechas, registrar un informe a nombre de uno de dos comercios parecidos), no contra un adversario que controle el servidor, el proceso o el SDK.

- `code-reviewer`: `corregir antes del PR`, 1 hallazgo IMPORTANTE con entrada reproducible y 5 MENORES. **Corregido:** el importante (la procedencia se omitía si la clave del hallazgo no era exactamente un frente: `registro mercantil`, `registro-mercantil`, `Registro Mercantil`…; ahora `front_of_alias` normaliza separadores y reconoce el frente por la primera palabra de la clave, lo que además arregla la lectura de `cobertura` del #4) y el menor 3 (el identificador del candidato distinguía mayúsculas), cada uno con prueba y mutación. **Declarados sin corregir** (MENORES, sin riesgo con los datos del servidor): (2) un candidato con el registro caído después no puede tener informe parcial; (4) y (6) una entrada de `fuentes_registro` sin `source`, o la marca `conflicts` sin `fuentes_registro`, borra el conflicto en silencio; (5) la coincidencia de fuente es por subcadena (`registro_mercantil_ficticio_inventado` pasa).
- `compliance-reviewer`: ver la sección siguiente.

## 5. Lo que NO se verificó, y límites

- Las denegaciones `conflicto` y `ambiguedad` con el modelo real (sección 3).
- Una sola corrida por caso; el modelo varía entre ejecuciones.
- Las fuentes respondidas son de toda la conversación y no por comercio: un comercio podría citar un origen que consultó otro (D1).
- Las contradicciones entre frentes distintos (una noticia frente al registro) no las señala el servidor: solo por prompt, sin garantía de hook.
- Que el coordinador muestre los candidatos y no elija entre valores, y que su respuesta presente ambos valores, solo se orienta por prompt (se observó bien en los casos 1, 2 y 3b).
- El escalamiento no lleva `conflictos` (ticket #6).
- Si dos candidatos se identifican por nombre (no por identificador), el informe a nombre del nombre y no del identificador no se bloquea por `ambiguedad`.
