# La interfaz de chat

Una página local donde el analista conversa con el coordinador y **ve lo que pasa**: a quién delega, qué responde cada fuente, qué llamada se bloquea y por qué, qué informe se registra y cuándo se escala. Especificación: `specs/007-chat-eventos-visibles/`.

## Arrancarla

```bash
python -m uv sync
python -m uv run python -m due_diligence.web          # http://127.0.0.1:8000
```

Necesita `ANTHROPIC_API_KEY` en el entorno (nunca en el repositorio). Sin ella la página abre, pero cada turno termina en un error legible. `--puerto N` cambia el puerto. Solo escucha en `127.0.0.1`: otra dirección se rechaza salvo con `--permitir-red`, porque la interfaz **no tiene autenticación ni guarda nada en disco** (es una demostración local).

## Qué se ve

Cada hecho es una tarjeta con su etiqueta, un título en lenguaje llano, un detalle y la hora.

| Tarjeta | Cuándo aparece | De dónde sale |
|---|---|---|
| Analista | Envías un mensaje | Tu texto |
| Coordinador | El coordinador responde | Su mensaje, con su formato (títulos, listas, negritas, código y tablas); lo que no tiene formato se ve como texto |
| Delegación | Delega en un frente (registro, listas, noticias, riesgo) | La llamada que hizo y el encargo que dio |
| Resultado | Un frente responde, falla o no se puede dar por completo | Lo que devolvió el subagente |
| Hallazgo | Una fuente responde sin error | Una frase redactada por el sistema con lo que devolvió el servidor y a qué consulta corresponde (p. ej. "Sin coincidencias en las listas restrictivas para la persona PE-0001"); una consulta fallida no genera hallazgo |
| Bloqueo | Un hook rechaza una llamada | **La decisión del hook**, con su regla y su motivo literal |
| Informe | Se registra un informe | El sobre `ok: true` del servidor |
| Escalamiento | Se escala a cumplimiento | El sobre `ok: true` del servidor |
| Fin del turno / Error | Termina el turno o falla | La razón de parada del modelo o la causa del error |

Los bloqueos, el informe y el escalamiento **no se leen del texto del modelo**: lo que el modelo cuenta sobre lo que hizo no es una prueba. Se muestra lo que el sistema decidió y lo que el servidor confirmó.

## Los siete casos en la interfaz

Los mensajes de cada caso están en `docs/CASOS.md`. En la interfaz se reconocen así:

| Caso | Qué debe verse |
|---|---|
| 1 Alto riesgo | Delegaciones y resultados, tarjeta de Escalamiento (y, si el modelo intenta habilitar, un Bloqueo) |
| 2 Bajo riesgo | Delegaciones, resultados y un Informe con `habilitar`, sin bloqueos |
| 3 Representante en listas | Resultado de listas con coincidencia y Escalamiento |
| 4 Nombres casi idénticos | Solo el registro: el coordinador pide el identificador, sin Informe |
| 5 Listas sin identificar | No se delega en listas; si el modelo lo intenta, Bloqueo por la regla 1 |
| 6 Falla de noticias | Resultado de noticias con "Falló" y el informe declarando el frente sin cubrir |
| 7 Fechas distintas | Resultado del registro con ambas fechas y el informe o escalamiento que las declara |

## Límites declarados

- Una conversación vive en memoria mientras el proceso corre; recargar la página recupera el historial (verificado en el navegador integrado con el modelo real, que recuerda el contexto), reiniciar el proceso lo pierde.
- Un turno a la vez por conversación.
- Starlette en lugar de FastAPI (decisión D1 de `research.md`).
- El aspecto visual se comprobó en el navegador integrado de Claude Code con el modelo real (casos 1 y 4, ver `verification.md`); no se ha probado en Chrome, Firefox ni Safari, ni en un teléfono real.
- Al enviar un mensaje vacío la página avisa y no crea ninguna tarjeta. El navegador puede servir una copia en caché de la página tras cambiar el código: recarga con Ctrl+F5.
- No valida el encabezado `Host`: pensada solo para `127.0.0.1`, sin protección contra DNS rebinding.
