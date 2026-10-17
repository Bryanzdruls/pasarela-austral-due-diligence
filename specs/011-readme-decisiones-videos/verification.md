# Verificación: README, DECISIONES.md, guion de video y zip de entrega

## Línea base (T001)
En `main` (merge del PR #23, `f11f80b`) la suite tenía 1.528 pruebas en verde, `ruff check` y `ruff format --check` limpios y `verify_ecosystem.py` con código 0. La rama parte de ahí.

## Historia 3: el zip de entrega
**Pruebas primero (T006).** `scripts/tests/test_verify_delivery.py` falló por la razón esperada: `ModuleNotFoundError: No module named 'verify_delivery'`.

**Implementación (T007, T008).** 51 pruebas en verde. Una falló al principio por un defecto real del script, no de la prueba: el mensaje de error salía por `stderr` con la codificación local de Windows (cp1252) y llegaba ilegible, el mismo defecto que ya apareció en los hooks del #9. Se fija UTF-8 en `stdout` y `stderr` al principio de `main`.

**Sobre el repositorio real (T009, informativo).** `python scripts/verify_delivery.py --build`: historial con 84 commits, 3.384.955 bytes (`.git` 2.350.438 y resto 707.663, frente a un límite de 50.000.000), sin dependencias, sin archivos de secretos y sin credenciales en los archivos ni en el historial. Falló solo `coincide con el último commit`, porque el `.gitignore` tenía un cambio sin confirmar: el caso que la comparación de contenido (hallazgo C1 del análisis) existe para detectar.
