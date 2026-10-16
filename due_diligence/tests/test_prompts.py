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
