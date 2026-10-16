# Data Model: Hooks del SDK para las reglas de negocio 1 a 3

## Recomendación (vocabulario cerrado)

| Valor | Significado |
|---|---|
| `habilitar` | Recomienda habilitar al comercio; sujeta a las reglas 2 y 3 y a la identificación unívoca |
| `no_habilitar` | Recomienda no habilitar; siempre permitida |
| `escalar_a_cumplimiento` | Deriva a un oficial de cumplimiento; siempre permitida |

Cualquier otro valor se rechaza.

## Categorías de alto riesgo (política de la pasarela)

Raíces normalizadas (minúsculas, sin tildes): `apuesta`, `cripto`, `suplemento`, `medicament`. Una categoría cuyo texto normalizado contiene alguna es de alto riesgo.

## Caso de comercio (`CommerceCase`, por identificador de comercio)

| Campo | Origen | Notas |
|---|---|---|
| `id` | resultado del registro | `matches[0].id` |
| `representante_id` | resultado del registro | `matches[0].representante_legal.id`; puede faltar |
| `categoria_registro` | resultado del registro | `matches[0].categoria` |
| `listas_match` | resultados de listas | `true` si hubo coincidencia del comercio **o** del representante; conserva cuál |
| `alto_riesgo` | determinado al decidir | una vez `true`, se conserva |

Solo existe un `CommerceCase` cuando el comercio quedó identificado de forma unívoca.

### Identificación unívoca

El resultado del registro identifica al comercio solo si: `ok == true`, `content.match_count == 1`, `content.ambiguous == false` y `content.matches[0].existe == true`.

## Estado de la conversación (`CaseBook`)

| Dato | Alcance | Notas |
|---|---|---|
| `commerces` | conversación | diccionario `id → CommerceCase` |
| `risk_observations` | solicitud en curso | pares `(categoria consultada, riesgo devuelto)` del catálogo; se limpia con cada solicitud nueva |
| `declared_text` | solicitud en curso | texto de la solicitud del analista; se reemplaza con cada solicitud nueva |

## Decisión (`Decision`)

| Campo | Notas |
|---|---|
| `allowed` | `true` / `false` |
| `rule` | `1`, `2`, `3`, `vocabulario`, `fail_closed` o `None` si se permite |
| `reason` | texto para el modelo: qué regla se incumplió y qué hacer |

## Reglas de decisión

| Acción | Condición para permitir |
|---|---|
| `consultar_listas_restrictivas`, `tipo: comercio` | `referencia` es un comercio identificado |
| `consultar_listas_restrictivas`, `tipo: persona` | `referencia` es el `representante_id` de un comercio identificado |
| `registrar_informe`, `habilitar` | comercio identificado, sin `listas_match`, sin alto riesgo |
| `registrar_informe`, `no_habilitar` o `escalar_a_cumplimiento` | siempre |
| `escalar_a_cumplimiento` | siempre |
| `registrar_informe`, otro valor | nunca (vocabulario) |
