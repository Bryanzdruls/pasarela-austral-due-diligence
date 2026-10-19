"""El zip de entrega: lo que lo invalida se detecta, y el detalle nunca repite una credencial.

Los repositorios y los zips son sintéticos; los valores con forma de credencial se construyen en
tiempo de ejecución, nunca literales.
"""

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
import verify_delivery as d

SCRIPT = Path(__file__).resolve().parents[1] / "verify_delivery.py"
URL_VIDEO = "https://ejemplo.invalid/video"
README_PENDIENTE = "# Proyecto\n\n- **Video de funcionamiento**: PENDIENTE\n"
README_PUBLICADO = f"# Proyecto\n\n- **Video de funcionamiento**: {URL_VIDEO}\n"


def clave_anthropic():
    return "sk-" + "ant-" + "a" * 30


def token_github():
    return "gh" + "p_" + "b" * 30


def clave_privada():
    return "-----BEGIN RSA " + "PRIVATE KEY-----"


# --------------------------------------------------------------------------- ayudantes


def git(repo, *args):
    base = ["-c", "core.autocrlf=false", "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    proc = subprocess.run(
        ["git", *base, *args], cwd=repo, capture_output=True, text=True, encoding="utf-8"
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def commit(repo, mensaje="cambio"):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", mensaje)


@pytest.fixture
def repo(tmp_path):
    raiz = tmp_path / "proyecto"
    raiz.mkdir()
    archivos = {
        "README.md": README_PENDIENTE,
        ".gitignore": ".venv/\n.env\n.env.*\n!.env.example\n__pycache__/\n",
        ".env.example": "# solo nombres, sin valores\nANTHROPIC_API_KEY=\n",
        "src/app.py": "def main():\n    return 1\n",
        "docs/nota.md": "una nota\n",
    }
    for nombre, contenido in archivos.items():
        ruta = raiz / nombre
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(contenido, encoding="utf-8", newline="")
    git(raiz, "init", "-q", "-b", "main")
    commit(raiz, "primer commit")
    return raiz


@pytest.fixture
def zip_ok(repo, tmp_path):
    return d.build_zip(repo, tmp_path / "entrega.zip")


def editar(origen, destino, agregar=None, quitar=(), reemplazar=None):
    """Copia un zip cambiando miembros. Las rutas son relativas a la carpeta raíz del zip."""
    reemplazar = reemplazar or {}
    with zipfile.ZipFile(origen) as zin:
        nombres = zin.namelist()
        prefijo = nombres[0].split("/", 1)[0] + "/"
        with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zout:
            for nombre in nombres:
                relativo = nombre[len(prefijo) :]
                if any(relativo == q or relativo.startswith(q) for q in quitar):
                    continue
                datos = reemplazar.get(relativo, zin.read(nombre))
                zout.writestr(nombre, datos)
            for relativo, datos in (agregar or {}).items():
                zout.writestr(prefijo + relativo, datos)
    return destino


def fallos(checks):
    return {c.name: c.detail for c in checks if not c.ok}


# --------------------------------------------------------------------------- T003: contenido


def test_a_complete_archive_passes_every_check(zip_ok):
    checks = d.check_zip(zip_ok)
    assert fallos(checks) == {}
    assert {c.name for c in checks} == set(d.ALL_CHECKS) - {d.CHECK_VIDEO, d.CHECK_DOCS}


def test_an_archive_without_history_fails(zip_ok, tmp_path):
    sin = editar(zip_ok, tmp_path / "sin.zip", quitar=(".git/",))
    problemas = fallos(d.check_zip(sin))
    detalle = problemas[d.CHECK_HISTORY]
    assert ".git" in detalle and detalle.startswith("falta") and "HEAD" in detalle
    assert ".git/objects/" in detalle  # dice qué falta, no solo que no se puede leer


def test_a_corrupt_history_fails_even_if_the_files_are_there(zip_ok, tmp_path):
    roto = editar(zip_ok, tmp_path / "roto.zip", reemplazar={".git/HEAD": b"basura\n"})
    assert d.CHECK_HISTORY in fallos(d.check_zip(roto))


@pytest.mark.parametrize(
    "miembro",
    [
        ".venv/lib/x.py",
        "venv/bin/python",
        "node_modules/pkg/index.js",
        "src/__pycache__/app.cpython-312.pyc",
        ".pytest_cache/v/cache",
        ".ruff_cache/0.1/x",
        ".mypy_cache/x.json",
        "lib/site-packages/x.py",
        "suelto.pyc",
    ],
)
def test_installed_dependencies_and_caches_fail_and_are_named(zip_ok, tmp_path, miembro):
    malo = editar(zip_ok, tmp_path / "malo.zip", agregar={miembro: b"x"})
    problemas = fallos(d.check_zip(malo))
    assert d.CHECK_DEPENDENCIES in problemas and miembro in problemas[d.CHECK_DEPENDENCIES]


def test_the_default_limit_is_exactly_fifty_million_bytes():
    assert d.SIZE_LIMIT == 50_000_000


def test_an_archive_over_the_limit_fails_with_its_size_and_where_it_comes_from(zip_ok):
    problemas = fallos(d.check_zip(zip_ok, limit=1000))
    detalle = problemas[d.CHECK_SIZE]
    assert str(zip_ok.stat().st_size) in detalle.replace(".", "").replace(",", "")
    assert ".git" in detalle and "resto" in detalle


@pytest.mark.parametrize(
    "nombre",
    [
        ".env",
        ".env.local",
        ".env.production",
        "config/.env",
        "claves/servidor.pem",
        "claves/servidor.key",
        "credentials.json",
        "config/credentials-prod.json",
        "ssh/id_rsa",
    ],
)
def test_secret_and_environment_files_fail_and_are_named(zip_ok, tmp_path, nombre):
    malo = editar(zip_ok, tmp_path / "malo.zip", agregar={nombre: b"X=1\n"})
    problemas = fallos(d.check_zip(malo))
    assert d.CHECK_SECRET_FILES in problemas and nombre in problemas[d.CHECK_SECRET_FILES]


def test_the_environment_template_with_only_names_is_allowed(zip_ok):
    assert d.CHECK_SECRET_FILES not in fallos(d.check_zip(zip_ok))


@pytest.mark.parametrize("linea", ["ANTHROPIC_API_KEY=algo", 'TOKEN="valor"', "X=1 # comentario"])
def test_the_environment_template_with_a_value_fails(zip_ok, tmp_path, linea):
    malo = editar(
        zip_ok, tmp_path / "malo.zip", reemplazar={".env.example": (linea + "\n").encode()}
    )
    problemas = fallos(d.check_zip(malo))
    assert d.CHECK_SECRET_FILES in problemas and ".env.example" in problemas[d.CHECK_SECRET_FILES]
    assert "algo" not in problemas[d.CHECK_SECRET_FILES]


@pytest.mark.parametrize("fabricar", [clave_anthropic, token_github, clave_privada])
def test_a_credential_inside_a_file_fails_names_the_file_and_never_repeats_the_value(
    zip_ok, tmp_path, fabricar
):
    valor = fabricar()
    malo = editar(
        zip_ok, tmp_path / "malo.zip", agregar={"src/config.py": f'X = "{valor}"\n'.encode()}
    )
    problemas = fallos(d.check_zip(malo))
    detalle = problemas[d.CHECK_CREDENTIALS]
    assert "src/config.py" in detalle
    assert valor not in detalle and valor[8:] not in detalle
    assert all(valor not in texto for texto in problemas.values())


def test_a_binary_or_unreadable_file_does_not_break_the_scan(zip_ok, tmp_path):
    ok = editar(
        zip_ok,
        tmp_path / "ok.zip",
        agregar={"datos/imagen.bin": bytes(range(256)) * 50, "datos/raro.txt": b"\xff\xfe\x00x"},
    )
    assert d.CHECK_CREDENTIALS not in fallos(d.check_zip(ok))


def test_a_credential_committed_and_later_deleted_still_fails_in_the_history(repo, tmp_path):
    valor = token_github()
    (repo / "secreto.txt").write_text(valor + "\n", encoding="utf-8")
    commit(repo, "añade algo")
    (repo / "secreto.txt").unlink()
    commit(repo, "lo borra")
    problemas = fallos(d.check_zip(d.build_zip(repo, tmp_path / "e.zip")))
    assert d.CHECK_HISTORY_CREDENTIALS in problemas
    assert d.CHECK_CREDENTIALS not in problemas  # el árbol actual está limpio
    assert all(valor not in texto for texto in problemas.values())


# --------------------------------------------------------------------------- T004: coincidencia


def test_an_extra_or_missing_file_compared_with_the_last_commit_fails_and_is_named(
    zip_ok, tmp_path
):
    de_mas = editar(zip_ok, tmp_path / "mas.zip", agregar={"extra/suelto.txt": b"x"})
    assert "extra/suelto.txt" in fallos(d.check_zip(de_mas))[d.CHECK_TREE]
    de_menos = editar(zip_ok, tmp_path / "menos.zip", quitar=("docs/nota.md",))
    assert "docs/nota.md" in fallos(d.check_zip(de_menos))[d.CHECK_TREE]


def test_a_versioned_file_with_a_different_content_fails_and_is_named(zip_ok, tmp_path):
    distinto = editar(
        zip_ok, tmp_path / "distinto.zip", reemplazar={"src/app.py": b"def main():\n    return 2\n"}
    )
    assert "src/app.py" in fallos(d.check_zip(distinto))[d.CHECK_TREE]


def test_only_a_difference_in_line_endings_is_not_a_difference(zip_ok, tmp_path):
    crlf = editar(
        zip_ok, tmp_path / "crlf.zip", reemplazar={"src/app.py": b"def main():\r\n    return 1\r\n"}
    )
    assert d.CHECK_TREE not in fallos(d.check_zip(crlf))


def test_uncommitted_changes_to_a_versioned_file_fail_after_building(repo, tmp_path):
    (repo / "src" / "app.py").write_text("def main():\n    return 99\n", encoding="utf-8")
    problemas = fallos(d.check_zip(d.build_zip(repo, tmp_path / "e.zip")))
    assert "src/app.py" in problemas[d.CHECK_TREE]


def test_building_includes_history_and_versioned_files_under_a_root_folder(repo, tmp_path):
    zip_path = d.build_zip(repo, tmp_path / "e.zip")
    with zipfile.ZipFile(zip_path) as z:
        nombres = z.namelist()
    assert all(n.startswith("proyecto/") for n in nombres)
    for esperado in ("proyecto/.git/HEAD", "proyecto/README.md", "proyecto/src/app.py"):
        assert esperado in nombres
    assert any(n.startswith("proyecto/.git/objects/") for n in nombres)
    assert "proyecto/.env.example" in nombres


def test_building_leaves_out_what_is_not_versioned(repo, tmp_path):
    (repo / ".venv" / "lib").mkdir(parents=True)
    (repo / ".venv" / "lib" / "x.py").write_text("x", encoding="utf-8")
    (repo / "src" / "__pycache__").mkdir()
    (repo / "src" / "__pycache__" / "a.pyc").write_bytes(b"x")
    (repo / ".env").write_text("A=1\n", encoding="utf-8")
    (repo / ".env.local").write_text("B=2\n", encoding="utf-8")
    (repo / "borrador.txt").write_text("sin versionar", encoding="utf-8")
    with zipfile.ZipFile(d.build_zip(repo, tmp_path / "e.zip")) as z:
        nombres = " ".join(z.namelist())
    for ausente in (".venv", "__pycache__", "proyecto/.env ", ".env.local", "borrador.txt"):
        assert ausente not in nombres + " "


def test_building_writes_outside_the_repository_by_default(repo):
    destino = d.build_zip(repo)
    try:
        assert destino == repo.parent / "proyecto.zip"
        assert repo not in destino.parents
    finally:
        destino.unlink(missing_ok=True)


# --------------------------------------------------------------------------- T005: video y CLI


def test_the_video_check_only_exists_with_final_and_follows_the_readme(repo, tmp_path):
    pendiente = d.build_zip(repo, tmp_path / "a.zip")
    assert d.CHECK_VIDEO not in {c.name for c in d.check_zip(pendiente)}
    assert d.CHECK_VIDEO in fallos(d.check_zip(pendiente, final=True))

    (repo / "README.md").write_text(README_PUBLICADO, encoding="utf-8", newline="")
    commit(repo, "publica el video")
    publicado = d.build_zip(repo, tmp_path / "b.zip")
    checks = d.check_zip(publicado, final=True)
    assert d.CHECK_VIDEO in {c.name for c in checks} and d.CHECK_VIDEO not in fallos(checks)


@pytest.mark.parametrize(
    "texto, esperado",
    [
        (README_PENDIENTE, "pendiente"),
        (README_PUBLICADO, "publicado"),
        ("# x\n- Video de funcionamiento: PENDIENTE https://a.invalid/v\n", "inconsistente"),
        ("# x\n- Video de funcionamiento:\n", "inconsistente"),
        ("# sin sección de video\n", "ausente"),
    ],
)
def test_the_video_state_is_read_from_the_readme(texto, esperado):
    assert d.video_state(texto) == esperado


def run_cli(*args, env=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )


def test_the_cli_exits_0_on_a_complete_archive_and_1_when_a_check_fails(zip_ok, tmp_path):
    ok = run_cli("--zip", str(zip_ok))
    assert ok.returncode == 0 and "FALLA" not in ok.stdout
    malo = editar(zip_ok, tmp_path / "malo.zip", agregar={".env": b"A=1\n"})
    mal = run_cli("--zip", str(malo))
    assert mal.returncode == 1 and "FALLA" in mal.stdout and d.CHECK_SECRET_FILES in mal.stdout
    assert ".env" in mal.stdout


def test_the_cli_exits_2_without_arguments_or_with_a_missing_zip(tmp_path):
    sin = run_cli()
    assert sin.returncode == 2 and "--zip" in (sin.stdout + sin.stderr)
    falta = run_cli("--zip", str(tmp_path / "no_existe.zip"))
    assert falta.returncode == 2 and "no_existe.zip" in (falta.stdout + falta.stderr)


def test_the_cli_exits_2_when_git_is_not_available(zip_ok, tmp_path):
    vacio = tmp_path / "vacio"
    vacio.mkdir()
    entorno = {**os.environ, "PATH": str(vacio)}
    proc = run_cli("--zip", str(zip_ok), env=entorno)
    assert proc.returncode == 2 and "git" in (proc.stdout + proc.stderr).lower()


def test_json_output_is_a_valid_object_with_size_breakdown_and_every_check(zip_ok):
    proc = run_cli("--zip", str(zip_ok), "--json")
    datos = json.loads(proc.stdout)
    assert datos["ok"] is True and datos["tamano_bytes"] == zip_ok.stat().st_size
    assert set(datos["desglose"]) == {"git", "resto"}
    assert {c["name"] for c in datos["checks"]} == set(d.ALL_CHECKS) - {d.CHECK_VIDEO, d.CHECK_DOCS}


def test_build_through_the_cli_writes_and_verifies_the_archive(repo, tmp_path):
    salida = tmp_path / "salida.zip"
    proc = run_cli("--build", "--root", str(repo), "--out", str(salida))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert salida.is_file()


def test_the_archive_may_or_may_not_have_a_common_root_folder(zip_ok, tmp_path):
    plano = tmp_path / "plano.zip"
    with zipfile.ZipFile(zip_ok) as zin, zipfile.ZipFile(plano, "w") as zout:
        for nombre in zin.namelist():
            zout.writestr(nombre.split("/", 1)[1], zin.read(nombre))
    assert fallos(d.check_zip(plano)) == {}


# --------------------------------------------------------------------------- --final y documentos


@pytest.fixture
def repo_docs(repo):
    """El repositorio sintético con README, DECISIONES.md y guion válidos y el video publicado."""
    import test_docs as td

    td.arbol(
        repo,
        readme_texto=td.readme(video=URL_VIDEO),
        archivos=("scripts/hacer.py",),
    )
    commit(repo, "documentos")
    return repo


def test_final_also_runs_the_document_checks_on_the_content_of_the_zip(repo_docs, tmp_path):
    zip_path = d.build_zip(repo_docs, tmp_path / "e.zip")
    checks = d.check_zip(zip_path, final=True)
    assert d.CHECK_DOCS in {c.name for c in checks}
    assert fallos(checks) == {}
    assert d.CHECK_DOCS not in {c.name for c in d.check_zip(zip_path)}


def test_a_broken_document_in_the_zip_fails_the_final_check_and_names_what_broke(
    repo_docs, tmp_path
):
    with_missing = (repo_docs / "README.md").read_text(encoding="utf-8")
    (repo_docs / "README.md").write_text(with_missing + "\nVer `docs/inventado.md`.\n")
    commit(repo_docs, "cita algo que no existe")
    zip_path = d.build_zip(repo_docs, tmp_path / "e.zip")
    problemas = fallos(d.check_zip(zip_path, final=True))
    assert d.CHECK_DOCS in problemas and "rutas citadas existen" in problemas[d.CHECK_DOCS]
    assert "docs/inventado.md" in problemas[d.CHECK_DOCS]


def test_a_zip_without_the_documents_fails_the_final_check(repo, tmp_path):
    problemas = fallos(d.check_zip(d.build_zip(repo, tmp_path / "e.zip"), final=True))
    assert d.CHECK_DOCS in problemas and "DECISIONES.md" in problemas[d.CHECK_DOCS]


def test_the_final_cli_exits_0_when_everything_is_in_order_and_1_when_it_is_not(
    repo_docs, repo, tmp_path
):
    ok = run_cli("--build", "--final", "--root", str(repo_docs), "--out", str(tmp_path / "a.zip"))
    assert ok.returncode == 0, ok.stdout
    assert d.CHECK_DOCS in ok.stdout and "FALLA" not in ok.stdout
    (repo_docs / "DECISIONES.md").unlink()
    commit(repo_docs, "borra las decisiones")
    mal = run_cli("--build", "--final", "--root", str(repo_docs), "--out", str(tmp_path / "b.zip"))
    assert mal.returncode == 1 and d.CHECK_DOCS in mal.stdout and "FALLA" in mal.stdout


# ------------------------------------------------------- revisión: .git, UTF-16 y miembros del zip


@pytest.mark.parametrize(
    "miembro, contenido",
    [
        (".git/config", '[remote "origin"]\n\turl = https://u:{valor}@github.com/x/y.git\n'),
        (".git/hooks/pre-push", "#!/bin/sh\nexport CLAVE={valor}\n"),
        (".git/COMMIT_EDITMSG", "mensaje con {valor}\n"),
        (".git/packed-refs", "# {valor}\n"),
    ],
)
def test_a_credential_in_the_text_files_of_the_git_folder_fails_and_is_not_repeated(
    zip_ok, tmp_path, miembro, contenido
):
    valor = token_github()
    datos = contenido.format(valor=valor).encode()
    malo = editar(zip_ok, tmp_path / "malo.zip", quitar=(miembro,), agregar={miembro: datos})
    detalle = fallos(d.check_zip(malo))[d.CHECK_CREDENTIALS]
    assert miembro in detalle and valor not in detalle


def test_a_credential_added_as_a_new_file_inside_the_git_folder_fails(zip_ok, tmp_path):
    malo = editar(
        zip_ok, tmp_path / "malo.zip", agregar={".git/hooks/pre-commit": token_github().encode()}
    )
    assert ".git/hooks/pre-commit" in fallos(d.check_zip(malo))[d.CHECK_CREDENTIALS]


def test_a_secret_file_name_inside_the_git_folder_also_fails(zip_ok, tmp_path):
    malo = editar(zip_ok, tmp_path / "malo.zip", agregar={".git/" + ".env": b"A=1\n"})
    assert ".git/.env" in fallos(d.check_zip(malo))[d.CHECK_SECRET_FILES]


@pytest.mark.parametrize("codificacion", ["utf-16", "utf-16-le", "utf-16-be", "utf-32"])
def test_a_credential_written_in_a_wide_encoding_is_found(zip_ok, tmp_path, codificacion):
    valor = clave_anthropic()
    datos = f"notas: {valor}\n".encode(codificacion)
    malo = editar(zip_ok, tmp_path / "malo.zip", agregar={"src/notas.txt": datos})
    detalle = fallos(d.check_zip(malo))[d.CHECK_CREDENTIALS]
    assert "src/notas.txt" in detalle and valor not in detalle


@pytest.mark.parametrize(
    "nombre",
    [
        "." + "envrc",
        "prod" + ".env",
        "config/prod" + ".env",
        ".netrc",
        ".pgpass",
        ".pypirc",
        ".npmrc",
        ".aws/credentials",
        "credentials",
        "id_ed25519",
        "id_ecdsa",
        "claves/llave.p12",
        "claves/llave.pfx",
    ],
)
def test_more_secret_file_names_fail_and_are_named(zip_ok, tmp_path, nombre):
    malo = editar(zip_ok, tmp_path / "malo.zip", agregar={nombre: b"x"})
    problemas = fallos(d.check_zip(malo))
    assert d.CHECK_SECRET_FILES in problemas and nombre in problemas[d.CHECK_SECRET_FILES]


def test_a_zip_with_members_outside_the_root_folder_is_rejected_with_a_message(zip_ok, tmp_path):
    fuera = tmp_path / "fuera.zip"
    with zipfile.ZipFile(zip_ok) as zin, zipfile.ZipFile(fuera, "w") as zout:
        for nombre in zin.namelist():
            zout.writestr(nombre, zin.read(nombre))
        zout.writestr("otro/clave.txt", b"suelto")
    with pytest.raises(d.UsageError, match="fuera de la carpeta raíz"):
        d.check_zip(fuera)
    proc = run_cli("--zip", str(fuera))
    assert proc.returncode == 2 and "fuera de la carpeta raíz" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_a_zip_with_repeated_member_names_is_rejected(zip_ok, tmp_path):
    repetido = tmp_path / "repetido.zip"
    with zipfile.ZipFile(zip_ok) as zin, zipfile.ZipFile(repetido, "w") as zout:
        for nombre in zin.namelist():
            zout.writestr(nombre, zin.read(nombre))
        with pytest.warns(UserWarning):  # zipfile avisa del nombre duplicado
            zout.writestr("proyecto/src/app.py", b"otra copia")
    with pytest.raises(d.UsageError, match="repetidos"):
        d.check_zip(repetido)
    proc = run_cli("--zip", str(repetido))
    assert proc.returncode == 2 and "src/app.py" in proc.stderr


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("- Video de funcionamiento: http://TODO\n", "inconsistente"),
        ("- Video de funcionamiento: https://todo\n", "inconsistente"),
        ("- Video de funcionamiento: https://\n", "inconsistente"),
        ("- Video de funcionamiento: https://youtu.be/abc\n", "publicado"),
    ],
)
def test_a_video_link_needs_to_be_a_well_formed_https_url(texto, esperado):
    assert d.video_state(texto) == esperado


