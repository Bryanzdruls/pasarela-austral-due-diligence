from due_diligence.agents import FRONT_TOOLS, build_agents
from due_diligence.events import FrontName

PREFIX = "mcp__pasarela-fuentes__"


def test_exactly_four_agents_named_after_the_fronts():
    agents = build_agents()
    assert set(agents) == {f.value for f in FrontName}
    assert len(agents) == 4


def test_each_agent_has_only_the_tool_of_its_front():
    expected = {
        "registro_mercantil": [PREFIX + "consultar_registro_mercantil"],
        "listas_restrictivas": [PREFIX + "consultar_listas_restrictivas"],
        "noticias": [PREFIX + "buscar_noticias"],
        "riesgo_categoria": [PREFIX + "consultar_riesgo_categoria"],
    }
    agents = build_agents()
    for name, tools in expected.items():
        assert agents[name].tools == tools, name
    # FRONT_TOOLS es la única fuente de verdad de la asignación
    assert {f.value: [t] for f, t in FRONT_TOOLS.items()} == expected


def test_no_agent_can_use_builtin_or_output_tools():
    for name, agent in build_agents().items():
        assert agent.tools is not None and len(agent.tools) == 1, name
        assert agent.tools[0].startswith(PREFIX), name
        assert "registrar_informe" not in agent.tools[0], name
        assert "escalar_a_cumplimiento" not in agent.tools[0], name


def test_every_agent_has_a_description_to_be_chosen_by():
    for name, agent in build_agents().items():
        assert len(agent.description.strip()) > 20, name


def test_every_prompt_demands_json_with_content_and_metadata():
    for name, agent in build_agents().items():
        p = agent.prompt
        assert "JSON" in p, name
        assert "contenido" in p and "metadatos" in p, name
        assert "fuente" in p and "fecha" in p, name


def test_front_specific_prompt_rules():
    agents = build_agents()
    assert "no elijas" in agents["registro_mercantil"].prompt.lower()
    assert "todas las coincidencias" in agents["registro_mercantil"].prompt
    assert "NO es una coincidencia en listas" in agents["noticias"].prompt
    assert "identificador" in agents["listas_restrictivas"].prompt
    assert "sin_clasificar" in agents["riesgo_categoria"].prompt
