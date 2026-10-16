"""Ninguna credencial en la configuración ni en la documentación (SC-008, FR-016)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Formas de clave de Anthropic, de token de GitHub y de clave privada, armadas por partes
# para que este archivo no contenga ninguna.
STRICT = re.compile(
    "|".join(
        [
            "sk-" + r"ant-[A-Za-z0-9_-]{20,}",
            "gh[po]" + r"_[A-Za-z0-9]{20,}",
            "github" + r"_pat_[A-Za-z0-9_]{20,}",
            "BEGIN [A-Z ]*" + "PRIVATE KEY",
        ]
    )
)
SCANNED = [".claude", ".mcp.json", "CLAUDE.md", "docs", "mcp_server/CLAUDE.md"]
SKIPPED_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache"}


def files_to_scan(root: Path):
    targets = list(root.glob("*/CLAUDE.md")) + [root / name for name in SCANNED]
    for target in targets:
        if target.is_file():
            yield target
        elif target.is_dir():
            for path in target.rglob("*"):
                if path.is_file() and not SKIPPED_DIRS & set(path.parts):
                    yield path


def hits(root: Path) -> list[str]:
    found = []
    for path in files_to_scan(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if STRICT.search(text):
            found.append(path.relative_to(root).as_posix())
    return found


def test_the_real_repository_has_no_credentials_in_config_or_docs():
    assert hits(ROOT) == []


def test_the_scan_covers_the_configuration_it_claims_to_cover():
    scanned = {p.relative_to(ROOT).as_posix() for p in files_to_scan(ROOT)}
    assert {".mcp.json", "CLAUDE.md", ".claude/settings.json", "docs/ECOSISTEMA.md"} <= scanned


def test_a_sample_credential_built_at_runtime_is_detected(tmp_path):
    (tmp_path / ".claude").mkdir()
    samples = {
        ".claude/settings.json": "sk-" + "ant-" + "a" * 30,
        ".mcp.json": "gh" + "p_" + "b" * 30,
        "docs/nota.md": "github" + "_pat_" + "c" * 30,
        "CLAUDE.md": "-----BEGIN RSA " + "PRIVATE KEY-----",
    }
    for name, content in samples.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    assert sorted(hits(tmp_path)) == sorted(samples)


def test_ordinary_text_is_not_flagged(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("Usa ${GITHUB_PERSONAL_ACCESS_TOKEN} y sk-corto", "utf-8")
    assert hits(tmp_path) == []