# ------------------------------------------------------- revisión, ronda 2


@pytest.mark.parametrize("nombre", ["notas.idx", "datos/x.pack", "src/paquete.pack"])
@pytest.mark.parametrize("codificacion", ["utf-8", "utf-16"])
def test_a_versioned_file_named_like_a_git_pack_is_still_scanned(
    zip_ok, tmp_path, nombre, codificacion
):
    """Solo los paquetes de .git se saltan por su nombre; un archivo del proyecto, no."""
    valor = clave_anthropic()
    malo = editar(
        zip_ok, tmp_path / "malo.zip", agregar={nombre: f"x {valor}\n".encode(codificacion)}
    )
    detalle = fallos(d.check_zip(malo))[d.CHECK_CREDENTIALS]
    assert nombre in detalle and valor not in detalle


@pytest.mark.parametrize("codificacion", ["utf-8-sig", "utf-16", "utf-16-le", "utf-32"])
def test_the_environment_template_saved_with_a_byte_order_mark_or_wide_is_still_empty(
    zip_ok, tmp_path, codificacion
):
    plantilla = "# a=b\nANTHROPIC_API_KEY=\n".encode(codificacion)
    ok = editar(zip_ok, tmp_path / "ok.zip", reemplazar={".env.example": plantilla})
    assert d.CHECK_SECRET_FILES not in fallos(d.check_zip(ok))


def test_a_value_in_a_wide_encoded_template_is_still_found(zip_ok, tmp_path):
    plantilla = "ANTHROPIC_API_KEY=algo\n".encode("utf-16")
    malo = editar(zip_ok, tmp_path / "malo.zip", reemplazar={".env.example": plantilla})
    assert ".env.example" in fallos(d.check_zip(malo))[d.CHECK_SECRET_FILES]
