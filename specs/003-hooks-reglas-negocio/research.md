# Research: Hooks del SDK para las reglas de negocio 1 a 3

Cada decisión lleva su alternativa descartada: alimentan `DECISIONES.md`.

## D1. Las decisiones salen de lo que devolvieron las fuentes, observado con `PostToolUse`
- **Decisión**: un `CaseBook` por conversación que `PostToolUse` alimenta con los resultados reales de `consultar_registro_mercantil`, `consultar_listas_restrictivas` y `consultar_riesgo_categoria`; `PreToolUse` decide con ese estado.
- **Por qué**: lo medido con el modelo real (ver D2) muestra que el hook recibe el sobre JSON de cada herramienta. Así la regla no depende de lo que el modelo escriba.
- **Alternativas descartadas**: (a) leer el texto del coordinador o de los subagentes: es justo lo que el enunciado excluye; (b) confiar en que el prompt ordene las llamadas: es la falta grave que este ticket cierra.

## D2. Forma real de la entrada de los hooks (medida con el modelo)
Medido el 2026-10-16 con el SDK 0.2.168:
- `PostToolUse` de una herramienta MCP entrega `tool_response` como **texto** con el sobre del servidor: `{"ok":true,"content":{...},"metadata":{...}}`. La herramienta `Agent` entrega un diccionario. Los hooks se disparan también para las llamadas de los subagentes, con su `agent_type`.
- `UserPromptSubmit` entrega `prompt` (el texto del analista) y `session_id`.
- El resultado del registro trae `content.match_count`, `content.ambiguous` y `content.matches[]` con `id`, `existe`, `representante_legal.id` y `categoria`; el de listas trae `content.match`.
- Hecho relevante: el catálogo devolvió `riesgo: "alto"` para "suplementos dietarios" pero `sin_clasificar` para "suplementos dietarios (venta en línea)" en otra ejecución: la regla 3 no puede depender solo del catálogo (D6).
- La lectura de `tool_response` tolera texto, diccionario y lista de bloques; si no se puede interpretar, no se registra nada (y por tanto no identifica ni autoriza: falla cerrado).

## D3. Regla 1: identificación unívoca por registro, comercio y representante
- **Decisión**: un comercio queda identificado solo si el registro devolvió `ok`, `match_count == 1`, `ambiguous == false` y la coincidencia tiene `existe == true`. `consultar_listas_restrictivas` con `tipo: comercio` exige que `referencia` sea un comercio identificado; con `tipo: persona`, que sea el representante legal de un comercio identificado. Todo lo demás se deniega.
- **Por qué**: es la regla literal del enunciado y cubre el caso "listas sin identificación unívoca, bloqueado".
- **Alternativa descartada**: bastar con que haya habido *alguna* consulta al registro: no impide consultar listas para otro identificador o tras un resultado ambiguo.

## D4. Reglas 2 y 3 se imponen donde sale la decisión: `registrar_informe`
- **Decisión**: la recomendación se verifica en la llamada a `registrar_informe` (campo `recomendacion`). El hook exige un vocabulario cerrado y, si es `habilitar`, rechaza cuando hay coincidencia en listas (regla 2), cuando el comercio es de alto riesgo (regla 3) o cuando no se identificó de forma unívoca (FR-010). `no_habilitar` y `escalar_a_cumplimiento` siempre se permiten; `escalar_a_cumplimiento` (la herramienta) siempre se permite.
- **Por qué**: el texto libre del coordinador no se puede verificar; el informe registrado es el único punto estructurado donde una recomendación de habilitar tiene efecto.
- **Alternativas descartadas**: (a) analizar el texto de la respuesta final del modelo: no es determinista; (b) permitir cualquier `recomendacion` y comprobar por palabras: cambiar la redacción lo esquiva (por eso el vocabulario es cerrado).

