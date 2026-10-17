# Research: Escalamiento con criterio y handoff a cumplimiento

Cada decisión lleva su alternativa descartada: alimentan `DECISIONES.md`.

## D1. Los motivos salen de lo que devolvieron las fuentes y de la solicitud
- **Decisión**: `CaseBook.escalation_grounds(comercio_id)` devuelve los motivos del comercio: `listas` (alguna consulta con coincidencia, del comercio o de su representante), `riesgo` (alto riesgo por la lista de la pasarela: registro, catálogo o solicitud; ya existe como `_is_high_risk`), `conflicto` (contradicción señalada por el registro, #5) y `noticias` (menciones en las noticias del comercio). Para un comercio sin identificar solo cuenta el alto riesgo declarado en la solicitud (`_request_evidence`).
- **Por qué**: es la misma garantía de #3 a #5: no depende de lo que el modelo escriba. Los tres primeros motivos ya se observaban; falta observar las menciones de noticias.
- **Alternativa descartada**: dejar que el modelo declare el motivo y comprobar solo la forma: es la falta que el enunciado excluye para lo grave.

## D2. "Hallazgo" y la cobertura incompleta
- **Decisión**: una cobertura incompleta, sola, **no** es un motivo para escalar. Un comercio de riesgo bajo sin coincidencias, contradicciones ni menciones, con un frente sin cubrir, recibe `no_habilitar` con el frente declarado `sin_cubrir` (#4).
- **Por qué**: el enunciado dice "no escala comercios de bajo riesgo sin hallazgos"; un frente que falló no es un hallazgo. Con el modelo real se vio el defecto contrario (#4): `CO-LB-0002` se escaló solo porque noticias o listas fallaron, lo que llenaría al oficial de casos sin nada que revisar cada vez que una fuente se caiga.
- **Alternativa descartada**: permitir escalar por cobertura incompleta: es una lectura plausible ("no se pudo verificar, que decida una persona"), pero contradice la lectura literal del criterio y vacía el filtro. Si la persona prefiere esa lectura, el cambio es una línea (un cuarto motivo `cobertura`) y está documentado.

## D3. Las menciones en noticias permiten escalar, no obligan
- **Decisión**: una respuesta de noticias con `menciones` no vacías marca al comercio de la solicitud (o, si aún no está identificado, al primero que se identifique) como "con menciones". Es un motivo que permite escalar; no se exige escalar por él y no se clasifica el contenido (una mención cultural cuenta igual).
- **Por qué**: el sistema no puede decidir si una noticia es adversa sin interpretar texto libre; permitir (en vez de exigir) deja la decisión al modelo y al oficial sin bloquear un escalamiento legítimo.
- **Alternativa descartada**: ignorar las noticias: bloquearía escalar un comercio con una noticia adversa y sin otro motivo.

## D4. Dónde se aplica el criterio
- **Decisión**: en `escalar_a_cumplimiento` y en `registrar_informe` cuando la recomendación es `escalar_a_cumplimiento` (que es escalar). Regla `escalamiento`. Va justo después de `ambiguedad` y antes de cobertura y procedencia: es el error más fundamental y evita que el modelo corrija formas para recibir al final "no corresponde escalar".
- **Por qué**: si solo se vigilara la herramienta, el modelo podría recomendar `escalar_a_cumplimiento` en el informe sin llamarla y sin motivo.

## D5. Contenido del resumen: el hallazgo del frente que motiva y una causa que nombra el motivo
- **Decisión**: `hallazgos` debe tener una entrada (con su fuente, ya comprobada por `procedencia`) del frente de cada motivo: `listas` ← coincidencia; `riesgo` o `registro` ← alto riesgo (cuando consta en el registro o el catálogo; si solo lo declaró el analista no se exige frente); `noticias` ← menciones. Regla `handoff_hallazgos`. La `causa` debe contener, normalizada, una palabra clave de cada motivo (`lista`, `riesgo`, `contradic`/`conflict`/`discrep`, `noticia`/`mencion`). Regla `handoff_causa`.
- **Por qué**: son los defectos que un resumen "sin conversación" no puede tener: un oficial que lee "revisar" sin el hallazgo de listas no puede actuar. Las palabras clave son comprobables y el rechazo dice cuáles faltan.
- **Alternativas descartadas**: (a) validar la calidad de la redacción: no determinista, se deja a la revisión y al modelo real; (b) exigir hallazgos de los cuatro frentes: el comercio puede tener un frente sin cubrir o no consultado, y ya hay regla de cobertura.
- **Límite declarado**: la comprobación es de presencia de palabras clave; "lista" aparece también en una frase que no nombra la coincidencia.

## D6. Los conflictos viajan al oficial
- **Decisión**: `escalar_a_cumplimiento` acepta `conflictos` (en el servidor, sin validar) y el hook exige para el escalamiento la misma declaración completa que para el informe (`_check_conflictos`). Cierra la limitación D9 del #5.
- **Alternativa descartada**: dejar los conflictos solo en el informe: el oficial no lo lee.

## D7. Orden de las comprobaciones
`check_informe` (recomendación `escalar_a_cumplimiento`): vocabulario → `ambiguedad` → `escalamiento` → cobertura → procedencia → conflicto → resto. `check_escalar`: `ambiguedad` → `escalamiento` → cobertura → procedencia → conflicto → `handoff_hallazgos` → `handoff_causa`. Falla cerrado: una excepción del hook deniega (ya existe).

## D8. Lo que no cambia
El hook `Stop` (exige escalar una vez ante coincidencia o alto riesgo) y `escalation_reasons` (reglas 2 y 3) no cambian: los motivos de escalamiento de este ticket son un conjunto mayor (conflicto y noticias) que solo **permite** escalar.

## D9. Pruebas existentes que cambian
Las que escalaban o recomendaban escalar un comercio sin motivo (en `test_rules_cobertura.py`, `test_rules_procedencia.py` y `test_rule_hooks.py`) siembran un motivo (una coincidencia en listas) y, si procede, el resumen completo. Cada ajuste se anota en `verification.md`.
