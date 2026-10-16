import subprocess
import sys
from pathlib import Path

from due_diligence.agents import build_agents
from due_diligence.options import REPO_ROOT, build_options

SERVER = "pasarela-fuentes"


def test_coordinator_is_restricted_to_the_agent_tool():
    o = build_options()
    assert o.tools == ["Agent"]
    assert o.allowed_tools == ["Agent"]


def test_no_max_turns_and_no_inherited_project_settings():
    o = build_options()
    assert o.max_turns is None
    assert o.setting_sources == []


def test_agents_are_the_four_fronts():
    assert set(build_options().agents) == set(build_agents())


def test_working_directory_is_the_repo_root():
    assert Path(build_options().cwd) == REPO_ROOT
    assert (REPO_ROOT / "mcp_server").is_dir()


def test_mcp_server_is_a_stdio_python_module_without_unsupported_keys():
    cfg = build_options().mcp_servers[SERVER]
    assert cfg["type"] == "stdio"
    assert cfg["command"] == sys.executable
    assert cfg["args"] == ["-m", "mcp_server"]
    assert "cwd" not in cfg  # McpStdioServerConfig no admite cwd
    assert Path(cfg["env"]["PYTHONPATH"]) == REPO_ROOT


def test_fault_and_runtime_variables_are_passed_only_when_set(monkeypatch, tmp_path):
    monkeypatch.delenv("PASARELA_FAULTS", raising=False)
    monkeypatch.delenv("PASARELA_RUNTIME_DIR", raising=False)
    env = build_options().mcp_servers[SERVER]["env"]
    assert "PASARELA_FAULTS" not in env and "PASARELA_RUNTIME_DIR" not in env

    monkeypatch.setenv("PASARELA_FAULTS", "noticias")
    monkeypatch.setenv("PASARELA_RUNTIME_DIR", str(tmp_path))
    env = build_options().mcp_servers[SERVER]["env"]
    assert env["PASARELA_FAULTS"] == "noticias"
    assert env["PASARELA_RUNTIME_DIR"] == str(tmp_path)


def test_server_module_is_importable_from_another_directory(tmp_path):
    cfg = build_options().mcp_servers[SERVER]
    proc = subprocess.run(
        [cfg["command"], "-c", "import mcp_server.server"],
        cwd=tmp_path,  # directorio distinto de la raíz del repo
        env={**cfg["env"], "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", "")},
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
