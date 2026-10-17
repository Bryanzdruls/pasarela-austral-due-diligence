# Quickstart: ejecutar los siete casos obligatorios

Contrato en [contracts/casos.md](contracts/casos.md); resumen de los casos en `docs/CASOS.md`.

## 1. Sin modelo ni clave (pytest)

```bash
python -m uv run pytest due_diligence/tests/test_casos_obligatorios.py -v
```

Esperado: 7 casos (más sus variantes) en verde en menos de un minuto.

## 2. Con el modelo real

```bash
python -m uv run python scripts/run_casos.py            # los 7
python -m uv run python scripts/run_casos.py --caso 3   # uno solo
```

Esperado: una línea por caso (`PASA` o `FALLA` con el motivo) y un resumen. Necesita `ANTHROPIC_API_KEY`.

## 3. Mutaciones de sistema

```bash
python scripts/mutate_rules.py
```

Esperado: todas detectadas, incluidas las que desconectan el hook de reglas, el de parada o la inyección de fallas.
