# Quickstart: validar el escalamiento con criterio y el handoff

Contrato en [contracts/escalamiento.md](contracts/escalamiento.md); datos en [data-model.md](data-model.md).

## 1. Pruebas automáticas (sin modelo ni clave)

```bash
python -m uv run pytest due_diligence mcp_server -q
python -m uv run ruff check .
```

Esperado: todo en verde. Cubren: cada motivo permite escalar; un riesgo bajo sin hallazgos, con y sin frentes sin cubrir, no; el informe con `escalar_a_cumplimiento` igual; un comercio sin identificar con alto riesgo declarado sí y sin él no; el resumen sin el hallazgo del frente, con una causa que no nombra el motivo o con una contradicción sin declarar, no; el resumen completo sí; y `habilitar` y el hook de parada sin cambios.

## 2. Verificación por mutación

```bash
python scripts/mutate_rules.py
```

Esperado: todas detectadas (exit 0).

## 3. Con el modelo real (manual)

Con `ANTHROPIC_API_KEY` válida:

```bash
python -m uv run python -m due_diligence
```

| # | Mensaje | Esperado |
|---|---|---|
| 1 | C1: "Due diligence de Tienda Verde SAS, CO-TV-0001, suplementos dietarios" | Se escala con resumen completo: hallazgo de registro o riesgo con fuente, cobertura, causa que nombra el alto riesgo y acción recomendada |
| 2 | C3: "Due diligence de Distribuidora Andina Ficticia SAS, CO-DA-0003" (representante con coincidencia) | Se escala con el hallazgo de listas y una causa que nombra la coincidencia |
| 3 | C2: "Due diligence de Libros del Faro SAS, CO-LB-0002" | `habilitar`; no se escala |
| 4 | C2 con `PASARELA_FAULTS=noticias` | Informe `habilitar` o `no_habilitar` con noticias sin cubrir; no se escala |
| 5 | Con un prompt de prueba que ordena escalar `CO-LB-0002` | El hook rechaza (`escalamiento`) |
| 6 | Con un prompt de prueba que ordena escalar `CO-TV-0001` con la causa "revisar" | El hook rechaza (`handoff_causa`) |

Anotar el resultado de cada caso en `verification.md`.
