# Quickstart: validar errores estructurados y cobertura parcial

Contrato en [contracts/cobertura.md](contracts/cobertura.md); datos en [data-model.md](data-model.md).

## 1. Pruebas automáticas (sin modelo ni clave)

```bash
python -m uv run pytest due_diligence -q
python -m uv run ruff check .
```

Esperado: todo en verde. Cubren: fallo de cada una de las cuatro fuentes (reintentable y no), éxito del reintento, tope de un reintento, informe que omite o declara el frente caído (`registrar_informe` y `escalar_a_cumplimiento`), `habilitar` sin registro o sin listas (caída o nunca consultadas, comercio y representante), respuesta ilegible, aislamiento por comercio y por solicitud, y el estado `fallido` de un frente en los eventos.

## 2. Verificación por mutación

```bash
python scripts/mutate_rules.py
```

Rompe a propósito cada comprobación de cobertura (no registrar fallos, no limpiar el fallo tras un éxito, no limitar los reintentos, aceptar la omisión de un frente caído, permitir `habilitar` sin listas, etc.) y comprueba que alguna prueba falla. Esperado: todas detectadas (exit 0).

## 3. Con el modelo real y fallas inyectadas (manual)

Con el inicio de sesión de Claude Code o con `ANTHROPIC_API_KEY` válida:

```bash
PASARELA_FAULTS=noticias python -m uv run python -m due_diligence
```

| # | Falla | Mensaje | Esperado |
|---|---|---|---|
| 1 | `noticias` (reintentable) | Due diligence de CO-LB-0002 | Un solo reintento de noticias; el informe declara `noticias` sin cubrir y conserva los otros tres frentes |
| 2 | `noticias:no_reintentable` | Igual | Sin reintento; mismo informe parcial |
| 3 | `listas` | Igual y "recomienda habilitar" | `habilitar` se rechaza (`cobertura_habilitar`); queda `no_habilitar` o `escalar_a_cumplimiento` con `listas` sin cubrir |
| 4 | `registro` | Igual | Nada se consulta en listas (regla 1); informe sin cubrir `registro` y `listas` |
| 5 | ninguna | Igual | Informe con cobertura completa, como antes |

Anotar el resultado de cada caso en `verification.md`.
