# Verificación del ticket #2 con modelo real (T025 y T035)

Fecha: 2026-10-16. Rama `002-coordinador-subagentes`. Se ejecutó la matriz de 5 casos de `quickstart.md` con el Agent SDK (`claude-agent-sdk` 0.2.168) y el modelo real, guiada por un script que usa las mismas piezas que la consola (`DueDiligenceSession`).

**Cómo se ejecutó.** La variable `ANTHROPIC_API_KEY` del entorno devolvió `Invalid API key`; la CLI que el SDK arranca por debajo usó el inicio de sesión de claude.ai (se retiró la variable solo en el proceso del script). Con una clave válida el resultado debería ser el mismo, pero **no se comprobó con esa clave**.

## Hallazgo: por defecto los subagentes se lanzaban en segundo plano

La primera ejecución (`verification-run1-segundo-plano.txt`) **no cumplía** el comportamiento esperado:

- Cada `SubagentFinished` llegaba a los ~0,1 s con estado `no_estructurado`: era el acuse del lanzamiento, no el resultado del frente.
- Los tres frentes se iniciaban de forma escalonada (cada uno tras el acuse del anterior) y el coordinador cerraba el turno diciendo "sigo esperando los resultados"; el informe aparecía turnos después, inyectado como notificación al responder otra pregunta.
- Es decir, SC-001 y SC-004 fallaban aunque las 92 pruebas sin modelo pasaban: el fallo solo se ve con el modelo real.

Se probaron dos palancas, con la prueba primero y repitiendo la matriz:

| Cambio | Resultado |
|---|---|
| `AgentDefinition(background=False)` en los cuatro frentes | Se conserva (es lo correcto), pero **no cambió el comportamiento**: seguía llegando el acuse |
| `ClaudeAgentOptions(env={"CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1"})` | **Lo corrige**: la delegación devuelve el resultado del frente (estado `completo`) |

Las dos quedan en el código, con una prueba cada una (`test_agents.py` y `test_options.py`).

## Matriz tras la corrección (`verification-run3-primer-plano.txt`)

| # | Mensaje | Esperado | Observado | Resultado |
|---|---|---|---|---|
| 1 | Due diligence de Tienda Verde SAS (CO-TV-0001), suplementos dietarios, volumen mensual estimado | Tres `SubagentStarted` (registro, noticias, riesgo) antes de cualquier `SubagentFinished`; listas solo tras terminar el registro; informe por frente con "Datos aportados por el analista" y recomendación; `RunFinished` `success` | Marcas de tiempo: `registro_mercantil` iniciado 20:30:11.2, `noticias` 20:30:12.1, `riesgo_categoria` 20:30:13.0; el primer `terminó` (registro) a las 20:30:14.9; `listas_restrictivas` iniciado a las 20:30:18.9, después de terminar el registro; informe con una sección por frente, datos del analista separados y recomendación de derivar a un oficial de cumplimiento; `RunFinished` `success`/`end_turn`/`completed` | **Aprobado** (SC-001, SC-004) |
| 2 | "¿Y qué dijeron las noticias?" | Respuesta sin ningún `SubagentStarted` nuevo | Responde con lo que ya tenía (fuente y fecha) y dice que no repitió la búsqueda; 0 `SubagentStarted` | **Aprobado** (SC-007) |
| 3 | Due diligence de Libros del Faro SAS (CO-LB-0002) | Investigación nueva; los `encargo` no contienen datos de Tienda Verde | Cuatro frentes nuevos; ningún `encargo` menciona a Tienda Verde ni su identificador; el informe habilita por riesgo bajo y declara que no hay categoría ni volumen del analista | **Aprobado** (SC-007, SC-003) |
| 4 | (conversación nueva) "Necesito un due diligence" | Pide el comercio; ningún `SubagentStarted` | Pide comercio, categoría y volumen; 0 `SubagentStarted` | **Aprobado** (SC-006) |
| 5 | (conversación nueva) "Due diligence de Cafetería Aurora" | No inventa un comercio; el manejo completo es el ticket #5 | El registro devolvió dos coincidencias: las presenta en una tabla, no consulta listas ni riesgo y pide el identificador | **Aprobado** (adelanta parte del #5) |

Todos los turnos cerraron por `ResultMessage` (`success`, `end_turn`), no por texto ni por contador (SC-005).

## T035: `agent_type` real y herramientas de los subagentes

Con `PASARELA_HOOK_TRACE` (`verification-hook-trace.jsonl`, ejecución correcta):

- El SDK entrega `agent_type` con el **nombre del frente** (`registro_mercantil`, `listas_restrictivas`, `noticias`, `riesgo_categoria`) y un `agent_id` por subagente; el coordinador llega con `agent_type` nulo.
- Cada subagente **pudo usar su herramienta MCP** (3 llamadas del registro, 5 de noticias, 4 de listas, 2 de riesgo, todas `allow`); el coordinador solo usó `Agent` (10 llamadas).
- En la primera ejecución el coordinador intentó `registrar_informe` y `escalar_a_cumplimiento` y el hook las **denegó**: el aislamiento por hook funciona con el modelo real.

## Sin verificar o con límites

- **Clave del API:** no se comprobó con una `ANTHROPIC_API_KEY` válida (ver arriba).
- **Reglas 1 a 3:** el coordinador las respetó en los 5 casos, pero siguen siendo orientación del prompt (FR-007) hasta el ticket #3; **no cuentan como garantizadas**.
- **Registro del informe y escalamiento:** el coordinador no tiene esas herramientas (ticket #6); lo declara en su respuesta.
- **Variabilidad:** cada ejecución con modelo es distinta; la matriz se corrió completa una vez tras la corrección y los casos coinciden con lo esperado, pero no se repitió varias veces.
- Los textos de los informes salen del modelo: se guardan como evidencia, no como prueba automática.
