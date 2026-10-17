# Contrato: arnés de escenario y ejecución con el modelo real

## Arnés (`due_diligence/tests/escenario.py`)

```python
escenario = Escenario(tmp_path, monkeypatch, faults="")  # PASARELA_FAULTS opcional
await escenario.solicitud("Necesito el due diligence de ...")  # UserPromptSubmit
r = await escenario.llamar(
    "consultar_registro_mercantil", {"consulta": "..."}, agente="registro_mercantil"
)
r.permitida  # bool: ningún hook la rechazó
r.regla  # regla que rechazó (p. ej. "1", "2", "3", "cobertura", "conflicto", "escalamiento"), o None
r.motivo  # texto del rechazo, o None
r.respuesta  # dict con el sobre del servidor si se ejecutó, o None
await escenario.parada()  # Stop: {} si puede cerrar, o {"decision": "block", ...}
escenario.registros("INF")  # informes guardados (lista de dict)
escenario.registros("ESC")  # escalamientos guardados
```

- Los hooks son los de `build_options(book).hooks`, ejecutados en orden; una llamada se ejecuta solo si ninguno la rechaza.
- Las herramientas son las funciones reales de `mcp_server/tools`; los informes y escalamientos se guardan en `PASARELA_RUNTIME_DIR` (temporal).
- Tras ejecutar una llamada, `PostToolUse` recibe `tool_response` como texto con el sobre JSON, igual que en el SDK.

## Ejecución real (`python scripts/run_casos.py`)

```text
python scripts/run_casos.py                 # los 7 casos
python scripts/run_casos.py --caso 3        # solo el caso 3
python scripts/run_casos.py --salida DIR    # guarda llamadas y registros en DIR
```

- Sin `ANTHROPIC_API_KEY`: mensaje claro y código de salida 2, sin llamar al modelo (la bandera `--usar-sesion-claude` permite usar el inicio de sesión de Claude Code).
- Una línea por caso: `PASA caso N — título` o `FALLA caso N — título: motivo`; resumen final; código 0 solo si todos pasan.
- La salida guarda por caso `llamadas.jsonl` (las herramientas ejecutadas: herramienta, agente, entrada, respuesta y turno), `conversacion.txt`, `resumen.json` (denegaciones con su regla y el error si lo hubo) y la carpeta `registros/` con los informes y escalamientos guardados.

## `due_diligence/casos_reales.py`

```text
CASOS: tuple[Caso, ...]             # los siete, con numero, titulo, mensajes y faults
Registro(llamadas, denegaciones, informes, escalamientos, textos, error)    # lo observado
Caso.comprobar(registro) -> list[str]                  # motivos de fallo; vacío = pasa
```

Las comprobaciones usan las llamadas ejecutadas y los registros guardados; nunca el texto de la respuesta. Las denegaciones (de la traza de reglas) se anotan en la salida como dato informativo.
