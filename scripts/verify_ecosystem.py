"""Verifica que el ecosistema de Claude Code cumple los mínimos del enunciado (solo stdlib).

Uso: python scripts/verify_ecosystem.py [--root RUTA] [--json]
Sale con 0 si todo cumple y con 1 si algún mínimo falla, diciendo cuál y por qué.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from frontmatter import as_list, parse_frontmatter

CHECK_MEMORY = "memoria de proyecto"
CHECK_RULES = "reglas con paths"
CHECK_AGENTS = "subagentes restringidos"
CHECK_SKILLS = "skills propias"
CHECK_SKILL_OPTIONS = "opciones de skills"
CHECK_HOOKS = "hooks"
CHECK_COMMAND = "comando propio"
CHECK_MCP = "servidores MCP"
CHECK_CREDENTIALS = "credenciales en .mcp.json"
CHECK_INVENTORY = "inventario del ecosistema"

ALL_CHECKS = (
    CHECK_MEMORY,
    CHECK_RULES,
    CHECK_AGENTS,
    CHECK_SKILLS,
    CHECK_SKILL_OPTIONS,
    CHECK_HOOKS,
    CHECK_COMMAND,
    CHECK_MCP,
    CHECK_CREDENTIALS,
    CHECK_INVENTORY,
)

INVENTORY = "docs/ECOSISTEMA.md"
_IGNORED_DIRS = {".git", ".venv", "node_modules", "__pycache__", "specs", ".specify"}
_WRITE_TOOLS = {"edit", "write", "bash", "notebookedit", "multiedit"}
_ENV_REFERENCE = re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*\}")
# Prefijos de credenciales conocidas; se arman por partes para no escribirlas completas aquí.
_SECRET = re.compile(
    "|".join(
        ["sk-" + "ant-[A-Za-z0-9_-]{16,}", "gh[pousr]" + "_[A-Za-z0-9]{20,}", "github" + "_pat_"]
    )
)
_SENSITIVE_HEADER = re.compile(r"auth|token|key|secret", re.IGNORECASE)
_IMPORT = re.compile(r"(?:^|\s)@([\w./-]+\.md)\b")
_HOOK_SCRIPT = re.compile(r"\.claude/hooks/([\w./-]+\.py)")


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _json(path: Path) -> dict:
    try:
        data = json.loads(_read(path) or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _skills(root: Path) -> list[Path]:
    found = sorted((root / ".claude" / "skills").glob("*/SKILL.md"))
    return [p for p in found if not p.parent.name.startswith("speckit")]


def _commands(root: Path) -> list[Path]:
    found = sorted((root / ".claude" / "commands").glob("*.md"))
    return [p for p in found if not p.name.startswith("speckit")]


def _claude_files(root: Path) -> list[Path]:
    return [
        p
        for p in sorted(root.rglob("CLAUDE.md"))
        if not _IGNORED_DIRS & set(p.relative_to(root).parts)
    ]


def _imports(root: Path) -> list[str]:
    return _IMPORT.findall(_read(root / "CLAUDE.md"))


def _hook_entries(root: Path) -> list[tuple[str, str, dict]]:
    """Lista de (evento, matcher, definición) de los hooks de settings.json."""
    entries = []
    hooks = _json(root / ".claude" / "settings.json").get("hooks", {})
    for event, groups in hooks.items() if isinstance(hooks, dict) else []:
        for group in groups if isinstance(groups, list) else []:
            for hook in group.get("hooks", []):
                entries.append((event, group.get("matcher", ""), hook))
    return entries


def _hook_scripts(root: Path) -> list[str]:
    scripts = []
    for _, _, hook in _hook_entries(root):
        text = " ".join([str(hook.get("command", "")), *map(str, hook.get("args", []))])
        scripts += [f".claude/hooks/{name}" for name in _HOOK_SCRIPT.findall(text)]
    return scripts


# --------------------------------------------------------------------------- comprobaciones


def check_memory(root: Path) -> Check:
    if not (root / "CLAUDE.md").is_file():
        return Check(CHECK_MEMORY, False, "falta CLAUDE.md en la raíz")
    missing = [name for name in _imports(root) if not (root / name).is_file()]
    if missing:
        return Check(
            CHECK_MEMORY, False, "CLAUDE.md importa archivos inexistentes: " + ", ".join(missing)
        )
    nested = [p for p in _claude_files(root) if p.parent != root]
    if not _imports(root) and not nested:
        return Check(
            CHECK_MEMORY, False, "CLAUDE.md no importa nada ni hay CLAUDE.md en subdirectorios"
        )
    return Check(
        CHECK_MEMORY, True, f"{len(_imports(root))} import(s), {len(nested)} en subdirectorios"
    )


def check_rules(root: Path) -> Check:
    scoped = [
        p.name
        for p in sorted((root / ".claude" / "rules").glob("*.md"))
        if as_list(parse_frontmatter(_read(p)).get("paths"))
    ]
    ok = len(scoped) >= 2
    return Check(
        CHECK_RULES, ok, f"{len(scoped)} con paths (mínimo 2): {', '.join(scoped) or 'ninguna'}"
    )


def check_agents(root: Path) -> Check:
    restricted = []
    for path in sorted((root / ".claude" / "agents").glob("*.md")):
        tools = {t.lower() for t in as_list(parse_frontmatter(_read(path)).get("tools"))}
        if tools and "*" not in tools and not tools & _WRITE_TOOLS:
            restricted.append(path.stem)
    ok = len(restricted) >= 2
    return Check(
        CHECK_AGENTS,
        ok,
        f"{len(restricted)} de solo lectura (mínimo 2): {', '.join(restricted) or 'ninguno'}",
    )


def check_skills(root: Path) -> Check:
    names = [p.parent.name for p in _skills(root)]
    ok = len(names) >= 2
    return Check(
        CHECK_SKILLS, ok, f"{len(names)} propias (mínimo 2): {', '.join(names) or 'ninguna'}"
    )


def check_skill_options(root: Path) -> Check:
    metas = [parse_frontmatter(_read(p)) for p in _skills(root)]
    missing = []
    if not any(m.get("context") == "fork" for m in metas):
        missing.append("context: fork")
    if not any(m.get("allowed-tools") for m in metas):
        missing.append("allowed-tools")
    if not any(m.get("argument-hint") for m in metas):
        missing.append("argument-hint")
    if missing:
        return Check(CHECK_SKILL_OPTIONS, False, "ninguna skill usa: " + ", ".join(missing))
    return Check(
        CHECK_SKILL_OPTIONS, True, "context: fork, allowed-tools y argument-hint presentes"
    )


def check_hooks(root: Path) -> Check:
    entries = _hook_entries(root)
    problems = []
    if len(entries) < 2:
        problems.append(f"hay {len(entries)} hook(s), el mínimo es 2")
    if not any(e == "PreToolUse" for e, _, _ in entries):
        problems.append("falta un hook PreToolUse que pueda bloquear")
    if not any(e == "PostToolUse" and re.search("Edit|Write", m) for e, m, _ in entries):
        problems.append("falta un hook PostToolUse sobre Edit/Write")
    absent = sorted({s for s in _hook_scripts(root) if not (root / s).is_file()})
    if absent:
        problems.append("scripts inexistentes: " + ", ".join(absent))
    if problems:
        return Check(CHECK_HOOKS, False, "; ".join(problems))
    return Check(CHECK_HOOKS, True, f"{len(entries)} hooks registrados, scripts presentes")


def check_command(root: Path) -> Check:
    names = [p.stem for p in _commands(root)]
    return Check(
        CHECK_COMMAND, bool(names), f"{len(names)} propio(s): {', '.join(names) or 'ninguno'}"
    )


def _servers(root: Path) -> dict:
    servers = _json(root / ".mcp.json").get("mcpServers", {})
    return servers if isinstance(servers, dict) else {}


def check_mcp(root: Path) -> Check:
    servers = _servers(root)
    problems = []
    github = next((s for n, s in servers.items() if "github" in n.lower()), None)
    if github is None:
        problems.append("falta el servidor de GitHub")
    else:
        toolsets = str((github.get("headers") or {}).get("X-MCP-Toolsets", ""))
        if "projects" not in toolsets.split(","):
            problems.append("el servidor de GitHub no habilita el toolset projects")
    own = [n for n, s in servers.items() if "github" not in n.lower() and s.get("type") == "stdio"]
    if not own:
        problems.append("falta el servidor MCP propio (stdio)")
    if problems:
        return Check(CHECK_MCP, False, "; ".join(problems))
    return Check(CHECK_MCP, True, "GitHub con projects y servidor propio: " + ", ".join(own))


def check_credentials(root: Path) -> Check:
    # El detalle nombra el servidor y el encabezado, nunca el valor.
    problems = []
    for name, server in _servers(root).items():
        if _SECRET.search(json.dumps(server)):
            problems.append(f"{name}: contiene algo con forma de credencial")
            continue
        for header, value in (server.get("headers") or {}).items():
            if _SENSITIVE_HEADER.search(header) and not _ENV_REFERENCE.search(str(value)):
                problems.append(
                    f"{name}: el encabezado {header} no es una referencia ${{VARIABLE}}"
                )
    if problems:
        return Check(CHECK_CREDENTIALS, False, "; ".join(problems))
    return Check(CHECK_CREDENTIALS, True, "los encabezados sensibles usan variables de entorno")


def _expected_pieces(root: Path) -> set[str]:
    pieces = {_rel(root, p) for p in _claude_files(root)}
    pieces |= {name for name in _imports(root) if (root / name).is_file()}
    for folder in ("rules", "agents"):
        pieces |= {_rel(root, p) for p in (root / ".claude" / folder).glob("*.md")}
    pieces |= {_rel(root, p) for p in _skills(root)} | {_rel(root, p) for p in _commands(root)}
    pieces |= {s for s in _hook_scripts(root) if (root / s).is_file()}
    for name in (".claude/settings.json", ".mcp.json", "scripts/verify_ecosystem.py"):
        if (root / name).is_file():
            pieces.add(name)
    return pieces


def _inventory_paths(text: str) -> list[str]:
    paths, in_table = [], False
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not line.strip().startswith("|"):
            in_table = False
        elif cells and cells[0].lower() == "pieza":
            in_table = True
        elif in_table and not set(cells[0]) <= set("-: "):
            paths.append(cells[0].strip("`").split("#")[0])
    return paths


def check_inventory(root: Path) -> Check:
    path = root / INVENTORY
    if not path.is_file():
        return Check(CHECK_INVENTORY, False, f"falta {INVENTORY}")
    rows = _inventory_paths(_read(path))
    uncovered = sorted(_expected_pieces(root) - set(rows))
    phantom = sorted({r for r in rows if not (root / r).exists()})
    problems = []
    if uncovered:
        problems.append("piezas sin fila: " + ", ".join(uncovered))
    if phantom:
        problems.append("filas con ruta inexistente: " + ", ".join(phantom))
    if problems:
        return Check(CHECK_INVENTORY, False, "; ".join(problems))
    return Check(CHECK_INVENTORY, True, f"{len(set(rows))} piezas inventariadas")


_CHECKS = (
    check_memory,
    check_rules,
    check_agents,
    check_skills,
    check_skill_options,
    check_hooks,
    check_command,
    check_mcp,
    check_credentials,
    check_inventory,
)


def check_all(root: Path) -> list[Check]:
    return [check(Path(root)) for check in _CHECKS]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verifica los mínimos del ecosistema de Claude Code"
    )
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--json", action="store_true", help="salida legible por máquina")
    args = parser.parse_args(argv)

    results = check_all(Path(args.root))
    ok = all(c.ok for c in results)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.json:
        payload = {
            "ok": ok,
            "checks": [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in results],
        }
        print(json.dumps(payload, ensure_ascii=False))
    else:
        for c in results:
            print(f"{'OK   ' if c.ok else 'FALLA'} {c.name}: {c.detail}")
        print("Ecosistema completo." if ok else "Hay mínimos sin cumplir.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
