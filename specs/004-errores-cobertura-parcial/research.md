# Research: Errores estructurados y cobertura parcial

Cada decisión lleva su alternativa descartada: alimentan `DECISIONES.md`. Las decisiones D1 a D7 del #3 siguen vigentes; aquí se numera desde D1 por ticket.

## D1. La cobertura se decide con lo que el servidor devolvió, no con lo que los agentes cuenten
- **Decisión**: el `CaseBook` observa con `PostToolUse` el sobre de cada una de las cuatro fuentes (`ok: true` o el error estructurado `{ok: false, error_code, retryable, partial}`) y de ahí sale el estado de cada frente. El informe y el escalamiento se verifican contra ese estado.
- **Por qué**: es la misma garantía del #3 (D1): la regla 5 es una falta grave y no puede depender de que el subagente describa bien su fallo ni de que el coordinador se acuerde de declararlo.
- **Alternativas descartadas**: (a) fiarse del resultado JSON que devuelve el subagente: es texto del modelo, justo lo que el enunciado excluye para lo grave (se usa solo para informar al coordinador y al chat, D8); (b) pedir al coordinador que lleve la cuenta en su prompt: es la falta que el ticket cierra.

## D2. Un frente es una lista de sujetos; cubierto solo si ninguno está caído
- **Decisión**: el estado se lleva por frente y **sujeto** (`listas`: `tipo` + `referencia`; `riesgo`: la categoría, normalizada). Para `registro` y `noticias` el sujeto es el propio frente: la fuente responde o no, sea cual sea la redacción de la consulta. **Corregido con el modelo real** (caso 1 de `verification.md`): con el sujeto igual a la consulta, un subagente reintentó noticias con tres redacciones distintas y esquivó el tope. Un éxito posterior del mismo sujeto borra su fallo (reintento recuperado). El frente está sin cubrir si algún sujeto está caído.
- **Por qué**: las listas se consultan dos veces (comercio y representante). Si falla solo la del representante, el frente no puede darse por limpio (caso límite de la spec), y si el reintento tiene éxito debe quedar cubierto.
- **Alternativas descartadas**: (a) un booleano por frente para todos: no distingue la consulta del representante y un éxito del comercio taparía la falla de la persona; (b) el texto de la consulta como sujeto en registro y noticias: lo esquiva cualquier reescritura (medido).

