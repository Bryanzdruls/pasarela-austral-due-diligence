# Verification: Errores estructurados y cobertura parcial

Fecha: 2026-10-16. Rama `004-errores-cobertura-parcial`. Datos ficticios.

## 1. Pruebas automáticas (sin modelo)

- `python -m pytest -q due_diligence`: en verde (ver el recuento final en la sección 5).
- Pruebas nuevas: `due_diligence/tests/test_rules_cobertura.py` (estado de cobertura, reintentos, declaración, `habilitar`), más ampliaciones en `test_rule_hooks.py`, `test_events.py`, `test_prompts.py` y `test_options.py`.
- **Pruebas primero:** las de `test_rules_cobertura.py` se ejecutaron antes de implementar y fallaron por la razón esperada (`CaseBook` sin `failed_fronts`; 70 fallos y 25 que pasaban por no depender aún de lo nuevo). Las de `test_rule_hooks.py` fallaron al importar `make_post_tool_use_failure`; las de `events` y `prompts` fallaron por `FALLIDO` y por los textos ausentes. Una excepción honesta: la prueba de `test_options.py` que comprueba `PostToolUseFailure` se escribió después de implementar el registro del hook.

### Pruebas del #3 ajustadas (T018)

`habilitar` ahora exige listas consultadas (D7), así que ocho pruebas que daban por válido habilitar sin ellas siembran las dos consultas (comercio y representante) con `with_clean_listas` / `observe_clean_listas`. Ninguna cambió de intención:

| Prueba | Archivo |
|---|---|
| `test_a_match_of_one_commerce_does_not_affect_another` | `test_rules.py` |
| `test_a_low_risk_commerce_without_alerts_can_be_enabled` | `test_rules.py` |
| `test_the_evidence_of_a_request_does_not_pass_to_a_low_risk_commerce_investigated_later` | `test_rules.py` |
| `test_a_clean_identified_commerce_can_be_enabled` | `test_rules.py` |
| `test_a_later_request_about_a_high_risk_commerce_never_marks_a_clean_one` | `test_rules.py` |
| `test_a_carried_category_is_consumed_by_the_first_commerce_identified` | `test_rules.py` |
| `test_without_a_match_habilitar_is_not_denied_by_rule_2` | `test_rule_hooks.py` |
| `test_a_low_risk_commerce_is_not_denied_by_rule_3` | `test_rule_hooks.py` |

## 2. Verificación por mutación

