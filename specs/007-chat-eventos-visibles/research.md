# Research: Interfaz de chat con eventos visibles

Cada decisión lleva su alternativa descartada: alimentan `DECISIONES.md`.

## D1. Starlette en lugar de FastAPI
- **Decisión**: Starlette + `sse-starlette` + `uvicorn`, ya instalados con el SDK de MCP; se declaran en `pyproject.toml`.
- **Por qué**: el issue dice "FastAPI + HTML con SSE", y FastAPI es Starlette con validación; aquí hay cinco rutas con cuerpos de una línea y no hace falta el resto. Evita una dependencia nueva y una instalación en el equipo del evaluador.
- **Alternativa descartada**: FastAPI tal cual el issue: añade un framework y sus dependencias sin aportar nada a estas rutas. Si se prefiere, el cambio es mecánico (las rutas y la lógica no cambian).

## D2. Los eventos que no viajan en el flujo del SDK se recogen del sistema
- **Decisión**: el bloqueo se recoge con una llamada opcional `on_decision(input_data, decision)` en `make_pre_tool_use`, que recibe la decisión del hook con su regla y motivo; el informe y el escalamiento se recogen con un hook `PostToolUse` observador que lee el sobre del servidor.
- **Por qué**: los bloqueos de los subagentes ocurren dentro del subagente y no aparecen como mensajes del coordinador; y lo que el modelo escribe sobre "lo que hizo" no es una prueba (principio III): hay que mostrar lo que el sistema decidió y lo que el servidor confirmó.
- **Alternativas descartadas**: (a) leer el texto del coordinador para detectar "bloqueado" o "escalé": no determinista; (b) leer el rastro de hooks de un archivo: acopla la interfaz a una variable de entorno y a la E/S.

## D3. Una vista pura de cada evento
`vista.py` convierte cada evento en `{tipo, titulo, detalle, hora}` con lenguaje llano y las reglas traducidas (p. ej. la regla `1` → "las listas solo se consultan para un comercio identificado"). Es una función pura: la prueba "se entiende sin conocer el código" la comprueba sin navegador.

## D4. Un turno a la vez, historial reproducible
Una conversación acepta un turno a la vez (el SDK es secuencial) y guarda todos sus eventos: quien se conecta o recarga recibe el historial y después los eventos en vivo. Alternativa descartada: un turno por conexión (un POST que devuelve el stream): una recarga perdería la conversación.

## D5. Seguridad de una interfaz local que muestra texto de un modelo
Escucha solo en `127.0.0.1`; la página inserta todo con `textContent` (nunca `innerHTML`); se valida el mensaje (no vacío, tamaño máximo) y el identificador de conversación. Sin autenticación ni persistencia: es una demostración local.

## D6. El contexto de la conversación
Una `Conversacion` reutiliza una sola `DueDiligenceSession` (cliente del SDK) entre turnos, como la consola; se abre en el primer turno y se cierra al apagar la aplicación.