## D3. A qué comercio pertenece una falla
- **Decisión**: una falla se asocia al comercio cuando el sujeto lo identifica (listas por `comercio` y por `persona` del representante) o cuando el comercio ya es de la solicitud en curso (noticias y riesgo, que no llevan identificador de comercio). El estado de un comercio **persiste entre solicitudes** hasta un éxito del mismo sujeto. Una falla que no se puede asociar (p. ej. el registro caído antes de identificar nada) queda como **huérfana de la solicitud** y se limpia con la solicitud siguiente.
- **Por qué**: el analista puede pedir el informe en un turno posterior al de la falla; si el estado se perdiera con cada solicitud, un informe parcial pasaría por completo (el hueco que el #3 ya cerró para la evidencia de riesgo). Y la falla de un comercio no puede afectar a otro (FR-012).
- **Alternativas descartadas**: (a) estado solo por solicitud: pierde la falla en el turno siguiente; (b) estado global de la conversación: mezcla comercios.
- **Riesgo declarado**: noticias y riesgo, sin identificador, se asocian a los comercios de la solicitud en curso; con dos comercios en la misma solicitud la falla se atribuye a ambos (declarar de más es el lado seguro).

## D4. El tope de reintentos lo impone el hook
- **Decisión**: `PreToolUse` gobierna también las cuatro herramientas de fuentes (`check_fuente`). Por solicitud y sujeto (D2): si la última llamada falló con `retryable: false`, se deniega repetirla; si ya hubo dos llamadas fallidas (el intento y su reintento), se deniega la tercera. El motivo dice que el frente debe declararse sin cubrir. La solicitud nueva del analista reinicia los contadores (puede pedir reintentar).
- **Por qué**: SC-003 exige que ningún frente se reintente más de una vez ni se reintente lo no reintentable; un prompt no lo garantiza, y un subagente puede reintentar por su cuenta sin que el coordinador lo sepa.
- **Alternativas descartadas**: (a) solo la instrucción en el prompt; (b) `max_turns`: contradice el ciclo por razón de parada (B4). Una consulta de otro sujeto (otra persona o categoría) no cuenta como reintento; en registro y noticias no hay otro sujeto: cualquier redacción es el mismo frente.

## D5. Declarar la cobertura: vocabulario cerrado y rechazo con el frente nombrado
- **Decisión**: `registrar_informe` y `escalar_a_cumplimiento` llevan `cobertura` como objeto `{frente: {estado, motivo}}` con `frente` en `registro`, `listas`, `noticias`, `riesgo` y `estado` en `cubierto` o `sin_cubrir` (contrato en [contracts/cobertura.md](contracts/cobertura.md)). Si hay un frente fallido y no consta con `estado: sin_cubrir`, el hook rechaza y nombra los frentes que faltan. Se admiten los alias `registro_mercantil`, `listas_restrictivas` y `riesgo_categoria`.
- **Por qué**: igual que el vocabulario de recomendaciones (#3 D5), una forma abierta se esquiva cambiando la redacción. Declarar de más (un frente que sí respondió como `sin_cubrir`) se acepta: es el lado seguro.
- **Alternativas descartadas**: (a) buscar palabras como "sin cubrir" en el texto de `cobertura`: no determinista; (b) añadir el campo al servidor y validar allí: el servidor informa, no decide (convención de `mcp_server/CLAUDE.md`).

## D6. `escalar_a_cumplimiento` también exige la declaración
- **Decisión**: el escalamiento se rechaza si no declara los frentes caídos (FR-009), con el mismo motivo y la misma forma. Es el único cambio a "escalar siempre se permite" del #3.
- **Por qué**: el oficial de cumplimiento debe saber qué falta verificar. El motivo es explícito y la corrección es de una línea, así que no hay riesgo real de no poder escalar.
- **Alternativa descartada**: permitir siempre y añadir la cobertura por nuestra cuenta: el hook no escribe en las llamadas (solo permite o deniega) y se perdería la coherencia con el informe.

## D7. Habilitar exige registro y listas cubiertos, también si nunca se consultaron
- **Decisión**: `habilitar` se rechaza si falta el registro o si las listas no están cubiertas: el comercio sin consulta correcta, o el representante legal sin consulta correcta (cuando el registro dio su identificador). Cubierto significa consultado con éxito. No se exige noticias ni riesgo.
- **Por qué**: una habilitación sin verificar el comercio y su representante ante listas contradice la intención de la regla 2: no basta con que "no haya coincidencia" si no se miró. Noticias y riesgo no sostienen la identificación ni la verificación; el riesgo ya lo cubre la lista propia de la pasarela (#3 D6).
- **Consecuencia**: las pruebas del #3 que daban por válido habilitar sin listas consultadas se ajustan para sembrar las dos consultas de listas (cada ajuste queda anotado en `tasks.md`). Es un cambio de comportamiento deliberado y se declara en `verification.md`.
- **Alternativas descartadas**: (a) exigir los cuatro frentes: bloquea habilitar por una caída de noticias, que el enunciado trata como informe parcial declarado y no como impedimento (caso 6); (b) exigir solo el registro: deja habilitar sin mirar listas.

## D8. Un error estructurado del subagente llega al coordinador y al chat como estado `fallido`
- **Decisión**: los subagentes responden con `{"estado": "error", "frente", "reintentable", "obtenido", "metadatos"}` cuando su fuente falla. `events.py` lo convierte en un `FrontResult` con estado `fallido` (contenido = lo obtenido, más el motivo y si es reintentable); una respuesta sin interpretar sigue siendo `no_estructurado` y se trata como no cubierta. Esto es informativo (coordinador, chat del #7); la autoridad es D1.
- **Por qué**: el coordinador necesita distinguir un fallo declarado de un resultado ilegible para decidir si reintenta; el chat necesita mostrarlo.
- **Alternativa descartada**: reutilizar `no_completado` (error del propio SDK): mezclaría la falla de la fuente con la falla del agente.

## D9. Respuestas que no se pueden interpretar y fallos de la llamada
- **Decisión**: una respuesta de una fuente que no se puede interpretar como sobre cuenta como **falla no reintentable** (ante la duda no se da por cubierta ni se insiste). Una llamada que falla antes de devolver un sobre (conexión cerrada, tiempo agotado) se observa con el hook `PostToolUseFailure` y cuenta igual. La forma real de esa entrada se mide en la implementación y se anota en `verification.md`.
- **Por qué**: FR-002. Un fallo de infraestructura que no llega como sobre no puede convertirse en "cubierto".
- **Alternativa descartada**: tratarlo como reintentable: invita a insistir contra una fuente que no sabemos si responde.

## D10. Nombres de frente
Las constantes del módulo de reglas (`registro`, `listas`, `noticias`, `riesgo`) son las del servidor (`PASARELA_FAULTS`); los subagentes usan los de `FrontName` (`registro_mercantil`, …). Una prueba comprueba que cada alias de uno corresponde al otro, para que renombrar un frente en un lado rompa la prueba.
