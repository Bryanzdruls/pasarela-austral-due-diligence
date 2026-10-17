# Contrato: escalamiento y handoff

## `escalar_a_cumplimiento` (servidor, #1; este ticket añade `conflictos`)

```json
{
  "comercio_id": "CO-XX-0003",
  "hallazgos": {
    "registro": {"contenido": "...", "fuente": "registro_mercantil_ficticio", "fecha": "2026-10-16"},
    "listas": {"contenido": "El representante legal PE-0003 figura en la lista...", "fuente": "listas_restrictivas_ficticias", "fecha": "2026-10-16"}
  },
  "cobertura": {"noticias": {"estado": "sin_cubrir", "motivo": "servicio no disponible tras un reintento"}},
  "conflictos": [],
  "causa": "Coincidencia en listas restrictivas del representante legal.",
  "accion_recomendada": "Revisar el caso antes de habilitar; no habilitar mientras tanto."
}
```

- Obligatorios (el servidor los exige): `comercio_id`, `hallazgos`, `cobertura`, `causa`, `accion_recomendada`.
- `conflictos` es opcional en el servidor (forma de #5: lista de `{dato, valores:[{valor, fuente}]}`); el hook lo exige cuando el comercio tiene una contradicción.

## Reglas nuevas (`due_diligence/rules.py`)

| Regla (`Decision.rule`) | Cuándo deniega | Herramienta |
|---|---|---|
| `escalamiento` | el comercio no tiene ningún motivo (coincidencia en listas, alto riesgo, contradicción o menciones en noticias); para un comercio sin identificar solo cuenta el alto riesgo declarado en la solicitud | `escalar_a_cumplimiento`; `registrar_informe` con `recomendacion: escalar_a_cumplimiento` |
| `handoff_hallazgos` | `hallazgos` no trae el frente que respalda un motivo existente (`listas`, `riesgo` o `registro`, `noticias`) | `escalar_a_cumplimiento` |
| `handoff_causa` | `causa` no contiene una palabra clave de un motivo existente (`lista`, `riesgo`, `contradic`/`conflict`/`discrep`, `noticia`/`mencion`) | `escalar_a_cumplimiento` |

Una cobertura incompleta no es un motivo (D2).

Orden en `check_informe` (con recomendación `escalar_a_cumplimiento`): vocabulario → `ambiguedad` → `escalamiento` → `cobertura` → `procedencia` → `conflicto` → resto.

Orden en `check_escalar`: `ambiguedad` → `escalamiento` → `cobertura` → `procedencia` → `conflicto` → `handoff_hallazgos` → `handoff_causa`.

## `CaseBook` (altas)

```text
CommerceCase.menciones: bool
escalation_grounds(comercio_id) -> dict[str, Ground]    # motivos del comercio (D1)
check_escalar / check_informe                            # aplican las reglas nuevas
```

`observe` marca `menciones` con una respuesta de noticias con `menciones` no vacío; nunca lanza. `rule_hooks.py` no cambia (ya llama a `check_informe` y `check_escalar`).
