# Contrato: comprobadores de entrega y de documentos

Ambos scripts siguen la forma de `scripts/verify_ecosystem.py`: solo biblioteca estándar, un `Check(name, ok, detail)` por comprobación, salida legible o `--json`, código `0` si todo cumple y `1` si algo falla.

## `python scripts/verify_delivery.py`

```text
python scripts/verify_delivery.py (--zip RUTA | --build [--out RUTA]) [--root RAIZ] [--final] [--json]
```

| Opción | Qué hace |
|---|---|
| `--zip RUTA` | Verifica un zip ya generado. |
| `--build` | Genera el zip del repositorio (`git ls-files` más `.git`) y lo verifica. `--out` fija la ruta; por defecto, `<carpeta superior>/<nombre del repositorio>.zip`. |
| `--root RAIZ` | Raíz del repositorio (por defecto, la del script). |
| `--final` | Añade la comprobación del enlace real del video en el README y ejecuta además las comprobaciones de `verify_docs.py`: una sola verificación final (FR-013). |
| `--json` | `{"ok": bool, "tamano_bytes": N, "desglose": {...}, "checks": [{"name","ok","detail"}]}`. |

Sin `--zip` ni `--build` el script falla con código `2` y un mensaje de uso. Si `git` no está disponible, o la ruta del zip no existe, falla con código `2` y dice la causa.

### Comprobaciones (nombres estables)

| Constante | Nombre | Falla si… |
|---|---|---|
| `CHECK_HISTORY` | historial incluido | falta `.git/HEAD` o `.git/objects/` en el zip |
| `CHECK_DEPENDENCIES` | sin dependencias ni cachés | un componente de ruta es `.venv`, `venv`, `node_modules`, `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache` o `site-packages`, o un miembro termina en `.pyc` |
| `CHECK_SIZE` | tamaño del archivo | el zip supera 50.000.000 bytes; el detalle da el tamaño y el desglose |
| `CHECK_SECRET_FILES` | sin archivos de secretos | hay `.env`, `.env.*` (salvo `.env.example`), `*.pem`, `*.key`, `credentials*.json` o `id_rsa*`; o `.env.example` trae un valor |
| `CHECK_CREDENTIALS` | sin credenciales en los archivos | un archivo de texto contiene una clave de Anthropic, un token de GitHub o un marcador de clave privada |
| `CHECK_HISTORY_CREDENTIALS` | sin credenciales en el historial | `git log --all -G` sobre el historial extraído encuentra esas formas |
| `CHECK_TREE` | coincide con el último commit | los archivos del zip fuera de `.git` no son exactamente los de `HEAD`, o el contenido de alguno difiere del commit (cambios sin confirmar); el detalle nombra el archivo |
| `CHECK_VIDEO` | enlace del video publicado | (solo `--final`) el README sigue con `PENDIENTE` o no trae una URL |
| `CHECK_DOCS` | documentos en orden | (solo `--final`) falla alguna comprobación de `verify_docs.py`; el detalle nombra cuál |

**El detalle de una falla de credenciales nombra el archivo (o el identificador corto del commit) y la clase de hallazgo, nunca el valor.**

## `python scripts/verify_docs.py`

```text
python scripts/verify_docs.py [--root RAIZ] [--json]
```

| Constante | Nombre | Falla si… |
|---|---|---|
| `CHECK_README` | README completo | falta el archivo o alguna sección obligatoria |
| `CHECK_README_LINKS` | enlaces del README | no cita el GitHub Project |
| `CHECK_VIDEO_STATE` | estado del enlace del video | la sección tiene a la vez `PENDIENTE` y una URL, o ninguna de las dos (el detalle dice `pendiente` o `publicado`) |
| `CHECK_PATHS` | rutas citadas existen | una ruta citada en README o DECISIONES.md no existe |
| `CHECK_DECISIONES_TABLE` | once necesidades | la tabla no tiene exactamente las filas 1 a 11, cada una con cinco celdas con contenido |
| `CHECK_DECISIONES_LENGTH` | extensión de DECISIONES.md | supera 1000 palabras (sin sintaxis ni bloques de código) |
| `CHECK_GUION` | guion del video | los tiempos suman más de 5:00, falta algún caso del 1 al 7 o falta el identificador ficticio del caso |

`pytest` ejecuta estas comprobaciones sobre el repositorio real (`scripts/tests/test_docs.py`).
