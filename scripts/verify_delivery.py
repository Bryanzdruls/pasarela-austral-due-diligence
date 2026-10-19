"""Construye y verifica el zip de entrega (solo biblioteca estándar).

Uso:
    python scripts/verify_delivery.py --build [--out RUTA] [--final] [--json]
    python scripts/verify_delivery.py --zip RUTA [--final] [--json]

Comprueba lo que el enunciado exige del archivo: el historial (`.git`) incluido, sin dependencias
instaladas, de 50 MB como máximo y sin ningún archivo de entorno ni credencial (una credencial en
el zip es una falta grave). Falla cerrado: ante la duda, rechaza. Código de salida 0 si cumple, 1 si
algo falla y 2 si no se pudo comprobar (uso incorrecto, zip inexistente o sin `git`).

El detalle de una falla de credenciales nombra el archivo o el commit, nunca el valor.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath

from verify_ecosystem import Check

CHECK_HISTORY = "historial incluido"
CHECK_DEPENDENCIES = "sin dependencias ni cachés"
CHECK_SIZE = "tamaño del archivo"
CHECK_SECRET_FILES = "sin archivos de secretos"
CHECK_CREDENTIALS = "sin credenciales en los archivos"
CHECK_HISTORY_CREDENTIALS = "sin credenciales en el historial"
CHECK_TREE = "coincide con el último commit"
CHECK_VIDEO = "enlace del video publicado"
CHECK_DOCS = "documentos en orden"

ALL_CHECKS = (
    CHECK_HISTORY,
    CHECK_DEPENDENCIES,
    CHECK_SIZE,
    CHECK_SECRET_FILES,
    CHECK_CREDENTIALS,
    CHECK_HISTORY_CREDENTIALS,
    CHECK_TREE,
    CHECK_VIDEO,
    CHECK_DOCS,
)

# El límite decimal es el más estricto: cumplirlo cumple cualquier lectura de "50 MB".
SIZE_LIMIT = 50_000_000
MAX_SCANNED_BYTES = 2_000_000
MAX_LISTED = 5

DEPENDENCY_DIRS = frozenset(
    {
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "site-packages",
    }
)

# Formas de credencial, armadas por partes para que este archivo no contenga ninguna.
_CLASSES = {
    "clave de Anthropic": "sk-" + "ant-[A-Za-z0-9_-]{20,}",
    "token de GitHub": "gh[pousr]" + "_[A-Za-z0-9]{20,}|github" + "_pat_[A-Za-z0-9_]{20,}",
    "clave privada": "BEGIN [A-Z ]*" + "PRIVATE KEY",
}
SECRET_PATTERN = "|".join(_CLASSES.values())
_SECRET = re.compile(SECRET_PATTERN)
_CLASS_RES = {name: re.compile(pattern) for name, pattern in _CLASSES.items()}

_URL = re.compile(r"https://[^\s/]+\.[^\s/]+\S*")


class UsageError(Exception):
    """No se pudo comprobar (uso incorrecto, zip inexistente, sin git): código de salida 2."""


# --------------------------------------------------------------------------- git


def _require_git() -> None:
    if shutil.which("git") is None:
        raise UsageError(
            "git no está disponible en el PATH: hace falta para verificar el historial"
        )


def _git(cwd: Path, *args: str) -> bytes:
    proc = subprocess.run(
        ["git", "-c", "safe.directory=*", "-c", "core.quotepath=off", *args],
        cwd=cwd,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", "replace").strip() or "git falló")
    return proc.stdout


def _names(output: bytes) -> list[str]:
    return [item.decode("utf-8", "replace") for item in output.split(b"\0") if item]


# --------------------------------------------------------------------------- construcción


def build_zip(root: Path | str, out: Path | str | None = None) -> Path:
    """Zip del repositorio: lo versionado (`git ls-files`) más toda la carpeta `.git`.

    Parte de lo versionado, así que el entorno virtual, las cachés y cualquier archivo local sin
    versionar (un archivo de entorno con secretos) quedan fuera por construcción.
    """
    _require_git()
    root = Path(root).resolve()
    destino = Path(out) if out else root.parent / f"{root.name}.zip"
    try:
        versionados = _names(_git(root, "ls-files", "-z"))
    except RuntimeError as error:
        raise UsageError(f"{root} no es un repositorio git: {error}") from None
    base = root.name
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as archivo:
        for relativo in versionados:
            origen = root / relativo
            if origen.is_file():
                archivo.write(origen, f"{base}/{relativo}")
        carpeta_git = root / ".git"
        for origen in sorted(carpeta_git.rglob("*")):
            if origen.is_file():
                archivo.write(origen, f"{base}/.git/{origen.relative_to(carpeta_git).as_posix()}")
    return destino


# --------------------------------------------------------------------------- lectura del zip


def _prefix(names: list[str]) -> str:
    """Carpeta raíz común del zip (con barra final), o '' si los miembros están en la raíz."""
    for name in names:
        if name == ".git/HEAD":
            return ""
        if name.endswith("/.git/HEAD"):
            return name[: -len(".git/HEAD")]
    firsts = {name.split("/", 1)[0] for name in names if "/" in name}
    sueltos = [name for name in names if "/" not in name]
    if len(firsts) == 1 and not sueltos:
        return firsts.pop() + "/"
    return ""


def _is_safe(name: str) -> bool:
    ruta = PurePosixPath(name)
    return not ruta.is_absolute() and ".." not in ruta.parts and ":" not in name.split("/")[0]


def size_info(zip_path: Path) -> tuple[int, dict[str, int]]:
    """Tamaño del zip y desglose (comprimido) entre `.git` y el resto."""
    with zipfile.ZipFile(zip_path) as archivo:
        infos = [i for i in archivo.infolist() if not i.is_dir()]
        pref = _prefix([i.filename for i in infos])
        git = sum(i.compress_size for i in infos if i.filename[len(pref) :].startswith(".git/"))
        resto = sum(i.compress_size for i in infos) - git
    return zip_path.stat().st_size, {"git": git, "resto": resto}


def _listed(names: list[str]) -> str:
    mostrados = ", ".join(sorted(names)[:MAX_LISTED])
    return mostrados + (f" y {len(names) - MAX_LISTED} más" if len(names) > MAX_LISTED else "")


# --------------------------------------------------------------------------- comprobaciones


def video_state(readme: str) -> str:
    """Estado del enlace del video en el README: pendiente, publicado, inconsistente o ausente."""
    lineas = [x for x in readme.splitlines() if "video de funcionamiento" in x.lower()]
    if not lineas:
        return "ausente"
    texto = " ".join(lineas)
    hay_url, hay_pendiente = bool(_URL.search(texto)), "PENDIENTE" in texto
    if hay_url and not hay_pendiente:
        return "publicado"
    if hay_pendiente and not hay_url:
        return "pendiente"
    return "inconsistente"


def _check_history(repo: Path, rels: list[str]) -> Check:
    faltan = []
    if ".git/HEAD" not in rels:
        faltan.append(".git/HEAD")
    if not any(r.startswith(".git/objects/") for r in rels):
        faltan.append(".git/objects/")
    if faltan:
        return Check(
            CHECK_HISTORY, False, "falta la carpeta .git del historial: " + ", ".join(faltan)
        )
    try:
        cuenta = int(_git(repo, "rev-list", "--count", "--all").decode().strip() or 0)
    except (RuntimeError, ValueError) as error:
        return Check(CHECK_HISTORY, False, f"el historial de .git no se puede leer: {error}")
    if cuenta == 0:
        return Check(CHECK_HISTORY, False, "el historial de .git no tiene ningún commit")
    return Check(CHECK_HISTORY, True, f"{cuenta} commits en .git")


def _check_dependencies(rels: list[str]) -> Check:
    malos = []
    for rel in rels:
        if rel.startswith(".git/"):
            continue
        partes = rel.split("/")
        if DEPENDENCY_DIRS & set(partes[:-1]) or rel.endswith(".pyc"):
            malos.append(rel)
    if malos:
        return Check(
            CHECK_DEPENDENCIES, False, "dependencias o cachés dentro del zip: " + _listed(malos)
        )
    return Check(CHECK_DEPENDENCIES, True, "sin entornos virtuales, node_modules ni cachés")


def _check_size(zip_path: Path, limit: int) -> Check:
    total, desglose = size_info(zip_path)
    detalle = (
        f"tamaño {total} bytes (límite {limit}): .git {desglose['git']} y resto {desglose['resto']}"
    )
    return Check(CHECK_SIZE, total <= limit, detalle)


def _env_template_values(texto: str) -> list[int]:
    lineas = []
    texto = texto.replace("\ufeff", "").replace("\x00", "")  # marca de orden de bytes y UTF-16/32
    for numero, linea in enumerate(texto.splitlines(), start=1):
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        valor = linea.split("=", 1)[1].strip()
        if valor and not valor.startswith("#"):
            lineas.append(numero)
    return lineas


_SECRET_NAMES = frozenset({".envrc", ".netrc", ".pgpass", ".pypirc", ".npmrc", "credentials"})
_SECRET_SUFFIXES = (".env", ".pem", ".key", ".p12", ".pfx")
_SECRET_PREFIXES = ("id_rsa", "id_dsa", "id_ecdsa", "id_ed25519")


def _is_secret_file(nombre: str) -> bool:
    n = nombre.lower()
    if n.startswith(".env.") and n != ".env.example":
        return True
    if n in _SECRET_NAMES or n.endswith(_SECRET_SUFFIXES) or n.startswith(_SECRET_PREFIXES):
        return True
    return bool(re.fullmatch(r"credentials.*\.json", n))


def _check_secret_files(archivo: zipfile.ZipFile, pref: str, rels: list[str]) -> Check:
    malos = [r for r in rels if _is_secret_file(r.split("/")[-1])]
    problemas = list(malos)
    for rel in rels:
        if rel.split("/")[-1].lower() == ".env.example" and not rel.startswith(".git/"):
            texto = archivo.read(pref + rel).decode("utf-8", "ignore")
            if lineas := _env_template_values(texto):
                problemas.append(f"{rel} (trae un valor en la línea {lineas[0]})")
    if problemas:
        return Check(
            CHECK_SECRET_FILES, False, "archivos de secretos o de entorno: " + _listed(problemas)
        )
    return Check(
        CHECK_SECRET_FILES,
        True,
        "ningún archivo de entorno ni de claves (la plantilla va sin valores)",
    )


def _texts(datos: bytes) -> list[str]:
    """El archivo leído como texto; con ceros además sin ellos (UTF-16 y UTF-32 de texto ASCII)."""
    textos = [datos.decode("utf-8", "ignore")]
    if b"\x00" in datos:
        textos.append(datos.replace(b"\x00", b"").decode("utf-8", "ignore"))
    return textos


def _is_git_binary(rel: str) -> bool:
    """Objetos y paquetes de git: comprimidos, los cubre `git log -G` sobre el historial."""
    return rel.startswith(".git/") and (
        rel.startswith(".git/objects/") or rel.endswith((".pack", ".idx"))
    )


def _check_credentials(archivo: zipfile.ZipFile, pref: str, rels: list[str]) -> Check:
    hallazgos: list[str] = []
    for rel in rels:
        info = archivo.getinfo(pref + rel)
        if _is_git_binary(rel) or info.file_size > MAX_SCANNED_BYTES:
            continue
        textos = _texts(archivo.read(pref + rel))
        if any(_SECRET.search(t) for t in textos):
            clase = next(n for n, rx in _CLASS_RES.items() if any(rx.search(t) for t in textos))
            hallazgos.append(f"{rel} ({clase})")
    if hallazgos:
        return Check(
            CHECK_CREDENTIALS, False, "algo con forma de credencial en: " + _listed(hallazgos)
        )
    return Check(CHECK_CREDENTIALS, True, "ningún archivo contiene algo con forma de credencial")


def _check_history_credentials(repo: Path, history_ok: bool) -> Check:
    if not history_ok:
        return Check(
            CHECK_HISTORY_CREDENTIALS, False, "no se pudo comprobar: el historial no es legible"
        )
    try:
        salida = _git(repo, "log", "--all", "--format=%h", "-G", SECRET_PATTERN)
    except RuntimeError as error:
        return Check(
            CHECK_HISTORY_CREDENTIALS, False, f"no se pudo comprobar el historial: {error}"
        )
    commits = salida.decode().split()
    if commits:
        return Check(
            CHECK_HISTORY_CREDENTIALS,
            False,
            "algo con forma de credencial en el historial, commits: " + _listed(commits),
        )
    return Check(
        CHECK_HISTORY_CREDENTIALS, True, "el historial no contiene nada con forma de credencial"
    )


def _head_blobs(repo: Path, paths: list[str]) -> dict[str, bytes | None]:
    entrada = "".join(f"HEAD:{p}\n" for p in paths).encode()
    proc = subprocess.run(
        ["git", "-c", "safe.directory=*", "cat-file", "--batch"],
        cwd=repo,
        input=entrada,
        capture_output=True,
    )
    salida, pos, blobs = proc.stdout, 0, {}
    for ruta in paths:
        fin = salida.index(b"\n", pos)
        cabecera = salida[pos:fin].split()
        if cabecera[-1] == b"missing":
            blobs[ruta], pos = None, fin + 1
            continue
        tamano = int(cabecera[2])
        blobs[ruta] = salida[fin + 1 : fin + 1 + tamano]
        pos = fin + 1 + tamano + 1
    return blobs


def _normalized(datos: bytes) -> bytes:
    return datos.replace(b"\r\n", b"\n")


def _check_tree(
    archivo: zipfile.ZipFile, pref: str, repo: Path, rels: list[str], history_ok: bool
) -> Check:
    if not history_ok:
        return Check(CHECK_TREE, False, "no se pudo comprobar: el historial no es legible")
    try:
        en_head = set(_names(_git(repo, "ls-tree", "-r", "--name-only", "-z", "HEAD")))
    except RuntimeError as error:
        return Check(CHECK_TREE, False, f"no se pudo leer el último commit: {error}")
    en_zip = {r for r in rels if not r.startswith(".git/")}
    de_mas, de_menos = sorted(en_zip - en_head), sorted(en_head - en_zip)
    comunes = sorted(en_zip & en_head)
    distintos = []
    if comunes:
        blobs = _head_blobs(repo, comunes)
        for ruta in comunes:
            en_commit = blobs.get(ruta)
            if en_commit is None or _normalized(archivo.read(pref + ruta)) != _normalized(
                en_commit
            ):
                distintos.append(ruta)
    partes = []
    if de_mas:
        partes.append("de más: " + _listed(de_mas))
    if de_menos:
        partes.append("de menos: " + _listed(de_menos))
    if distintos:
        partes.append("con contenido distinto del commit: " + _listed(distintos))
    if partes:
        return Check(
            CHECK_TREE, False, "el zip no coincide con el último commit; " + "; ".join(partes)
        )
    return Check(CHECK_TREE, True, f"{len(comunes)} archivos idénticos a los del último commit")


def check_zip(zip_path: Path | str, final: bool = False, limit: int = SIZE_LIMIT) -> list[Check]:
    """Todas las comprobaciones de un zip de entrega; `final` añade las del enlace del video."""
    zip_path = Path(zip_path)
    if not zip_path.is_file():
        raise UsageError(f"No existe el zip: {zip_path}")
    _require_git()
    with zipfile.ZipFile(zip_path) as archivo:
        miembros = [i.filename for i in archivo.infolist() if not i.is_dir()]
        if not all(_is_safe(n) for n in miembros):
            raise UsageError("el zip tiene miembros con una ruta insegura; no se extrae")
        if repetidos := sorted({n for n, veces in Counter(miembros).items() if veces > 1}):
            raise UsageError("el zip tiene miembros repetidos: " + _listed(repetidos))
        pref = _prefix(miembros)
        if fuera := [n for n in miembros if not n.startswith(pref)]:
            raise UsageError(
                f"el zip tiene miembros fuera de la carpeta raíz «{pref}»: " + _listed(fuera)
            )
        rels = [n[len(pref) :] for n in miembros]
        with tempfile.TemporaryDirectory() as temporal:
            archivo.extractall(temporal)
            repo = Path(temporal) / pref.rstrip("/") if pref else Path(temporal)
            historia = _check_history(repo, rels)
            checks = [
                historia,
                _check_dependencies(rels),
                _check_size(zip_path, limit),
                _check_secret_files(archivo, pref, rels),
                _check_credentials(archivo, pref, rels),
                _check_history_credentials(repo, historia.ok),
                _check_tree(archivo, pref, repo, rels, historia.ok),
            ]
            if final:
                readme = (
                    (repo / "README.md").read_text("utf-8", "ignore")
                    if (repo / "README.md").is_file()
                    else ""
                )
                estado = video_state(readme)
                checks.append(
                    Check(
                        CHECK_VIDEO, estado == "publicado", f"estado del enlace del video: {estado}"
                    )
                )
                checks.append(_check_docs(repo))
    return checks


def _check_docs(repo: Path) -> Check:
    """Las comprobaciones de documentos sobre el contenido del zip, no sobre el árbol de trabajo."""
    import verify_docs  # import tardío: verify_docs importa este módulo

    rotos = [c for c in verify_docs.check_all(repo) if not c.ok]
    if rotos:
        detalle = "; ".join(f"{c.name}: {c.detail}" for c in rotos)
        return Check(CHECK_DOCS, False, detalle)
    return Check(CHECK_DOCS, True, "README, DECISIONES.md y el guion pasan sus comprobaciones")


# --------------------------------------------------------------------------- línea de órdenes


def main(argv: list[str] | None = None) -> int:
    for flujo in (sys.stdout, sys.stderr):  # los acentos llegan legibles también en Windows
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Construye y verifica el zip de entrega")
    parser.add_argument("--zip", help="verifica un zip ya generado")
    parser.add_argument("--build", action="store_true", help="genera el zip y lo verifica")
    parser.add_argument(
        "--out", help="ruta del zip con --build (por defecto, junto al repositorio)"
    )
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument(
        "--final", action="store_true", help="exige también el enlace real del video"
    )
    parser.add_argument("--json", action="store_true", help="salida legible por máquina")
    args = parser.parse_args(argv)
    if not args.zip and not args.build:
        parser.error("indica --zip RUTA para verificar un zip o --build para generarlo")

    try:
        zip_path = build_zip(args.root, args.out) if args.build else Path(args.zip)
        checks = check_zip(zip_path, final=args.final)
        total, desglose = size_info(zip_path)
    except UsageError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    ok = all(c.ok for c in checks)
    if args.json:
        carga = {
            "ok": ok,
            "tamano_bytes": total,
            "desglose": desglose,
            "checks": [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in checks],
        }
        print(json.dumps(carga, ensure_ascii=False))
    else:
        print(f"Zip: {zip_path}")
        for c in checks:
            print(f"{'OK   ' if c.ok else 'FALLA'} {c.name}: {c.detail}")
        print("El zip cumple lo que exige el enunciado." if ok else "El zip NO se puede entregar.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
