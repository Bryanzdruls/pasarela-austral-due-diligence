# Verificación: README, DECISIONES.md, guion de video y zip de entrega

## Línea base (T001)
En `main` (merge del PR #23, `f11f80b`) la suite tenía 1.528 pruebas en verde, `ruff check` y `ruff format --check` limpios y `verify_ecosystem.py` con código 0. La rama parte de ahí.

## Historia 3: el zip de entrega
**Pruebas primero (T006).** `scripts/tests/test_verify_delivery.py` falló por la razón esperada: `ModuleNotFoundError: No module named 'verify_delivery'`.

**Implementación (T007, T008).** 51 pruebas en verde. Una falló al principio por un defecto real del script, no de la prueba: el mensaje de error salía por `stderr` con la codificación local de Windows (cp1252) y llegaba ilegible, el mismo defecto que ya apareció en los hooks del #9. Se fija UTF-8 en `stdout` y `stderr` al principio de `main`.

**Sobre el repositorio real (T009, informativo).** `python scripts/verify_delivery.py --build`: historial con 84 commits, 3.384.955 bytes (`.git` 2.350.438 y resto 707.663, frente a un límite de 50.000.000), sin dependencias, sin archivos de secretos y sin credenciales en los archivos ni en el historial. Falló solo `coincide con el último commit`, porque el `.gitignore` tenía un cambio sin confirmar: el caso que la comparación de contenido (hallazgo C1 del análisis) existe para detectar.

## Historias 1 y 2: README y DECISIONES.md
**Pruebas primero (T011).** `scripts/tests/test_docs.py` falló por la razón esperada: `ModuleNotFoundError: No module named 'verify_docs'`.

**Implementación (T012, T013).** 48 pruebas sintéticas en verde (las 49 con la del repositorio real); solo fallaba la del repositorio real, porque aún no existían los documentos.

**El comprobador detectó un error mío (T016).** Al escribir `DECISIONES.md` cité entre comillas invertidas `CLAUDE.local.md` y `settings.local.json` como rutas; son archivos personales que, por diseño, no existen en el repositorio, y `rutas citadas existen` falló nombrándolos. Se corrigió el documento (se nombran sin marcar como ruta) y no el comprobador.

**Resultado sobre el repositorio real.** `python scripts/verify_docs.py`: las 8 secciones del README, el enlace al GitHub Project, el video `pendiente`, todas las rutas citadas existen, las 11 necesidades con sus cinco columnas y 571 palabras en `DECISIONES.md` (máximo 1.000).

**Revisión cruzada de `DECISIONES.md` con `docs/ECOSISTEMA.md` (T016, hallazgo C2).** Cada fila se contrastó con su fila de origen: 1 (memoria y su importación), 2 (preferencias locales ignoradas por git), 3 (regla con `paths`), 4 (hook de especificación, también por terminal), 5 (hook de datos reales y su regla), 6 (`permissions.deny` y el hook de secretos, plantilla accesible), 7 (hook posterior a la edición, no bloquea), 8 (revisor de código de solo lectura lanzado por `/abrir-pr`), 9 (revisor de cumplimiento y su skill con `context: fork`), 10 (skills sobre el MCP de GitHub; un hook no puede llamar al MCP) y 11 (plugin y catálogo en este repositorio, hook autocontenido). Sin contradicciones ni decisiones nuevas. Una diferencia deliberada de nivel de detalle: `ECOSISTEMA.md` lista 25 piezas y `DECISIONES.md` solo las que resuelven cada necesidad; esta última no menciona `verify_ecosystem.py` ni el MCP propio, que no son una de las once necesidades.

## Historia 4: guion del video
**Pruebas primero (T019).** Las pruebas de `CHECK_GUION` fallaron por la razón esperada: `AttributeError: module 'verify_docs' has no attribute 'CHECK_GUION'`. Tras implementarlo (T020), 70 pruebas sintéticas en verde y solo fallaba la del repositorio real, porque aún no existía `docs/VIDEO.md`.

**Ensayo con el modelo real (T021, 2026-10-17).** Se corrieron los siete casos contra la interfaz con el modelo real, uno detrás de otro (el caso 6 en un servidor reiniciado con la falla de noticias), y se cronometraron:

| Caso | Segundos | Qué se vio |
|---|---|---|
| 1 | 47,7 | 4 delegaciones, 6 hallazgos, informe «escalar a cumplimiento» y escalamiento |
| 2 | 38,7 | 5 hallazgos, informe «habilitar», sin escalamiento |
| 3 | 45,7 | hallazgo de listas del representante, informe y escalamiento |
| 4 | 59,7 (25,2 + 34,5) | dos turnos; informe a nombre de `CO-CA-0004` tras el identificador |
| 5 | 55,5 | **sin bloqueo**: el modelo pasó por el registro y escaló el caso; el hook de la regla 1 no llegó a ejercerse |
| 7 | 54,2 | informe y escalamiento por la contradicción de fechas |
| 6 | 49,4 | un bloqueo real por el tope de reintentos e informe «no habilitar» con «Sin cubrir: las noticias» |

Los casos 1 a 5 y 7 sumaron 301,6 s en serie; con el 6 y el reinicio de la interfaz, una grabación en directo pasaría de seis minutos. Por eso el guion pide acelerar las esperas al editar: con los tiempos del video editado el total es 4:35 (máximo 5:00).

**Hallazgo de logística que el ensayo destapó.** El caso 6 solo funciona en la interfaz si el servidor se arranca con `PASARELA_FAULTS=noticias` (la variable pasa al servidor MCP); hay que reiniciarla y por eso el guion graba el caso 6 al final. No estaba en `docs/INTERFAZ.md`; el README y el guion ya lo dicen.

**No verificado:** el ensayo se hizo por la API de la interfaz (la misma que usa la página), no con una grabación de pantalla; la velocidad ×6 de la edición es una propuesta, no se probó con un editor.

## Verificación final única (T023 a T026, hallazgo I1 del análisis)
`python scripts/verify_delivery.py --build --final` ejecuta ahora, además del enlace del video, las comprobaciones de `verify_docs.py` **sobre el contenido del zip** (no sobre el árbol de trabajo): una sola orden dice si se puede entregar. Pruebas primero: 4 fallaron por la razón esperada (`CHECK_DOCS` no existía) y la que comprueba que sin `--final` no existe ya pasaba. Tras implementarlo, 126 pruebas en verde entre `test_verify_delivery.py` y `test_docs.py`.

## SC-001: los pasos del README en una copia limpia (T027)
Se siguieron los pasos del README tal cual en una copia limpia (`git clone` de la rama a un directorio temporal, que se borró después), en esta máquina de desarrollo:

| Paso | Tiempo |
|---|---|
| `git clone` | 2 s |
| `python -m uv sync` | 2 s |
| `python -m uv run pytest -q` | 185 s (1.654 pruebas en verde, sin clave) |
| Arrancar la interfaz y comprobar que responde (`/api/estado` y la página, HTTP 200) | 3 s |
| **Total** | **≈ 192 s (3 min 12 s)** |

**Cumple** el límite de cinco minutos con 1 min 48 s de margen. **Límites de la medida:** la caché de `uv` estaba caliente (en un equipo sin caché, la instalación tarda más: no se midió); un equipo más lento que este alargaría las pruebas, que son el 96 % del tiempo. Por eso el README ofrece una comprobación rápida (los siete casos sin modelo, en segundos). La interfaz arranca sin clave y solo avisa de que faltará para conversar. No se probó en Linux ni macOS.

## Verificación por mutación de los comprobadores (T028)
24 mutaciones (14 de `verify_delivery.py` y 9 de `verify_docs.py`, más un control): historial sin comprobar, entornos virtuales y cachés aceptados, tamaño que nunca falla y límite subido a 60 MB, archivo de entorno local y plantilla con valor aceptados, contenido sin escanear, historial sin escanear, nombres y contenido sin comparar con el último commit, enlace con `PENDIENTE` contado como publicado, `--final` sin documentos, detalle que repite el valor, `--build` que empaqueta lo no versionado, fila repetida de `DECISIONES.md`, código contado como palabras, rutas sin comprobar, tiempos sumados a cero, límite de palabras subido, secciones del README no exigidas, enlace al Project no exigido, guion que puede pasarse de cinco minutos y caso sin su identificador. **Todas detectadas; el control sin mutación pasa.**

Una sobrevivió la primera vez (**D1**, no detectar la falta de `.git/HEAD` y `.git/objects/`): sin esos archivos otra ruta del código también falla (la lectura del historial), pero con un mensaje peor. El efecto era el mismo y el mensaje no. Se endureció la prueba para exigir que el detalle diga qué falta (`falta … HEAD … .git/objects/`) y la mutación pasó a detectarse.

## Trazabilidad (T029)
`docs/TRAZABILIDAD.md`: D2 y D3 a Hecho, D5 (zip) y D6 (video) a Parcial con lo que queda en manos de la persona, la nota del ticket #11 y el resumen recalculado (Hecho 70, Parcial 5, Falta 2).

## Cierre (T030, T031)
**Recuento final.** `python -m uv run pytest -q`: **1.654 pruebas en verde** (1.528 en `main` más 126 nuevas: 55 de `test_verify_delivery.py` y 71 de `test_docs.py`), `ruff check` y `ruff format --check` limpios, `python scripts/verify_ecosystem.py` con código 0 y `python scripts/verify_docs.py` con todo en orden. Ninguna prueba anterior se modificó (SC-007).

**El zip real (SC-005).** `python scripts/verify_delivery.py --build` sobre el repositorio confirmado: 89 commits en `.git`, 3.566.535 bytes (`.git` 2.487.638 y resto 738.391, frente a 50.000.000), sin entornos virtuales ni cachés, sin archivos de entorno ni de claves, sin credenciales en los archivos ni en el historial y **313 archivos idénticos a los del último commit**. Código de salida 0.

**Con `--final` (hoy).** Falla solo en `enlace del video publicado: pendiente` y dice «El zip NO se puede entregar»; `documentos en orden` pasa. Es lo esperado: el video lo graba y publica la persona. Pasará cuando pegue el enlace en el README, haga el commit y vuelva a generar el zip.

**«Dos páginas».** Se midió como 1.000 palabras (un sustituto, sin generar un PDF): `DECISIONES.md` tiene 571.

## Lo que NO se verificó, y límites
- **El video de funcionamiento, el zip final subido a la plataforma, la invitación a los evaluadores y el video de defensa son de la persona**; el ticket entrega el guion, los comprobadores y los documentos.
- **SC-001 se midió una vez, en esta máquina**, con la caché de `uv` caliente y sin probar Linux ni macOS. Un equipo más lento alarga las pruebas (el 96 % del tiempo); por eso el README ofrece una comprobación rápida.
- **El guion se ensayó por la API de la interfaz**, no con una grabación de pantalla; la aceleración ×6 de la edición es una propuesta que no se probó con un editor.
- **El comprobador del zip detecta formas conocidas de credencial** (claves de Anthropic, tokens de GitHub y claves privadas). No detecta otras clases (por ejemplo, la clave de otro proveedor) y escanea hasta 2 MB por archivo; los archivos binarios solo se miden por nombre.
- **`git log --all -G` mira los cambios de líneas**: una credencial en un objeto inalcanzable o dentro de un archivo binario del historial no aparecería.
- `DECISIONES.md` condensa 11 decisiones; el razonamiento largo sigue en `docs/ECOSISTEMA.md` y en los `research.md`.
