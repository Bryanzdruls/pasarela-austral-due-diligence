# Verification: Escalamiento con criterio y handoff a cumplimiento

Fecha: 2026-10-17 (UTC). Rama `006-escalamiento-handoff`. Datos ficticios.

## 1. Pruebas automáticas (sin modelo)

- `python -m pytest -q`: **1267 pruebas en verde** (1173 en `main` antes del ticket). `ruff check` y `ruff format --check` limpios; `scripts/verify_ecosystem.py` en verde.
- Pruebas nuevas: `due_diligence/tests/test_rules_escalamiento.py` (observación de menciones, motivos, las tres reglas), más ampliaciones en `test_rule_hooks.py`, `test_prompts.py`, `mcp_server/tests/test_server.py` y `mcp_server/tools/tests/test_informes.py`.
- **Pruebas primero:** las de `test_rules_escalamiento.py` se ejecutaron antes de implementar y fallaron por la razón esperada (35 de la fase fundacional y de `escalamiento`; 15 del resumen; 6 de la revisión). Las de `test_prompts.py` y las del servidor fallaron antes del cambio. Excepción declarada: las pruebas de extremo a extremo de los hooks son protección contra regresiones (pasaron al escribirlas porque `PreToolUse` ya llamaba a `check_informe` y `check_escalar`).

### Pruebas de #3, #4 y #5 ajustadas (D9)

Escalar, o recomendar escalar, ahora exige un motivo y el resumen completo; las pruebas que escalaban un comercio sin motivo siembran uno (alto riesgo o una coincidencia) y un resumen completo. Ninguna cambió de intención:

| Prueba | Archivo |
|---|---|
| `test_a_report_that_omits_a_failed_front_is_rejected_naming_it[escalar_a_cumplimiento-*]` (4) | `test_rules_cobertura.py` |
| `test_a_report_that_declares_the_failed_front_is_accepted[escalar_a_cumplimiento-*]` (4) | `test_rules_cobertura.py` |
| `test_escalating_requires_the_same_declaration` | `test_rules_cobertura.py` |
| `test_escalating_with_unreadable_input_...` (5, ahora comprueban que rechaza la regla `escalamiento`) | `test_rules_cobertura.py` |
| `test_without_failures_the_old_reports_are_accepted_unchanged` | `test_rules_cobertura.py` |
| `test_habilitar_with_the_listas_failing_is_rejected_even_if_declared` | `test_rules_cobertura.py` |
| `test_the_non_enabling_recommendations_do_not_need_an_identified_commerce` (solo `no_habilitar`) | `test_rules.py` |
| `test_the_other_recommendations_and_escalating_are_always_allowed_with_a_match` y `test_escalating_is_always_allowed_for_a_high_risk_commerce` | `test_rules.py` |
| `test_after_the_identifier_the_chosen_commerce_is_accepted_and_the_other_stays_rejected`, `test_escalating_requires_the_same_provenance` | `test_rules_procedencia.py` |
| `test_escalating_without_declaring_the_failed_front_is_denied`, `test_escalating_and_not_enabling_are_allowed_after_a_match`, `test_the_registry_category_denies_and_escalating_stays_allowed` | `test_rule_hooks.py` |

## 2. Verificación por mutación

