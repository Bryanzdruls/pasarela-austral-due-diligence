# Quickstart: la interfaz de chat

Contrato en [contracts/web.md](contracts/web.md).

## 1. Pruebas (sin modelo ni clave)

```bash
python -m uv run pytest due_diligence/web -q
```

## 2. Arrancar la interfaz

```bash
python -m uv run python -m due_diligence.web      # http://127.0.0.1:8000
```

Abre la dirección, escribe un mensaje de los casos de `docs/CASOS.md` (p. ej. "Necesito el due diligence de Tienda Verde SAS, identificador CO-TV-0001. Quieren procesar ventas en línea de suplementos dietarios.") y observa los eventos: delegaciones, resultados, bloqueos, informe y escalamiento. Necesita `ANTHROPIC_API_KEY`.

## 3. Verificación con el modelo real

Recorre los siete casos de `docs/CASOS.md` en la interfaz y anota en `verification.md` el evento que aparece en cada uno.
