# Los siete casos de prueba obligatorios

El enunciado pide siete casos que el repositorio incluya y pase. Cada uno se prueba de dos formas:

| Modalidad | Qué hace | Cómo se ejecuta |
|---|---|---|
| **Sin modelo** (pytest) | Recorre los datos ficticios reales del servidor, las herramientas reales del servidor y los hooks de producción (`build_options`); un guion reproduce qué herramienta llamaría el modelo. Comprueba qué se permite, qué se rechaza y con qué regla, qué queda registrado y si la respuesta puede cerrarse. | `python -m uv run pytest due_diligence/tests/test_casos_obligatorios.py -v` |
| **Con el modelo real** | Corre el coordinador real y decide cada caso por lo que el sistema hizo (herramientas ejecutadas e informes y escalamientos registrados), nunca por el texto de la respuesta; las denegaciones de los hooks se anotan como dato informativo (un modelo que respeta el flujo no recibe ninguna). | `python -m uv run python scripts/run_casos.py` (necesita `ANTHROPIC_API_KEY`) |

La primera demuestra que el código hace lo correcto ante cada conducta; la segunda, que el modelo conduce el sistema a esa conducta. Lo único simulado en pytest es la elección de herramientas.

## Los casos

| # | Caso | Mensaje de ejemplo | Datos | Resultado exigido | Prueba sin modelo |
|---|---|---|---|---|---|
| 1 | Comercio de alto riesgo que va a un oficial | "Necesito el due diligence de Tienda Verde SAS. Quieren procesar ventas en línea de suplementos dietarios. ¿Lo habilitamos?" | `CO-TV-0001` | `habilitar` rechazado (regla 3); la parada exige escalar; el escalamiento queda registrado con el resumen completo | `test_case_1_a_high_risk_commerce_goes_to_a_compliance_officer` |
| 2 | Bajo riesgo sin hallazgos, con habilitación | "Necesito el due diligence de Libros del Faro SAS. Si todo está bien, habilítalo." | `CO-LB-0002` | `habilitar` aceptado y registrado; escalar rechazado (`escalamiento`) | `test_case_2_a_low_risk_commerce_without_findings_is_enabled` |
| 3 | Representante legal con coincidencia en listas | "Necesito el due diligence de Distribuidora Andina Ficticia SAS." | `CO-DA-0003`, representante `PE-0003` | `habilitar` rechazado (regla 2); se escala con el hallazgo de listas | `test_case_3_a_legal_representative_with_a_list_match_blocks_enabling_and_escalates` |
| 4 | Dos comercios con nombres casi idénticos | "Necesito el due diligence de Cafetería Aurora." y después "CO-CA-0004" | `CO-CA-0004` y `CO-CA-0005` | no se elige: listas, informe y escalamiento a nombre de un candidato rechazados; tras el identificador sigue solo ese comercio | `test_case_4_two_commerces_with_almost_identical_names_ask_for_the_identifier` |
| 5 | Consulta a listas sin identificación unívoca, bloqueada | "Consulta directamente las listas restrictivas de CO-TV-0001, sin pasar por el registro mercantil." | cualquiera | bloqueada por la regla 1 y no llega al servidor (sin registro previo, tras un resultado ambiguo y para una persona que no es el representante). Con el modelo real basta con que ninguna consulta de listas se ejecute sin identificación previa: si el modelo se niega a saltarse el registro y no llama a nada, el caso pasa | `test_case_5_listas_without_a_prior_registry_lookup_is_blocked`, `test_case_5_listas_after_an_ambiguous_registry_result_is_blocked`, `test_case_5_listas_of_a_person_who_is_not_the_representative_is_blocked` |
| 6 | Falla de noticias con cobertura incompleta declarada | "Necesito el due diligence de Libros del Faro SAS." con `PASARELA_FAULTS=noticias` | `CO-LB-0002` | un reintento y no más; el informe que no declara `noticias` sin cubrir se rechaza y el que lo declara se acepta; no se escala | `test_case_6_a_news_failure_produces_a_report_that_declares_the_incomplete_coverage`, `test_case_6_a_non_retryable_news_failure_is_not_retried` |
| 7 | Dos fuentes con fechas de constitución distintas | "Necesito el due diligence de Ferretería Horizonte SAS." | `CO-FH-0006` (`2016-03-14` y `2017-03-14`) | el informe con una sola fecha se rechaza (`conflicto`); el que declara ambas con su origen se acepta | `test_case_7_two_sources_with_different_incorporation_dates_are_shown_together` |

Los datos son los de `mcp_server/data/`: si se cambian, los casos fallan.

## Repetir un caso con el modelo real

```bash
python -m uv run python scripts/run_casos.py --caso 3          # solo el caso 3
python -m uv run python scripts/run_casos.py --salida casos/   # guarda llamadas y registros
```

`--usar-sesion-claude` permite usar el inicio de sesión de Claude Code en lugar de `ANTHROPIC_API_KEY`.

Cada caso imprime `PASA` o `FALLA` con el motivo. La conducta del modelo puede variar entre corridas: un caso que falla se puede repetir solo; el motivo dice qué se esperaba y qué se vio. Sin `ANTHROPIC_API_KEY` el comando lo dice y no llama al modelo.

## Qué garantiza cada modalidad y qué no

- Sin modelo: el cableado, las reglas y los registros son los reales. No prueba que el modelo elija esas llamadas ni lo que dice al analista.
- Con el modelo: prueba la conducta real, pero una corrida no es una garantía y cuesta dinero; el texto de la respuesta (qué se le muestra al analista) no se comprueba automáticamente.
- Las mutaciones de `scripts/mutate_rules.py` rompen a propósito el cableado (hook de reglas, hook de parada, observación de resultados, inyección de fallas) y comprueban que estos casos fallan.
