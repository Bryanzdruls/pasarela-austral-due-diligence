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