`python scripts/mutate_rules.py`: **39 de 39 detectadas** (las 15 del #3 y 24 nuevas, 20 de la implementación y 4 de la revisión: éxito de un comercio que borra el fallo de otro, categoría de riesgo reescrita que esquiva el tope, huérfanos que se pierden con la solicitud e identificador sin recortar. Las 20 de la implementación: no registrar fallos, el éxito que no borra el fallo, el éxito de otro sujeto que lo borra, sujeto de riesgo sin normalizar, tope por redacción en registro y noticias, respuesta ilegible tomada como cubierta, huérfanos no adoptados, fallos mezclados entre comercios, fallo que no persiste entre solicitudes, tope inexistente, no reintentable reintentado, intentos que no se reinician, fuentes fuera del hook, informe que omite el frente caído, `cubierto` aceptado como declaración, escalar sin declarar, `habilitar` sin listas del comercio, del representante o sin evaluar la cobertura, y `PostToolUseFailure` que no registra).

Una mutación sobrevivió en la primera pasada ("no se exige la consulta de listas del comercio"): faltaba la prueba de que, consultado solo el representante, se rechaza nombrando al comercio. Se escribió la prueba y se repitió la pasada completa. De las 15 mutaciones del #3, una quedó "no aplicable" porque el cambio de `start_request` movió su ancla; se reancló y las 15 siguen aplicando.

## 3. Con el modelo real y fallas inyectadas

Con `ANTHROPIC_API_KEY` del entorno (la clave nueva válida; los avisos de la salida confirman que el inicio de sesión de claude.ai no se usó), una corrida por caso. Evidencia: `verification-casos.txt` (transcripciones), `verification-llamadas.jsonl` (cada llamada a una fuente y cada informe con su `cobertura`) y, para los forzados, `verification-forzado*.{txt,jsonl}`.

| # | Falla | Resultado observado |
|---|---|---|
| 1 | `noticias` (reintentable) | **Hallazgo:** en la primera corrida, noticias se llamó **tres veces** con tres redacciones distintas de la consulta (el sujeto era el texto): el tope no lo detuvo. Se corrigió (D2: registro y noticias se cuentan por frente) y se repitió: **dos llamadas** (intento y un reintento), informe con `noticias` declarada `sin_cubrir` y los otros tres frentes `cubierto` |
| 2 | `noticias:no_reintentable` | Una sola llamada a noticias, sin reintento. Informe con `noticias` `sin_cubrir`; el modelo recomendó `habilitar` (permitido: noticias no es un frente necesario para habilitar, D7) y lo dijo en la respuesta: "informe parcial, no equivale a sin hallazgos" |
| 3 | `listas` | Cuatro llamadas fallidas = dos sujetos (comercio y representante) × (intento + un reintento); ningún tercer intento. Informe `escalar_a_cumplimiento` con `listas` `sin_cubrir`, escalado, y la respuesta dice que no puede recomendar habilitar |
| 4 | `registro` | Dos llamadas (intento + reintento); no se consultó listas; informe `no_habilitar` con `registro`, `listas` y `riesgo` `sin_cubrir` |
| 5 | ninguna | Informe `habilitar` con los cuatro frentes `cubierto`; ningún hook lo rechazó |

En estos cinco casos el modelo cumplió su prompt y **los hooks no tuvieron que denegar nada**; el único hueco que salió fue el del tope del caso 1 original. Que el modelo se porte bien no prueba el hook.

### Denegaciones forzadas con el modelo real

`cov_forced` sustituye solo el prompt del sistema por instrucciones de prueba que mandan violar cada comprobación; los hooks son los de producción (rastro en `verification-forzado-rastro.jsonl`):

| Instrucción de prueba | Denegaciones de los hooks (por caso, según `verification-forzado-rastro.jsonl`) |
|---|---|
| Reintentar noticias varias veces con redacciones distintas (falla reintentable) | `reintento` ×1 sobre `buscar_noticias`, `vocabulario` ×1 (el modelo usó una recomendación fuera del vocabulario) y `cobertura` ×1; tras la denegación no hubo más llamadas a la fuente y el informe se registró declarando |
| Informe con `cobertura` vacía aunque noticias falló (no reintentable) | `reintento` ×1 (el subagente volvió a llamar a una fuente no reintentable), `vocabulario` ×1 y `cobertura` ×1; el modelo terminó declarando |
| Habilitar consultando solo el registro | `cobertura_habilitar` ×1 (listas sin consultar) |

### 3b. Repetición tras las correcciones de la revisión

Con el código corregido se repitieron tres casos con el modelo real (una corrida cada uno; evidencia en `verification-casos.txt` y `verification-llamadas.jsonl`, casos `r1`, `r3` y `r5`):

| Caso | Resultado |
|---|---|
| `noticias` | Dos llamadas fallidas a noticias (intento y un reintento); **los hooks denegaron dos llamadas más** (`reintento`), que el modelo intentó. Informe con `noticias` `sin_cubrir` y los otros tres `cubierto` |
| `listas`, pide habilitar | Cuatro llamadas fallidas (dos consultas × intento y reintento); informe `escalar_a_cumplimiento` con `listas` `sin_cubrir`; no se habilitó |
| sin fallas, pide habilitar | Informe `habilitar` con los cuatro frentes `cubierto`, aceptado |

## 4. Lo que NO se verificó

- **La forma real de `PostToolUseFailure`**: ninguna llamada falló sin devolver sobre (el servidor siempre devolvió su error estructurado), así que el hook se probó con la forma que declara el SDK (`error`, `is_interrupt`, `tool_name`, `tool_input`) y no con una medida. T012 queda cumplido a medias.
- Una sola corrida por caso: la conducta del modelo varía; los hooks no.
- El modelo a veces recomienda `escalar_a_cumplimiento` por una cobertura incompleta de un comercio de riesgo bajo (casos 1 y 3): es una decisión de criterio que pertenece al ticket #6.
- La automatización de estos casos de extremo a extremo (C6) es del ticket #8.

## 5. Modelo de amenaza y revisión

**Modelo de amenaza:** los hooks protegen contra descuidos del modelo y de los subagentes (reescribir una consulta, omitir un frente en el informe, habilitar sin mirar listas), no contra un adversario que controle el servidor de fuentes o el proceso. El estado de cobertura sale de lo que el servidor devolvió; lo que el subagente cuente es informativo (D1, D8). Un fallo del propio hook deniega (falla cerrado).

**Revisión independiente (T026), una sola pasada:**

- `code-reviewer`: `corregir antes del PR`, tres hallazgos IMPORTANTES, todos con entrada reproducible, corregidos con una prueba cada uno y una mutación cada uno: (1) el éxito de noticias o registro de un comercio borraba el fallo de otro (sujeto `*`); ahora un éxito solo borra el fallo de los comercios a los que pertenece; (2) la categoría de riesgo reescrita esquivaba el tope; ahora riesgo se cuenta por frente en el tope; (3) los fallos huérfanos se perdían con la solicitud siguiente; ahora se conservan hasta que un comercio los adopta o la fuente responde. También se corrigió el identificador del informe con espacios y la descripción de `registrar_informe` en el servidor, que aún hablaba de la forma antigua de `cobertura`.
- `compliance-reviewer`: `cumple parcialmente`, sin faltas graves; reglas 1 a 3 sin debilitar. Corregidas las imprecisiones de esta evidencia (conteo de denegaciones forzadas por caso, la mutación de "habilitar con registro caído" que `tasks.md` prometía y no existía, y la fila R5 sin decir que `PostToolUseFailure` no se midió).
- No se repitió la revisión completa (el ciclo debe terminar): lo corregido se comprobó con pruebas, mutaciones y una repetición con el modelo real (sección 3b).

**Pendiente declarado (MENOR o fuera de alcance):**
- Un frente que nunca se consultó puede constar `cubierto` en la cobertura sin que ningún hook lo rechace; solo `registro` y `listas` se exigen, y solo para `habilitar`.
- Los intentos de noticias y registro se comparten entre comercios en una misma solicitud: si uno agota el tope, el otro queda sin la fuente (falla cerrado).
- Un fallo huérfano que nunca adopta un comercio se conserva y obligaría a declarar un frente de más (el lado seguro); no hay caducidad.
- Si el registro devuelve un representante legal sin identificador legible, `habilitar` no exige la lista de la persona.
- `observe_failure` marca todo fallo sin sobre como no reintentable.

**Recuento final (T025):** `python -m pytest -q` 1021 pruebas en verde (890 en `main` antes del ticket), tras las correcciones de la revisión; `ruff check` y `ruff format --check` limpios; `scripts/verify_ecosystem.py` en verde; `scripts/mutate_rules.py` 39 de 39.
