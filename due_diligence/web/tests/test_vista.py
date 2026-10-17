"""La vista de cada evento: lo que el analista lee, sin términos internos."""

import pytest

from due_diligence.events import (
    CallBlocked,
    CoordinatorText,
    Escalated,
    FrontName,
    FrontResult,
    FrontStatus,
    ReportRegistered,
    RunFinished,
    SubagentFinished,
    SubagentStarted,
)
from due_diligence.web.vista import REGLAS, a_vista, vista_analista, vista_error

TIPOS = {
    "analista",
    "coordinador",
    "delegacion",
    "resultado",
    "bloqueo",
    "informe",
    "escalamiento",
    "fin",
    "error",
}
INTERNOS = ("mcp__", "PreToolUse", "PostToolUse", "hook", "CaseBook", "tool_use_id")


def completo(frente=FrontName.REGISTRO_MERCANTIL):
    return FrontResult(
        frente,
        {"x": 1},
        {"fuente": "registro_ficticio", "fecha": "2026-01-01"},
        FrontStatus.COMPLETO,
    )


def check_common(vista, tipo):
    assert vista["tipo"] == tipo and tipo in TIPOS
    assert vista["titulo"].strip() and vista["hora"]
    assert isinstance(vista["extra"], dict)
    for texto in (vista["titulo"], vista["detalle"]):
        assert not any(term in texto for term in INTERNOS)


def test_analyst_and_coordinator_messages():
    v = vista_analista("Necesito el due diligence de CO-XX-0001", "2026-10-17T10:00:00+00:00")
    check_common(v, "analista")
    assert "CO-XX-0001" in v["detalle"]
    v = a_vista(CoordinatorText("Resumen del caso"), 4)
    check_common(v, "coordinador")
    assert v["detalle"] == "Resumen del caso"


def test_a_delegation_names_the_front_in_plain_words_and_shows_the_brief():
    v = a_vista(SubagentStarted(FrontName.REGISTRO_MERCANTIL, "tu_1", "Busca CO-XX-0001"), 1)
    check_common(v, "delegacion")
    assert "registro mercantil" in v["titulo"].lower()
    assert "Busca CO-XX-0001" in v["detalle"]
    assert "tu_1" not in v["titulo"] + v["detalle"]


@pytest.mark.parametrize("frente", list(FrontName))
def test_every_front_has_a_plain_name(frente):
    v = a_vista(SubagentStarted(frente, "t", "encargo"), 1)
    assert "_" not in v["titulo"]


def test_a_complete_front_result_says_it_responded_with_its_source():
    v = a_vista(SubagentFinished(FrontName.REGISTRO_MERCANTIL, completo()), 2)
    check_common(v, "resultado")
    assert "respondió" in v["titulo"].lower()
    assert "registro_ficticio" in v["detalle"] and "2026-01-01" in v["detalle"]


def test_a_failed_front_says_so_whether_retryable_and_what_was_obtained():
    error = {"reintentable": True, "obtenido": {"nombre": "Comercio"}, "motivo": "fuente caída"}
    result = FrontResult(
        FrontName.NOTICIAS,
        {"error": error},
        {"fuente": "noticias_ficticias", "fecha": "2026-01-01"},
        FrontStatus.FALLIDO,
    )
    v = a_vista(SubagentFinished(FrontName.NOTICIAS, result), 2)
    check_common(v, "resultado")
    assert "falló" in v["titulo"].lower()
    assert "fuente caída" in v["detalle"] and "reintentar" in v["detalle"].lower()
    assert "nombre" in v["detalle"]


def test_a_front_without_structure_or_result_is_not_presented_as_complete():
    for result in (
        FrontResult(
            FrontName.NOTICIAS, {"texto_sin_estructura": "?"}, {}, FrontStatus.NO_ESTRUCTURADO
        ),
        FrontResult(FrontName.NOTICIAS, {"error": "x"}, {}, FrontStatus.NO_COMPLETADO),
        None,
    ):
        v = a_vista(SubagentFinished(FrontName.NOTICIAS, result), 2)
        check_common(v, "resultado")
        assert "respondió" not in v["titulo"].lower()


