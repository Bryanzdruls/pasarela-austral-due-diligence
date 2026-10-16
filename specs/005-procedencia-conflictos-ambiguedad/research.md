# Research: Procedencia, conflictos entre fuentes y ambigüedad

Cada decisión lleva su alternativa descartada: alimentan `DECISIONES.md`. Las decisiones de los tickets anteriores siguen vigentes (#3: las decisiones salen de lo que devolvió el servidor; #4: cobertura y reintentos).

## D1. La procedencia que se garantiza es "la fuente citada respondió de verdad"
- **Decisión**: el `CaseBook` guarda, por frente, las fuentes (y la fecha de consulta) de cada respuesta **correcta** del servidor (`metadata.source` y `metadata.fetched_at`). `registrar_informe` y `escalar_a_cumplimiento` rechazan un hallazgo de un frente cuya `fuente` no sea una de ellas.
- **Por qué**: el servidor ya exige una fuente por hallazgo, pero cualquier texto la cumple; el modelo podría citar una fuente que nunca consultó. Con lo observado la cita se puede verificar sin interpretar el hallazgo.
- **Alternativas descartadas**: (a) validar el contenido de cada afirmación contra la respuesta: requiere interpretar texto libre, no determinista; (b) confiar en el prompt: es la falta que el enunciado excluye para lo grave; (c) atribuir las respuestas a cada comercio: noticias y riesgo corren en paralelo con el registro, antes de que el comercio esté identificado (la misma complicación del #4 D3), a cambio de poco: la fuente es la misma para todos los comercios.
- **Alcance declarado**: la comprobación es de la conversación entera, no por comercio; no detecta un hallazgo de un comercio apoyado en la respuesta de otro.

## D2. Qué cuenta como fuente respondida
- Por frente: la `metadata.source` de cada respuesta `ok: true`; para el registro, también el `source` de cada entrada de `fuentes_registro` de los comercios devueltos (la cámara de comercio alterna es un origen legítimo de un valor del registro).
- La coincidencia se hace con el texto normalizado (minúsculas, sin tildes): la `fuente` del hallazgo debe **contener** el nombre de una fuente respondida; si es una lista, cada elemento debe cumplirlo. Así se toleran decoraciones ("registro_mercantil_ficticio (2026-10-16)") sin aceptar una fuente distinta.
- **Alternativa descartada**: igualdad exacta: el modelo real añade fechas o paréntesis y la regla rechazaría hallazgos legítimos.

## D3. Fecha de la consulta
- **Decisión**: el hallazgo debe traer una fecha no vacía en `fecha`, `fecha_consulta` o `fetched_at`. No se valida contra la fecha observada (el modelo puede copiar la fecha sin la hora).
- **Por qué**: FR-001 pide fuente y fecha; la fecha exacta no aporta garantía si la fuente ya es real.
- **Alternativa descartada**: exigir la fecha exacta: rechazaría hallazgos correctos por formato.

## D4. Qué claves de `hallazgos` son frentes
`front_of_alias` (#4) decide: `registro`, `listas`, `noticias`, `riesgo` y los alias de los subagentes. Las demás claves (p. ej. los datos aportados por el analista) no se comprueban contra las fuentes: no vienen de una fuente. Un hallazgo de un frente declarado `sin_cubrir` (#4) queda exento; uno de un frente que no respondió y no se declaró se rechaza con el motivo "no hay respuesta de esa fuente".

## D5. Contradicciones: la marca del servidor y los valores de `fuentes_registro`
- **Decisión**: al identificar un comercio de forma unívoca, el `CaseBook` lee `conflicts` y `fuentes_registro` del registro: por cada dato señalado, la lista de pares (valor, fuente) con más de un valor distinto. Se guarda en el comercio y persiste entre solicitudes.
- **Por qué**: es lo que el servidor devuelve para el caso del enunciado (`CO-FH-0006`: dos fechas de constitución de dos orígenes) y es verificable sin interpretar nada.
- **Alternativas descartadas**: (a) comparar los valores por nuestra cuenta ignorando la marca: duplica la lógica del servidor y mezcla responsabilidades (el servidor informa); (b) exigirlo al modelo con el prompt: falta grave.
- **Fuera de la garantía**: una contradicción entre frentes distintos (noticia frente a registro) no la señala nadie: se orienta por prompt y se verifica con el modelo real; está declarado.

## D6. Forma del conflicto declarado
`conflictos` (ya existe en `registrar_informe`) es una lista de `{"dato": ..., "valores": [{"valor": ..., "fuente": ...}]}`. El hook exige, por cada dato en conflicto del comercio, una entrada cuyo `dato` coincida (normalizado, con espacios o guiones bajos) y que contenga **todos** los pares (valor, fuente); declarar valores de más se acepta (lado seguro). Un informe sin contradicciones señaladas no está obligado a nada.
- **Alternativa descartada**: texto libre: no determinista.

## D7. Ambigüedad: candidatos sin identificar no admiten informe ni escalamiento
- **Decisión**: cuando el registro responde `ok: true` con `ambiguous: true` y varias coincidencias, cada `id` queda como **candidato**. Un candidato deja de serlo cuando el registro lo identifica de forma unívoca. `registrar_informe` y `escalar_a_cumplimiento` con el `comercio_id` de un candidato aún sin identificar se rechazan (regla `ambiguedad`), con el motivo de pedir el identificador al analista. El estado persiste entre solicitudes: el analista responde en el turno siguiente.
- **Por qué**: las reglas 1 a 3 ya impiden consultar listas y habilitar sin identificación unívoca (#3), pero el modelo podía registrar un informe `no_habilitar` o escalar a nombre de uno de los candidatos que eligió. Se cierra ese hueco sin impedir los informes de un comercio no identificado por otra razón (p. ej. registro caído, caso 4 del #4).
- **Alternativas descartadas**: (a) exigir identificación para todo informe: rompe el informe parcial con el registro caído (#4); (b) limpiar los candidatos con cada solicitud: el analista contesta en la solicitud siguiente y el modelo podría elegir antes.
- **Fuera de la garantía**: que el coordinador no lance noticias o riesgo "sobre" un candidato (esas llamadas no llevan identificador de comercio) y que muestre los candidatos con lo que los distingue: prompt, verificado con el modelo real.

## D8. Orden de las comprobaciones
`check_informe`: vocabulario → `ambiguedad` → `cobertura` (#4) → `procedencia` → `conflicto` → (solo `habilitar`) identificación → regla 2 → regla 3 → `cobertura_habilitar`. `check_escalar`: `ambiguedad` → `cobertura` → `procedencia`. Cada motivo dice qué falta y qué hacer. Falla cerrado: una excepción del hook deniega (ya implementado).

## D9. El escalamiento no lleva conflictos todavía
La herramienta `escalar_a_cumplimiento` no tiene campo `conflictos`; llevarlos al oficial es parte del handoff del #6. Aquí el escalamiento solo se somete a `ambiguedad`, `cobertura` y `procedencia`.

## D10. Pruebas existentes que cambian
Los informes con hallazgos de un frente sin respuesta previa de esa fuente dejan de aceptarse. La mayoría de las pruebas del #3 y el #4 usan `hallazgos: {}`; las que no, siembran la respuesta de la fuente con un ayudante. Cada ajuste se anota en `verification.md` (SC-005).