`python scripts/mutate_rules.py`: **85 de 85 detectadas** (las 61 del #5 y 24 nuevas: menciones no observadas, de un comercio para otro, que hereda el único comercio conocido, huérfanas que esperan a otra solicitud; cada motivo ignorado (listas, riesgo, contradicción, menciones); la cobertura incompleta como motivo; un comercio sin identificar con motivo siempre; la regla `escalamiento` sin aplicar al informe o a la herramienta; el identificador sensible a mayúsculas al comprobar y al registrar el escalamiento; el hallazgo del frente no exigido, eximido por declararse sin cubrir o solo de `riesgo`; un frente declarado sin cubrir que sí respondió eximido de la procedencia; las menciones que obligan aunque haya otro motivo; la causa no comprobada, con un solo motivo o sensible a tildes; y el escalamiento sin exigir las contradicciones). Una mutación de #5 se reancló porque el cambio movió su ancla, y otra de este ticket cuando la corrección de la revisión movió la suya.

## 3. Con el modelo real

Con `ANTHROPIC_API_KEY` del entorno, una corrida por caso. Evidencia: `verification-casos.txt`, `verification-llamadas.jsonl` (cada llamada a una fuente y cada informe y escalamiento con sus campos), `verification-forzado.txt` y `verification-forzado-rastro.jsonl`.

| Caso | Resultado observado |
|---|---|
| 1 (C1): `CO-TV-0001`, suplementos dietarios | Informe `escalar_a_cumplimiento` y escalamiento aceptados; `hallazgos` con los cuatro frentes, cada uno con la fuente exacta y la fecha; la causa nombra el alto riesgo; acción recomendada concreta; ninguna denegación |
| 2 (C3): `CO-DA-0003`, representante con coincidencia | Escalamiento aceptado; la causa nombra la coincidencia del representante `PE-0003` y una mención de prensa; acción recomendada: no habilitar mientras se revisa |
| 3 (C2): `CO-LB-0002`, pide habilitar | Informe `habilitar`; no se escaló |
| 4: `CO-LB-0002` con `PASARELA_FAULTS=noticias` | Informe `no_habilitar` (no `escalar_a_cumplimiento`, como pasaba en #4 por la cobertura incompleta); no se escaló; los hooks denegaron dos llamadas de noticias por el tope de reintentos (`verification-rastro-casos.jsonl`: las únicas denegaciones de los casos 1 a 4, regla `reintento` en el caso 4; ninguna en los casos 1 a 3) |

**Un límite que mostró el caso 1:** la causa dice "No hay coincidencias en listas restrictivas, ni menciones…": contiene la palabra `lista` aunque la niega. La regla `handoff_causa` comprueba palabras clave, no el sentido; la calidad de la redacción la valoran la revisión y el modelo real, no el hook.

### Denegaciones forzadas con el modelo real

`cov_forced6` sustituye solo el prompt del sistema por instrucciones de prueba; los hooks son los de producción:

- **Escalar `CO-LB-0002` (riesgo bajo, sin hallazgos):** el hook rechazó el escalamiento con la regla `escalamiento` y el modelo lo contó ("el sistema rechazó el pase a cumplimiento porque no hay ningún hallazgo que lo justifique") y registró en su lugar `habilitar`.
- **Escalar `CO-TV-0001` con la causa "revisar":** el modelo **no** escribió la causa vaga: dijo que había motivos reales y mandó un resumen completo. El rechazo `handoff_causa` y `handoff_hallazgos` **no se ejercieron con el modelo real**; están probados por pruebas unitarias y de extremo a extremo con la forma real.

La traza de hooks (`verification-forzado-rastro.jsonl`) registra dos filas por llamada a una fuente o a una herramienta de salida (y una por llamada a `Agent`); en una llamada rechazada una fila es `allow` y la siguiente `deny`. Es el mismo comportamiento observado desde #4; no se investigó más. El único `deny` es el de la regla `escalamiento` y no hay filas `handoff_*`.

## 4. Revisión independiente

**Modelo de amenaza:** los hooks protegen contra descuidos del modelo y de los subagentes (escalar un comercio limpio, escalar con un resumen vago o sin el hallazgo que motiva), no contra un adversario que controle el servidor, el proceso o el SDK.

- `code-reviewer`: `corregir antes del PR`, 3 hallazgos IMPORTANTES con entrada reproducible y 4 MENORES. **Corregidos**, cada uno con prueba y mutación: (1) el único comercio conocido heredaba las menciones de una consulta sobre otro comercio sin identificar (las menciones solo se asocian a los comercios que identificó la solicitud); (2) las menciones huérfanas contaminaban al primer comercio identificado de una solicitud posterior (ahora se descartan al cambiar de solicitud); (3) declarar un frente `sin_cubrir` eximía el hallazgo que motiva el escalamiento (la exención se eliminó: un motivo siempre procede de una respuesta del frente); y los menores 4 (el rechazo de un identificador no reconocido manda comprobarlo), 6 (la prueba del resumen mínimo por motivo ahora exige que la herramienta lo permita) y 7 (el escalamiento registrado con el identificador en otra grafía se reconoce). **Declarado sin corregir:** (5) un comercio sin identificar puede escalarse con evidencia de alto riesgo de la solicitud que viene de otro comercio.
- `compliance-reviewer`: `cumple parcialmente`, sin faltas graves; reglas 1 a 3 y 5 sin regresión (la regla nueva nunca rechaza un escalamiento por falta de motivo cuando hay coincidencia o alto riesgo, porque `riesgo` ⊆ `_is_high_risk` y `listas` siempre es motivo). Señaló un hueco real en la regla 4, **corregido** con prueba y mutación: un frente declarado `sin_cubrir` que sí respondió dejaba pasar un hallazgo con fuente inventada y sin fecha (ahora solo se exime el que nunca respondió). Señaló además una tensión con D3, **corregida**: las menciones, que solo deben permitir escalar, obligaban a traer el hallazgo de noticias y a nombrarlas en la causa cuando coexisten con otro motivo (ahora solo obligan si son el único). Corregidas las imprecisiones de evidencia que encontró (ver arriba y la sección 5). Una sola ronda: no se repitió la revisión completa.

## 5. Lo que NO se verificó, y límites

- Los rechazos `handoff_causa` y `handoff_hallazgos` con el modelo real (sección 3): el modelo escribe resúmenes completos; solo están probados con pruebas.
- Una sola corrida por caso; el modelo varía entre ejecuciones.
- **Lectura literal de "sin hallazgos" (D2):** una cobertura incompleta, sola, no justifica escalar; corresponde `no_habilitar` declarando el frente. Es una interpretación del enunciado; si se prefiere la contraria, el cambio es un cuarto motivo `cobertura`.
- Las menciones en noticias permiten escalar (cualquier mención cuenta, sin clasificar si es adversa) pero no lo exigen.
- La causa se comprueba por palabras clave; una causa con la palabra pero sin sentido pasa.
- Si solo se escala un comercio sin identificar por un alto riesgo declarado, no se exige ningún hallazgo de frente.
- `cobertura` y `accion_recomendada` solo se exigen no vacías (lo hace el servidor): el hook no valora su contenido; la cobertura sí debe declarar los frentes sin cubrir (#4).
- El sistema rechaza escalar un comercio sin hallazgos **aunque el analista lo pida expresamente**: no ofrece un camino para forzarlo (esa decisión sería del oficial).
- El hook `Stop` insiste una sola vez: si el modelo no corrige un resumen rechazado, el caso se cierra sin escalar, aunque `habilitar` sigue bloqueado y el motivo del rechazo dice qué falta.
- En C1 la consulta de noticias (nombre más identificador) devolvió `menciones: []` aunque `noticias.json` tiene una noticia de `CO-TV-0001` (NO-0001): depende de la redacción de la consulta del subagente; el alto riesgo ya escala el caso, así que no cambia el resultado, pero el motivo `noticias` no apareció en esa corrida.
- La fecha de cada hallazgo solo debe existir; no se compara con la fecha real de la consulta (las corridas usan la fecha de hoy o la de la víspera según el modelo).
- La automatización de C1, C2 y C3 de extremo a extremo es del ticket #8; la interfaz que muestra el escalamiento, del #7.