## D5. Vocabulario cerrado de la recomendación
`habilitar`, `no_habilitar` y `escalar_a_cumplimiento`, con esa grafía exacta (minúsculas, sin tildes, con guion bajo). Cualquier otro valor se rechaza y el motivo lista los permitidos. El prompt del coordinador los declara para que el modelo los use.
- **Alternativa descartada**: aceptar variantes ("Habilitar", "habilitar comercio"): abre la puerta a esquivar la comprobación.

## D6. Regla 3: la lista de la pasarela manda y tres fuentes de evidencia
- **Decisión**: la categoría cuenta como alto riesgo si, normalizada (sin tildes, minúsculas), contiene una de estas raíces: `apuesta`, `cripto`, `suplemento`, `medicament`. Fuentes de evidencia: (1) la categoría del registro para ese comercio; (2) las consultas al catálogo de riesgo de la solicitud en curso (por su argumento `categoria` o por su resultado `alto`); (3) el texto de la solicitud del analista en curso, leído con `UserPromptSubmit`. Basta una. Una vez determinado para un comercio, se conserva.
- **Por qué**: en la ejecución real el catálogo no clasificó una categoría de la lista; la lista de la pasarela no puede depender de él. La solicitud del analista es la única fuente que existe antes del registro.
- **Alcance de las fuentes (2) y (3)**: se limpian con cada nueva solicitud del analista, para que un comercio de riesgo bajo investigado después de uno de alto riesgo no herede su evidencia; el registro (1) y lo ya determinado se conservan por comercio.
- **Alternativas descartadas**: (a) solo el catálogo (falla con "sin clasificar"); (b) conservar la evidencia de toda la sesión (bloquea de más al cambiar de comercio, y el caso 3 de la verificación del #2 lo habría roto); (c) coincidencia por subcadena genérica sobre cualquier texto de la conversación: demasiado amplia. Raíces en lugar de palabras completas: cubren el singular y el plural y los matices ("venta en línea de suplementos dietarios").
- **Riesgo declarado**: la raíz `cripto` o `suplemento` en la solicitud de un comercio que no es de ese rubro bloquea habilitar (falso positivo hacia el lado seguro: decide un oficial).

## D7. Falla cerrado
Ante una entrada ininterpretable, un resultado con `ok: false`, un campo ausente o una excepción del propio hook, `PreToolUse` deniega y `PostToolUse` no registra. Un error en `PostToolUse` nunca debe convertirse en una autorización.

## D8. Estado por conversación, no global
`DueDiligenceSession` crea un `CaseBook` y lo entrega a `build_options`, que registra los hooks sobre ese objeto. Dos conversaciones no comparten estado. Las pruebas existentes que pasan `options` explícitas siguen funcionando (sin reglas).
- **Alternativa descartada**: estado global del módulo: se filtraría entre conversaciones y entre pruebas.

## D9. El coordinador gana `registrar_informe` y `escalar_a_cumplimiento`
Hasta el #2 el coordinador solo podía delegar y declaraba "no tengo la herramienta de registro". Sin esas dos herramientas las reglas 2 y 3 no tendrían dónde aplicarse. El hook de aislamiento las permite al coordinador (y a nadie más) y las reglas deciden. El contenido del escalamiento (resumen, cobertura, acción recomendada) es del ticket #6; aquí se permite la acción.

## D10. Mensajes de bloqueo útiles
Cada denegación devuelve `permissionDecisionReason` con la regla (1, 2, 3 o "vocabulario"), el motivo y qué hacer (por ejemplo "identifica al comercio en el registro mercantil", "escala a un oficial de cumplimiento"). El rastro `PASARELA_HOOK_TRACE` del #2 incluye ahora la regla.

## D11. Pruebas y verificación por mutación
Pruebas puras de `rules.py` (cada regla: bloqueo y caso permitido), pruebas de los hooks con la forma real de la entrada y una prueba de composición con el guard del #2. Verificación por mutación: romper a propósito cada regla (permitir listas sin identificar, ignorar la coincidencia del representante, ignorar una de las fuentes de alto riesgo, aceptar una recomendación fuera del vocabulario) y comprobar que alguna prueba falla. Comprobación con modelo real documentada en `verification.md`.

## Límites conocidos (para `docs/ECOSISTEMA.md` y la trazabilidad)

- La categoría declarada se lee del texto de la solicitud con raíces de la lista; un analista que declare la categoría con otras palabras (un sinónimo) no se detectaría por esa vía, aunque sí por el registro o el catálogo.
- Si el modelo no llama a `registrar_informe` y solo escribe una recomendación en texto, el hook no actúa sobre ese texto; el sistema depende de que el informe se registre (el prompt lo exige y el informe registrado es lo que queda como salida estructurada).
- Las fallas de las fuentes y la cobertura parcial no se tratan aquí (#4).

## D12. El escalamiento se exige con un hook de parada (A1 del análisis)

- **Decisión**: un hook `Stop` revisa, al intentar terminar la respuesta, si algún comercio tiene coincidencia en listas (regla 2) o alto riesgo (regla 3) y no consta un `escalar_a_cumplimiento` con éxito para él. Si falta, devuelve un bloqueo con el motivo ("escala a un oficial de cumplimiento con `escalar_a_cumplimiento`") y la respuesta continúa. Si el SDK indica que la parada ya fue bloqueada una vez (`stop_hook_active`), deja terminar: una sola exigencia por cierre, sin bucles.
- **Por qué**: la regla 2 del enunciado dice "impide recomendar la habilitación **y escala** el caso". Bloquear solo `habilitar` deja la mitad sin garantizar: el modelo podría limitarse a no recomendar nada y cerrar.
- **Observación del escalamiento**: `PostToolUse` de `escalar_a_cumplimiento` con `ok: true` marca el comercio como escalado; un `invalid_input` del servidor no cuenta (el modelo debe corregir los campos; el contenido es del #6).
- **Alternativas descartadas**: (a) orientarlo solo en el prompt: es la falta grave que se cierra; (b) bloquear sin límite: un fallo persistente del servidor dejaría la conversación sin poder terminar; (c) escalar automáticamente desde el hook: el hook no tiene los hallazgos ni el resumen que el oficial necesita (#6).
- **Límite declarado**: si el modelo cierra tras la primera exigencia sin escalar, el sistema no vuelve a bloquear; queda el rastro y la respuesta del coordinador, y el #6 trabaja el criterio de escalamiento.

## D13. La evidencia de la solicitud solo cuenta para los comercios de esa solicitud (hallazgo de la revisión)

- **Problema**: en la primera versión, la categoría declarada y las consultas al catálogo de la solicitud en curso se aplicaban a cualquier comercio conocido y la marca de alto riesgo quedaba permanente; un comercio limpio investigado antes heredaba el alto riesgo de uno posterior.
- **Decisión**: la evidencia de la solicitud cuenta para (a) los comercios identificados en ella, (b) los que menciona por identificador y (c) si solo se conoce un comercio, ese, **solo para decidir `habilitar` durante la solicitud**, sin marca permanente y sin exigir escalar (podría referirse a un comercio nuevo aún sin identificar). Una categoría declarada en una solicitud sin comercio ("es una casa de apuestas") se arrastra y la consume el primer comercio que se identifique.
- **Alternativas descartadas**: (a) aplicarla a todos (el bloqueante); (b) a ninguno salvo el identificado en la misma solicitud: un seguimiento "en realidad vende apuestas" sobre un comercio ya conocido no se detectaría; (c) arrastrarla indefinidamente: contaminaría comercios no relacionados.
- **Límite**: si hay varios comercios conocidos y la solicitud declara una categoría sin identificador ni nuevo registro, no se asigna a ninguno (queda el registro y el catálogo como fuentes).
