from due_diligence.events import FrontName
from due_diligence.prompts import COORDINATOR_PROMPT

P = COORDINATOR_PROMPT
LOWER = P.lower()


def test_mentions_the_four_fronts():
    for front in FrontName:
        assert front.value in P, front.value


def test_asks_for_the_commerce_when_missing_and_does_not_delegate():  # FR-010
    assert "si la solicitud no identifica un comercio" in LOWER
    assert "no delegues" in LOWER
    assert "identificador" in LOWER


def test_asks_to_clarify_when_several_commerces_are_mentioned():  # edge case
    assert "más de un comercio" in LOWER


def test_report_structure_and_recommendation():  # FR-009, FR-011
    assert "una sección por frente" in LOWER
    assert "Datos aportados por el analista" in P
    assert "recomendación" in LOWER


def test_encargo_is_minimal_and_never_carries_a_previous_commerce():  # FR-004, FR-012
    assert "no incluyas la conversación" in LOWER
    assert "comercio anterior" in LOWER


def test_followups_are_answered_from_what_was_already_investigated():  # FR-013
    assert "seguimiento" in LOWER
    assert "no vuelvas a lanzar" in LOWER


def test_independent_fronts_in_one_turn_and_lists_only_afterwards():  # FR-006, FR-007
    assert "en un mismo turno" in LOWER
    assert "solo después" in LOWER
    assert "representante legal" in LOWER
    assert "único comercio" in LOWER


def test_coordinator_does_not_query_sources_itself():
    assert "no consultes las fuentes" in LOWER


def test_says_the_decision_rules_are_enforced_elsewhere():
    # El prompt orienta; las reglas 1-3 las garantizan hooks (ticket #3).
    assert "orienta" in LOWER or "orientación" in LOWER


def test_declares_the_closed_recommendation_vocabulary_and_the_output_tools():
    # Ticket #3: el hook solo acepta estos valores, así que el modelo debe conocerlos exactos.
    for value in ("habilitar", "no_habilitar", "escalar_a_cumplimiento"):
        assert f"`{value}`" in COORDINATOR_PROMPT
    assert "registrar_informe" in COORDINATOR_PROMPT
    assert "escalar_a_cumplimiento" in COORDINATOR_PROMPT


def test_still_says_the_rules_are_enforced_by_hooks_and_not_by_the_prompt():
    assert "hooks" in LOWER and "no con estas instrucciones" in LOWER


# --- #4: errores estructurados y cobertura parcial ----------------------------------------


def test_every_subagent_prompt_describes_the_structured_error_and_forbids_inventing_data():
    from due_diligence.prompts import SUBAGENT_PROMPTS

    assert set(SUBAGENT_PROMPTS) == {f.value for f in FrontName}
    for front, prompt in SUBAGENT_PROMPTS.items():
        for field in ('"estado": "error"', '"frente"', '"reintentable"', '"obtenido"'):
            assert field in prompt, (front, field)
        assert "no inventes" in prompt.lower(), front
        assert "ok: false" in prompt or '"ok": false' in prompt, front


def test_the_coordinator_retries_once_what_is_retryable_and_declares_the_rest():
    text = COORDINATOR_PROMPT.lower()
    assert "una sola vez" in text and "reintentable" in text
    assert "no reintentes" in text
    assert "sin_cubrir" in text and "cobertura" in text


def test_the_coordinator_never_presents_a_partial_report_as_complete():
    text = COORDINATOR_PROMPT.lower()
    assert "no presentes" in text and "completo" in text
    assert "sin hallazgos" in text


def test_the_coordinator_prompt_shows_the_coverage_format_with_the_four_fronts():
    for front in ("registro", "listas", "noticias", "riesgo"):
        assert f'"{front}"' in COORDINATOR_PROMPT, front
    assert '"estado": "sin_cubrir"' in COORDINATOR_PROMPT


def test_the_coordinator_prompt_says_habilitar_needs_registry_and_listas_consulted():
    text = COORDINATOR_PROMPT.lower()
    assert "para recomendar `habilitar`" in text
    assert "listas" in text and "representante" in text


def test_the_coverage_rule_is_enforced_by_hooks_too_and_the_prompt_only_guides():
    text = COORDINATOR_PROMPT.lower()
    assert "hooks" in text and "regla 5" in text


# --- #5: procedencia, conflictos y comercios parecidos -----------------------------------


def test_the_coordinator_prompt_lists_the_exact_source_names_of_the_four_fronts():
    from due_diligence.events import EXPECTED_SOURCES

    for source in EXPECTED_SOURCES.values():
        assert source in COORDINATOR_PROMPT, source


def test_the_coordinator_prompt_describes_findings_with_source_and_date_per_front():
    text = COORDINATOR_PROMPT
    assert '"fuente"' in text and '"fecha"' in text and "hallazgos" in text
    assert "cada afirmación" in text.lower()


def test_the_coordinator_prompt_shows_the_conflict_format_and_forbids_choosing_a_value():
    text = COORDINATOR_PROMPT.lower()
    assert '"conflictos"' in COORDINATOR_PROMPT or "`conflictos`" in COORDINATOR_PROMPT
    assert '"dato"' in COORDINATOR_PROMPT and '"valores"' in COORDINATOR_PROMPT
    assert "no elijas" in text and "todos los valores" in text
    assert "origen" in text


def test_the_coordinator_prompt_shows_contradictions_between_fronts_too():
    text = COORDINATOR_PROMPT.lower()
    assert "se contradicen" in text and "noticia" in text and "registro" in text


def test_the_coordinator_prompt_asks_for_the_identifier_when_several_commerces_match():
    text = COORDINATOR_PROMPT.lower()
    assert "varios comercios" in text or "varias coincidencias" in text
    assert "candidatos" in text and "identificador" in text
    assert "no elijas" in text and "no lances" in text
    assert "no registres" in text or "no registrar" in text


def test_the_coordinator_prompt_says_to_ask_again_for_an_identifier_that_matches_no_candidate():
    text = COORDINATOR_PROMPT.lower()
    assert "no corresponde a ninguno" in text and "vuelve a pedir" in text


def test_the_provenance_rules_are_enforced_by_hooks_too_and_the_prompt_only_guides():
    text = COORDINATOR_PROMPT.lower()
    assert "regla 4" in text and "hooks" in text


def test_the_registry_subagent_still_includes_every_date_with_its_origin():
    from due_diligence.prompts import SUBAGENT_PROMPTS

    text = SUBAGENT_PROMPTS["registro_mercantil"].lower()
    assert "fechas distintas" in text and "origen" in text
