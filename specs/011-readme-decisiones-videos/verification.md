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
