# Contrato: interfaz web

## Rutas

| Método y ruta | Qué hace |
|---|---|
| `GET /` | La página de chat |
| `GET /api/estado` | `{"estado": "ok", "conversaciones": N}` (sin modelo) |
| `POST /api/conversaciones` | Crea una conversación: `{"id": "<id>"}` (201) |
| `POST /api/conversaciones/{id}/mensajes` | Cuerpo `{"texto": "..."}`; 202 si empieza el turno; 409 si hay un turno en curso; 422 si el texto está vacío o supera 4000 caracteres; 404 si la conversación no existe |
| `GET /api/conversaciones/{id}/eventos` | SSE: primero el historial y después los eventos en vivo; con `?hasta_fin=1` cierra tras el siguiente evento `fin` o `error` (uso de las pruebas) |

## Evento visible (cada `data:` del SSE)

```json
{"n": 3, "tipo": "bloqueo", "titulo": "Llamada bloqueada", "detalle": "...", "hora": "2026-10-17T12:00:00+00:00", "extra": {"regla": "1"}}
```

Tipos: `analista`, `coordinador`, `delegacion`, `resultado`, `bloqueo`, `informe`, `escalamiento`, `fin`, `error`. `n` es el número de orden en la conversación.

## Eventos del dominio nuevos (`due_diligence/events.py`)

```text
CallBlocked(agente, herramienta, regla, motivo)
ReportRegistered(informe_id, comercio_id, recomendacion)
Escalated(escalamiento_id, comercio_id, causa)
```

## Llamada opcional del hook de reglas

```text
make_pre_tool_use(book, on_decision=None)   # on_decision(input_data, decision) en cada rechazo
build_options(book=None, on_decision=None)
```

Sin `on_decision` el comportamiento es idéntico al de #3 a #6.
