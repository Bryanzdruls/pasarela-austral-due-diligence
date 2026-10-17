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

## 6. QA en un navegador con el modelo real y mejoras (FR-013 a FR-016, T020 a T027)

**Cómo se hizo (2026-10-17).** Se arrancó la interfaz con `python -m due_diligence.web` y se recorrió en el navegador integrado de Claude Code con el modelo real. La clave se tomó de la variable de entorno del usuario y se cargó solo en el proceso del servidor: no se escribió en ningún archivo ni se mostró. Se probaron el caso 1 (alto riesgo), el caso 4 (nombres casi idénticos), un intento de saltarse la regla 1, un mensaje vacío y una etiqueta HTML dentro del mensaje.

**Qué halló la primera pasada y qué se hizo**

| Hallazgo | Tarea | Resultado |
|---|---|---|
| La respuesta del coordinador mostraba `##`, `**`, comillas invertidas y la tabla como `\|---\|` | FR-013 | `markdown.py` produce bloques de datos; la página los dibuja con nodos del DOM y `textContent` |
| Las tarjetas de resultado solo decían la fuente y la fecha | FR-014 | Tarjeta `hallazgo` redactada por el sistema con lo que devolvió el servidor y la consulta a la que responde |
| El campo de mensaje flotaba a mitad de pantalla con la conversación vacía | FR-015 | Diseño en columna a pantalla completa |
| Enviar vacío no avisaba | FR-016 | Aviso, foco al campo y borrado al escribir |

**Defectos que encontraron las pruebas y la mutación (no la QA manual)**
- El tope de 200 bloques no era estricto: con 199 bloques, un párrafo pendiente y un título salían 201. Ahora se recorta al final (`test_the_cap_is_strict_...`).
- Ninguna prueba distinguía si el hallazgo comprobaba `ok: true`: su contenido de error ya no tenía forma de hallazgo. Se añadió una prueba con contenido válido y `ok: false`.
- Las dos frases de listas eran idénticas para el comercio y para el representante, y un "Sin menciones" iba seguido de "1 mención" sin decir de qué consulta. Los hallazgos de listas y noticias ahora nombran a quién se consultó o qué se buscó (texto acotado a una línea de 80 caracteres).
- Dos pruebas mías estaban mal y se corrigieron en la prueba, no en el código: `****` es una regla horizontal en Markdown, no una negrita vacía; y el literal `createElement("table")` no existe porque la página usa un ayudante `hijo(padre, "table")`.

**Verificado en el navegador con el modelo real**
- FR-015: con la conversación vacía, el borde inferior del formulario queda a 752 de 768 px y no hay desplazamiento (antes a 550 de 768).
- FR-016: el aviso aparece, el foco vuelve al campo, no se crea ninguna tarjeta y el aviso desaparece al escribir.
- FR-013: la respuesta final del caso 1 se dibujó con 6 títulos, 6 listas, 9 negritas y 6 fragmentos de código, sin `#`, `**` ni comillas invertidas sin interpretar. La tabla de candidatos del caso 4 se dibujó como una tabla real.
- FR-014: caso 1, "Categoría suplementos dietarios: riesgo alto", "CO-TV-0001, Tienda Verde SAS, estado activo. Representante legal: …" y las listas y noticias con su sujeto. Caso 4: "2 comercios con nombre parecido: CO-CA-0004 (…), CO-CA-0005 (…). Hace falta el identificador para continuar."
- Una etiqueta `<img onerror>` dentro del mensaje no se ejecutó (0 imágenes, el título no cambió).

**Verificación por mutación de lo nuevo.** 16 mutaciones (la negrita sin marcar, las tablas sin reconocer, el tope de bloques, la lista numerada, la frase de "sin coincidencias", el hallazgo ante un fallo del servidor, el nivel de riesgo, los bloques del coordinador, `innerHTML`, el aviso del vacío, el hueco a media pantalla, el aviso de identificador, y que los hallazgos pierdan su sujeto, su acotado o sus saltos de línea): todas detectadas por alguna prueba; el control sin mutación pasa. Las dos que sobrevivieron en la primera corrida (el tope y el fallo del servidor) son los dos primeros defectos de arriba y se corrigieron con pruebas nuevas.

