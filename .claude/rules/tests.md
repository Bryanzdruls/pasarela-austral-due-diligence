---
paths:
  - "**/tests/**/*.py"
  - "**/test_*.py"
---

# Convenciones de pruebas

- La prueba vive junto al código que prueba (`<paquete>/tests/` o `<paquete>/<subpaquete>/tests/`) y se llama `test_<modulo>.py`.
- Nombre en inglés que dice el comportamiento: `test_a_valid_card_number_is_blocked`, no `test_1`.
- **Primero la prueba**: escríbela, ejecútala y comprueba que falla por la razón esperada antes de implementar. Un script inexistente también sale con código 2: una prueba que solo mira el código de salida puede pasar sin probar nada; comprueba además el mensaje o el efecto.
- **Sin modelo real**: usa el cliente falso (`due_diligence/tests/fakes.py`) o llama al hook como subproceso con JSON por stdin (`.claude/hooks/tests/helpers.py`).
- **Valores sensibles generados en tiempo de ejecución**: tarjetas, NIT y documentos salen de `make_card`, `make_nit` y `make_documento`; nunca se escriben literales.
- Un fallo de una prueba nueva que dice "el hook estaba bien y la prueba mal" se corrige en la prueba y se explica en el commit.
- Antes de dar por buena una prueba de comportamiento delicado, rompe el código a propósito y comprueba que alguna prueba falla (verificación por mutación).