@pytest.mark.parametrize("regla", sorted(set(REGLAS) - {"evaluacion"}))
def test_every_known_rule_is_translated_and_the_literal_reason_is_kept(regla):
    v = a_vista(
        CallBlocked("listas_restrictivas", "consultar_listas_restrictivas", regla, "Motivo X"), 3
    )
    check_common(v, "bloqueo")
    assert "bloque" in v["titulo"].lower()
    assert REGLAS[regla] in v["detalle"] and "Motivo X" in v["detalle"]
    assert v["extra"]["regla"] == regla
    assert "consultar_listas_restrictivas" not in v["titulo"]


def test_the_known_rules_cover_everything_the_system_can_decide():
    expected = {
        "1", "2", "3", "ambiguedad", "cobertura", "cobertura_habilitar", "conflicto",
        "escalamiento", "handoff_causa", "handoff_hallazgos", "identificacion", "procedencia",
        "reintento", "vocabulario", "aislamiento", "evaluacion",
    }  # fmt: skip
    assert expected <= set(REGLAS)


def test_an_unknown_rule_gets_a_generic_text_and_does_not_fail():
    v = a_vista(CallBlocked("coordinador", "registrar_informe", "inventada", "Motivo"), 3)
    check_common(v, "bloqueo")
    assert "Motivo" in v["detalle"]


def test_report_and_escalation_show_number_commerce_and_recommendation_or_cause():
    v = a_vista(ReportRegistered("INF-0001", "CO-XX-0001", "no_habilitar"), 5)
    check_common(v, "informe")
    assert "INF-0001" in v["titulo"] + v["detalle"] and "CO-XX-0001" in v["detalle"]
    assert "no habilitar" in v["detalle"].lower()
    v = a_vista(Escalated("ESC-0001", "CO-XX-0003", "coincidencia en listas"), 6)
    check_common(v, "escalamiento")
    assert "ESC-0001" in v["titulo"] + v["detalle"] and "coincidencia en listas" in v["detalle"]


def test_the_end_of_turn_says_why_it_ended_and_errors_are_readable():
    v = a_vista(RunFinished("success", "end_turn", "completed"), 7)
    check_common(v, "fin")
    assert "terminó" in v["titulo"].lower()
    v = a_vista(RunFinished("error_exception", None, "RuntimeError"), 7)
    check_common(v, "error")
    assert "RuntimeError" in v["detalle"]
    v = vista_error("ProcessError", "2026-10-17T10:00:00+00:00")
    check_common(v, "error")


def test_markup_in_text_is_kept_as_data_not_interpreted():
    v = a_vista(CoordinatorText("<script>alert(1)</script>"), 1)
    assert v["detalle"] == "<script>alert(1)</script>"


def test_an_evaluation_failure_never_shows_the_internal_exception_text():
    motivo = "Una regla no pudo evaluarse (ValueError: C:/ruta/privada). Se deniega."
    v = a_vista(CallBlocked("coordinador", "registrar_informe", "evaluacion", motivo), 3)
    check_common(v, "bloqueo")
    assert "privada" not in v["titulo"] + v["detalle"] + str(v["extra"])
    assert REGLAS["evaluacion"] in v["detalle"]


def test_a_report_shows_which_fronts_were_left_uncovered():
    v = a_vista(
        ReportRegistered("INF-0002", "CO-LB-0002", "no_habilitar", sin_cubrir=("noticias",)), 5
    )
    check_common(v, "informe")
    assert "sin cubrir" in v["detalle"].lower() and "noticias" in v["detalle"]
    limpio = a_vista(ReportRegistered("INF-0003", "CO-LB-0002", "habilitar"), 5)
    assert "sin cubrir" not in limpio["detalle"].lower()