**Recuento.** `python -m pytest -q`: 1.512 pruebas en verde; 160 en `due_diligence/web/tests`. `ruff check` y `ruff format --check` limpios. `python scripts/verify_ecosystem.py` sale con 0.

**No verificado**
- **Recarga de la página:** hallada como defecto y corregida (sección 7).
- La tarjeta de bloqueo por hook no se vio en la página con el modelo real: el modelo se negó por sí mismo a saltarse la regla 1. La cubren las pruebas.
- Los casos 2, 3, 6 y 7 no se recorrieron en la página en esta QA (sí con `scripts/run_casos.py` y en la verificación del #7).
- Chrome, Firefox, Safari y un teléfono real: la vista móvil se comprobó solo por medidas (sin desbordamiento horizontal), porque las capturas con emulación móvil salieron con artefactos.
- El navegador puede servir la página en caché tras cambiar el código (ocurrió una vez); la interfaz no manda `Cache-Control`.

## 7. Defecto hallado por el usuario: el historial se perdía al recargar (T028)

**Qué pasó.** Al recargar la página, el coordinador respondía "es la primera vez que hablamos": la conversación no se recuperaba. La QA de la sección 6 lo había visto (la recarga creó una conversación nueva) pero no pudo concluir si era la página o el navegador integrado; el usuario lo confirmó en su navegador.

**Causa (reproducida).** Se comprobó primero que el navegador no era el culpable: `sessionStorage` y `localStorage` sobrevivían a la recarga. Instrumentando `removeItem`, la traza mostró `removeItem(cid)` en cada recarga. Al descargarse, el navegador cierra el `EventSource` y dispara su `onerror` con la conexión cerrada; la página tomaba eso por "el servidor ya no conoce la conversación (404)", llamaba a `nueva()`, que borra el `cid` guardado y crea otra conversación. La página nueva ya no encontraba la anterior.

**Arreglo.** La página cierra su propio flujo al descargarse (`pagehide` y `beforeunload`), ignora el error mientras se descarga y, si el navegador la restaura desde su caché de navegación (`pageshow` con `persisted`), se reconecta. El camino legítimo se conserva: tras un 404 (el servidor se reinició) se empieza otra conversación.

**Por qué no lo vieron las pruebas anteriores.** Las pruebas de la página solo buscaban texto en el archivo y las de la aplicación probaban el servidor (que sí devolvía el historial). Nadie ejecutaba el script de la página. Ahora `test_pagina_comportamiento.py` lo ejecuta con Node y un navegador simulado (almacenamiento, `EventSource`, `fetch`): 5 pruebas (conectar a la guardada, crear si no hay, descarga, restauración y 404). Se saltan si no hay Node.

**Verificación.** La prueba de la descarga falló antes del arreglo por esa razón ("la recarga borró la conversación guardada") y las otras pasaban. 4 mutaciones (volver a borrar al descargar, quitar `pagehide`/`beforeunload`, no reconectar al restaurar, que el 404 no empiece otra) detectadas. En el navegador integrado con el modelo real: se envió "recuerda la palabra clave ZORRO", se recargó, el `cid` y las 3 tarjetas se conservaron y a la pregunta "¿cuál era la palabra clave?" el coordinador respondió "La palabra clave era ZORRO".

**No verificado:** Chrome, Firefox y Safari reales (solo el navegador integrado y el navegador simulado); la restauración por caché de navegación (`pageshow`) solo con el navegador simulado; reiniciar el servidor sigue perdiendo las conversaciones (límite declarado).

## 8. Segunda ronda de `/abrir-pr 7` (T029)

Ambos revisores son independientes de la sesión que escribió el código y solo leen. El de código recibió el modelo de amenaza (demostración local sin autenticación; se protege el tratamiento como texto, que la interfaz no cambie las reglas, que lo mostrado sea lo que decidió el sistema y que el historial se conserve) y la lista de lo que queda fuera.

**code-reviewer: corregir antes del PR.** 0 bloqueantes, 2 importantes, 7 menores. No pudo ejecutar nada: los hallazgos salen de leer el código.

| # | Hallazgo | Estado |
|---|---|---|
| 1 IMPORTANTE | Un sustituto UTF-16 suelto en lo que escribe el modelo (respuesta, encargo) hacía fallar la codificación del flujo SSE; al reconectar se repetía el historial y moría en la misma tarjeta, sin que la recarga lo arreglara. | **Defecto real, corregido.** La prueba (`test_a_lone_surrogate_in_what_the_model_writes_...`) falló con `UnicodeEncodeError` antes del arreglo. Cada tarjeta se sanea al publicarse (`_sin_sustitutos`, recursivo, cambia el sustituto por U+FFFD). 4 mutaciones detectadas. |
| 2 IMPORTANTE | Las pruebas sobre el tratamiento como texto eran `grep` sobre el HTML: una mutación que cambiara `createTextNode` por un fragmento HTML seguía en verde. | **Tenía razón: pruebas vacías, código correcto.** El arnés de Node ahora entrega una tarjeta con bloques hostiles (`<img onerror>`, `<script>`, `<iframe>`, enlaces `javascript:`, atributos de evento en listas y celdas) y comprueba que solo se crean elementos de formato y que cada literal aparece íntegro como texto; otra prueba cubre el respaldo a texto plano. 5 mutaciones detectadas. |
| 3 MENOR | Expresiones regulares cuadráticas en el analizador (`"**a " * 16000`, o un título con 100.000 espacios) bloquean el bucle de eventos durante segundos. | **Pendiente.** No medido. Un tope de longitud por línea lo resolvería. |
| 4 MENOR | Los topes (100 filas, 100 viñetas, 200 bloques) recortan sin avisar. | **Pendiente.** Conviene un aviso "se omitieron N filas". |
| 5 MENOR | Las listas numeradas se renumeran desde 1 si las separa una línea en blanco o una sublista; se pierde la sangría. | **Pendiente.** |
| 6 MENOR | La tarjeta "Respondió …" toma fuente y fecha del JSON del subagente, no del servidor. | **Pendiente**, y coincide con la observación 2 del revisor de cumplimiento (abajo). |
| 7 MENOR | `obtenido` de un error estructurado se muestra como `repr` de un dict de Python y sin tope. | **Pendiente.** |
| 8 MENOR | Un POST justo después del evento `fin` puede dar un 409 espurio (la tarea termina un instante después). | **Pendiente.** No se pierde el texto. |
| 9 MENOR | El `repr(evento)` del final de `a_vista` es inalcanzable y fugaría datos internos si se añadiera un evento. | **Pendiente.** Una frase fija lo evitaría. |

Lo que el revisor comprobó y no halló problemas: los observadores capturan toda excepción y nunca alteran la decisión, no hay hueco entre el historial y la cola de un suscriptor, y dos POST concurrentes no abren dos turnos.

**compliance-reviewer: cumple parcialmente, sin faltas graves.** Reglas 1 a 3 cumplidas: la interfaz no las altera (los observadores solo leen; hay pruebas de que un observador que lanza no cambia la denegación y de que la salida es idéntica con y sin observador). Reglas 4 y 5 parciales, solo en lo que la interfaz muestra (las imponen los tickets #5 y #4):
1. El hallazgo del registro dice que hay fechas de constitución distintas pero no muestra las dos fechas ni su origen (entrada: el caso 7, `CO-FH-0006`).
2. La fuente y la fecha de la tarjeta "Respondió …" vienen del JSON del subagente, no del servidor (igual que el menor 6 de arriba).
3. El "Sin cubrir" del informe y la tarjeta "Falló" salen de lo que declara el modelo.
Un hueco menor: no hay prueba de que un `on_decision` que falla deje intacta la denegación del guard de aislamiento (`options.py`); el código lo hace bien.

**Recuento tras la ronda.** 168 pruebas en `due_diligence/web/tests`; la suite completa se cerró en 1.520 pruebas en verde, con `ruff` limpio y el ecosistema completo.

