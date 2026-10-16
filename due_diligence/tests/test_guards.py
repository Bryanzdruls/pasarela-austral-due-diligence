import pytest

from due_diligence.agents import FRONT_TOOLS
from due_diligence.events import FrontName
from due_diligence.guards import tool_guard

PREFIX = "mcp__pasarela-fuentes__"
OUTPUT_TOOLS = [PREFIX + "registrar_informe", PREFIX + "escalar_a_cumplimiento"]
BUILTIN_TOOLS = ["Bash", "Write", "Read", "Edit", "WebFetch"]


async def call(tool_name, agent_type=None, tool_input=None):
    data = {
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": tool_input or {},
        "tool_use_id": "t1",
    }
    if agent_type is not None:
        data["agent_type"] = agent_type
    return await tool_guard(data, "t1", None)


def assert_denied(output, tool_name):
    specific = output["hookSpecificOutput"]
    assert specific["hookEventName"] == "PreToolUse"
    assert specific["permissionDecision"] == "deny"
    assert tool_name in specific["permissionDecisionReason"]


@pytest.mark.parametrize("front", list(FrontName))
async def test_each_subagent_may_use_only_its_own_tool(front):
    assert await call(FRONT_TOOLS[front], agent_type=front.value) == {}


@pytest.mark.parametrize("front", list(FrontName))
async def test_a_subagent_is_denied_every_other_source_tool(front):
    for other, tool in FRONT_TOOLS.items():
        if other != front:
            assert_denied(await call(tool, agent_type=front.value), tool)


@pytest.mark.parametrize("front", list(FrontName))
async def test_a_subagent_is_denied_builtin_output_and_foreign_tools(front):
    for tool in [*BUILTIN_TOOLS, *OUTPUT_TOOLS, "mcp__otro__herramienta", "Agent"]:
        assert_denied(await call(tool, agent_type=front.value), tool)


async def test_the_coordinator_may_delegate_to_each_front():
    for front in FrontName:
        for tool in ("Agent", "Task"):
            out = await call(tool, tool_input={"subagent_type": front.value, "prompt": "x"})
            assert out == {}, (tool, front)


@pytest.mark.parametrize("tool_input", [{"subagent_type": "general-purpose"}, {}, {"prompt": "x"}])
async def test_the_coordinator_cannot_launch_builtin_or_unspecified_subagents(tool_input):
    # La herramienta Agent también puede lanzar subagentes integrados con herramientas amplias.
    assert_denied(await call("Agent", tool_input=tool_input), "Agent")


async def test_the_coordinator_is_denied_every_other_tool():
    for tool in [*FRONT_TOOLS.values(), *OUTPUT_TOOLS, *BUILTIN_TOOLS, "mcp__otro__herramienta"]:
        assert_denied(await call(tool), tool)


async def test_an_unknown_agent_type_fails_closed():
    assert_denied(await call(FRONT_TOOLS[FrontName.NOTICIAS], agent_type="otro"), "buscar_noticias")
    assert_denied(await call("Agent", agent_type="otro"), "Agent")


async def test_the_reason_is_human_readable():
    out = await call("Bash", agent_type="noticias")
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    assert "noticias" in reason and len(reason) > 20


async def test_background_delegation_is_denied():
    # En segundo plano, el resultado sería un acuse y no el JSON del frente.
    out = await call("Agent", tool_input={"subagent_type": "noticias", "run_in_background": True})
    assert_denied(out, "Agent")
    ok = await call("Agent", tool_input={"subagent_type": "noticias", "run_in_background": False})
    assert ok == {}


async def test_hook_trace_records_who_called_what(tmp_path, monkeypatch):
    import json

    trace = tmp_path / "trace.jsonl"
    monkeypatch.setenv("PASARELA_HOOK_TRACE", str(trace))
    await call(FRONT_TOOLS[FrontName.NOTICIAS], agent_type="noticias")
    await call("Bash")
    rows = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
    assert [(r["tool_name"], r["agent_type"]) for r in rows] == [
        (FRONT_TOOLS[FrontName.NOTICIAS], "noticias"),
        ("Bash", None),
    ]
    assert [r["decision"] for r in rows] == ["allow", "deny"]


async def test_no_trace_file_is_written_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("PASARELA_HOOK_TRACE", raising=False)
    monkeypatch.chdir(tmp_path)
    await call("Bash")
    assert list(tmp_path.iterdir()) == []
