# Verificación: interfaz de chat con eventos visibles (#7)

Fecha: 2026-10-16/17. Rama `007-chat-eventos-visibles`.

## Pruebas, formato y ecosistema

- `python -m uv run pytest -q`: pruebas en verde (1344 en `main` + las nuevas del ticket: 82 en `due_diligence/web/tests/` —observadores, vista, conversación, aplicación, arranque y página— y 8 en eventos, `on_decision`, `build_options`, consola y el camino de fallo cerrado). Recuento final: **1436 pruebas en verde** (1344 + 92).
- `ruff check .` y `ruff format --check .` limpios; `python scripts/verify_ecosystem.py`: ecosistema completo.
- Pruebas primero: cada grupo se escribió, se ejecutó y falló por la razón esperada (importación o atributo inexistente) antes de implementar; lo mismo con las correcciones tras las revisiones. La única prueba que fallaba a propósito entre pasos fue la de la página servida, hasta crear `index.html`.
- Ninguna prueba llama al modelo.
- Mutaciones (`python scripts/mutate_rules.py`): **89 de 89 detectadas**. Tres anclas (`PreToolUse`, `PostToolUse` y el fallo cerrado) se reanclaron porque el cableado cambió. Una primera pasada quedó colgada toda la noche (el equipo se suspendió) y dejó `rules.py` mutado: se restauró con `git checkout` y se añadió al script un tope de 600 s por mutación (una mutación que cuelga cuenta como detectada). Los observadores y la vista del chat no están dentro del alcance de ese script; los cubren sus pruebas.

## Modelo de amenaza (para las revisiones)

Qué se protege: una interfaz **local** que muestra texto del modelo y de las fuentes ficticias a un analista. (1) Ese texto nunca debe ejecutarse en el navegador (la página usa solo `textContent`; una prueba prohíbe `innerHTML`, `eval` y recursos externos). (2) No debe escuchar fuera de la máquina por defecto (`127.0.0.1`; otra dirección exige `--permitir-red`). (3) Un fallo al observar (bloqueo, informe, escalamiento) no puede cambiar una decisión de los hooks. (4) Una excepción interna no se muestra al navegador.
Fuera de alcance, declarado: autenticación, persistencia en disco, varios usuarios, protección frente a quien ya tiene acceso a la máquina o al navegador local.

## Con el modelo real, por la interfaz

Se arrancó `python -m due_diligence.web` y se recorrieron los siete casos de `docs/CASOS.md` con las mismas llamadas que hace el navegador (crear conversación, enviar mensaje, leer el flujo SSE), usando el inicio de sesión de Claude Code. El flujo completo de cada caso está en `evidencia/casoN.json` (datos ficticios).

| Caso | Eventos vistos (tarjetas) | Lo que se ve |
|---|---|---|
| 1 Alto riesgo | 1 analista, 4 delegaciones, 4 resultados, 1 informe, 1 escalamiento, 1 coordinador, 1 fin | Informe con recomendación "escalar a cumplimiento" y escalamiento ESC-0001 por riesgo |
| 2 Bajo riesgo | 4 delegaciones, 4 resultados, 1 informe, 2 coordinador, 1 fin | Informe "habilitar", sin bloqueos |
| 3 Representante en listas | 5 delegaciones, 5 resultados, informe y escalamiento | Escalamiento por coincidencia del representante; un resultado del registro no estructurado se muestra como no completo |
| 4 Nombres casi idénticos | 2 turnos, 6 delegaciones, informe | Tras el segundo turno ("CO-CA-0004") se registra el informe de ese comercio |
| 5 Listas sin identificar | informe y escalamiento de `CO-TV-0001` | El modelo pasó por el registro en lugar de consultar listas directamente: no hubo bloqueo que mostrar (ver límites) |
| 6 Falla de noticias | resultado "Falló las noticias… Se puede reintentar", **1 bloqueo**, informe "no habilitar" | **Un bloqueo real mostrado en la interfaz**: la regla del reintento ("Cada consulta se reintenta como máximo una vez") con el motivo literal del hook |
| 7 Fechas distintas | informe y escalamiento de `CO-FH-0006` | Escalamiento por contradicción en la fecha de constitución |

Cada informe y escalamiento mostrado corresponde a un sobre `ok: true` del servidor (el identificador `INF-0001`/`ESC-0001` lo da el servidor, no el modelo).

## Revisiones independientes (una ronda)

**Código (`code-reviewer`)**: corregir antes del PR. Se corrigieron los dos IMPORTANTES con entrada reproducible, cada uno con su prueba escrita antes:
- Un mensaje con un sustituto UTF-16 suelto (un escape `\u` de la zona de sustitutos, sin pareja) rompía el flujo SSE de esa conversación en cada reconexión. Ahora `enviar` lo rechaza (422) si no codifica a UTF-8.
- El texto de una excepción interna (regla `evaluacion`) llegaba al navegador en la tarjeta de bloqueo. Ahora la tarjeta muestra solo la explicación genérica.
- También: la prueba de 409 quedó sin código muerto y con una aserción real.

**Cumplimiento (`compliance-reviewer`)**: cumple parcialmente, sin faltas graves. Su B1 (la prueba de `evaluacion`) era el mismo hallazgo ya corregido. Corregido además: I1 (la tarjeta del informe dice "Sin cubrir: …" con los frentes que el informe declara), M3 (una llamada rechazada por el guard y por una regla se muestra una vez, por `tool_use_id`), M4 (prueba de `on_decision` en el camino de fallo cerrado) y M5 (documentación).

## Límites y pendientes declarados

- **No se vio la página en un navegador real**: la interfaz se verificó con pruebas de la página, de la aplicación y por la API/SSE con el modelo real. El aspecto visual (colores, tarjetas, modo oscuro, desplazamiento) está sin comprobar a ojo; conviene abrir `http://127.0.0.1:8000` antes de grabar el video.
- Caso 5: el modelo no intentó consultar listas sin identificar, así que la tarjeta de bloqueo por la regla 1 no se vio con el modelo real; sí la cubren las pruebas (`test_vista`, `test_conversacion`, `test_options`, que pasan por el hook real). El único bloqueo real fue el del caso 6.
- Sin validación de `Host`/`Origin` (DNS rebinding contra una interfaz local sin autenticación), sin tope de conversaciones ni de tamaño del cuerpo antes de leerlo. No corregido: fuera del modelo de amenaza declarado.
- `evidencia/caso3.json` y `caso6.json` se guardaron con el título anterior de un resultado no estructurado ("No se pudo dar por completo…"); el texto actual es "La respuesta de … no se toma como completa". Es la salida real de esa pasada y no se edita.
- `spec.md` nombra Starlette y `127.0.0.1` en las suposiciones y en FR-010 porque el issue nombra la tecnología.
- Una conversación vive en memoria; reiniciar el proceso la pierde. Un turno a la vez.
- Starlette en lugar de FastAPI (D1, declarado en la spec).
