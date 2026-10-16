# Contrato: procedencia, conflictos y ambigüedad

## Lo que devuelve el servidor (ya existe, #1)

Respuesta correcta de cualquier fuente:

```json
{"ok": true, "content": {...}, "metadata": {"source": "noticias_ficticias", "fetched_at": "2026-10-16T12:00:00+00:00"}}
```

Registro mercantil con una contradicción (caso `CO-FH-0006`) y con varios comercios (caso `CO-CA-0004` / `CO-CA-0005`):

```json
{"ok": true, "content": {"match_count": 1, "ambiguous": false, "matches": [{
  "id": "CO-FH-0006", "conflicts": ["fecha_constitucion"],
  "fuentes_registro": [
    {"source": "registro_mercantil_ficticio", "fecha_constitucion": "2016-03-14"},
    {"source": "camara_comercio_alterna_ficticia", "fecha_constitucion": "2017-03-14"}]}]}}
```

```json
{"ok": true, "content": {"match_count": 2, "ambiguous": true, "matches": [{"id": "CO-CA-0004", ...}, {"id": "CO-CA-0005", ...}]}}
```

## `hallazgos` en `registrar_informe` y `escalar_a_cumplimiento`

```json
{
  "registro": {"contenido": "...", "fuente": "registro_mercantil_ficticio", "fecha": "2026-10-16"},
  "listas": {"contenido": "...", "fuente": "listas_restrictivas_ficticias", "fecha": "2026-10-16"},
  "datos_del_analista": {"contenido": "...", "fuente": "analista"}
}
```

- Las claves que son un frente (`registro`, `listas`, `noticias`, `riesgo` y los alias de los subagentes) se comprueban: `fuente` (texto o lista de textos) debe contener el nombre de una fuente que respondió para ese frente, y debe haber una fecha en `fecha`, `fecha_consulta` o `fetched_at`.
- Las demás claves no se comprueban contra las fuentes (no vienen de una).
- Un frente declarado `sin_cubrir` en `cobertura` (#4) no se comprueba.

## `conflictos` en `registrar_informe`

```json
[{"dato": "fecha_constitucion",
  "valores": [{"valor": "2016-03-14", "fuente": "registro_mercantil_ficticio"},
              {"valor": "2017-03-14", "fuente": "camara_comercio_alterna_ficticia"}]}]
```

- Obligatorio solo si el comercio del informe tiene una contradicción señalada por el servidor; debe incluir todos los pares (valor, fuente). Valores de más se aceptan.
- `dato` se compara normalizado (`fecha constitucion` y `fecha_constitucion` valen).
- `escalar_a_cumplimiento` no lleva `conflictos` todavía (D9: handoff del #6).

## `Decision` nuevas (`due_diligence/rules.py`)

| Regla (`Decision.rule`) | Cuándo deniega | Herramienta |
|---|---|---|
| `ambiguedad` | `comercio_id` es un candidato de un resultado ambiguo aún sin identificar | `registrar_informe`, `escalar_a_cumplimiento` |
| `procedencia` | un hallazgo de un frente no cita una fuente que respondió, o no trae fuente o fecha | `registrar_informe`, `escalar_a_cumplimiento` |
| `conflicto` | el comercio tiene una contradicción y `conflictos` no la declara completa | `registrar_informe` |

Orden en `check_informe`: vocabulario → `ambiguedad` → `cobertura` → `procedencia` → `conflicto` → (solo `habilitar`) identificación → regla 2 → regla 3 → `cobertura_habilitar`. Orden en `check_escalar`: `ambiguedad` → `cobertura` → `procedencia`.

## `CaseBook` (altas)

```text
responded: dict[str, dict[str, str]]       # frente -> {fuente normalizada -> fecha}
candidates: set[str]                       # comercios de un resultado ambiguo sin identificar
CommerceCase.conflictos: dict[str, tuple[tuple[str, str], ...]]
check_informe / check_escalar              # ahora aplican las reglas nuevas
```

`observe` alimenta `responded`, `conflictos` y `candidates`; nunca lanza. `PreToolUse` no cambia: ya llama a `check_informe` y `check_escalar` y devuelve la denegación del SDK con el motivo.
