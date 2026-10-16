# ruff: noqa: E501  (las cadenas son fragmentos de código fuente a mutar)
"""Verificación por mutación de las reglas de negocio 1 a 3 (ticket #3, solo biblioteca estándar).

Rompe a propósito cada regla en `due_diligence/rules.py` o `rule_hooks.py`, ejecuta las pruebas de
`due_diligence` y comprueba que alguna falla. Restaura los archivos tras cada mutación.
Uso: `python scripts/mutate_rules.py`. Sale con 0 si todas se detectan y con 1 si alguna sobrevive
o no se pudo aplicar.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "due_diligence" / "rules.py"
HOOKS = ROOT / "due_diligence" / "rule_hooks.py"

MUTATIONS = [
    (
        "regla 1: permitir listas sin identificar",
        RULES,
        '        tipo = tool_input.get("tipo") if isinstance(tool_input, dict) else None\n',
        '        return ALLOW\n        tipo = tool_input.get("tipo") if isinstance(tool_input, dict) else None\n',
    ),
    (
        "regla 1: no exigir que la persona sea el representante",
        RULES,
        '        if tipo == "persona" and any(\n            c.representante_id == referencia for c in self.commerces.values()\n        ):\n'
        "            return ALLOW",
        '        if tipo == "persona":\n            return ALLOW',
    ),
    (
        "regla 2: ignorar la coincidencia del representante al observar",
        RULES,
        "            cases = [c for c in self.commerces.values() if c.representante_id == referencia]",
        "            cases = []",
    ),
    (
        "regla 2: una coincidencia no bloquea habilitar",
        RULES,
        "        if any(case.listas.values()):\n            return _deny_regla_2(case)",
        "        if False:\n            return _deny_regla_2(case)",
    ),
    (
        "regla 3: ignorar la categoría del registro",
        RULES,
        "if case.alto_riesgo or is_high_risk(case.categoria_registro) or in_request:",
        "if case.alto_riesgo or False or in_request:",
    ),
    (
        "regla 3: ignorar la solicitud del analista",
        RULES,
        "            is_high_risk(self.declared_text)\n",
        "            False\n",
    ),
    (
        "regla 3: depender solo del catálogo (ignorar la lista de la pasarela)",
        RULES,
        '            is_high_risk(categoria) or riesgo == "alto"\n',
        '            riesgo == "alto"\n',
    ),
    (
        "regla 3: no limpiar la evidencia al cambiar de solicitud",
        RULES,
        "        self.risk_observations = []\n        self.attempts = {}",
        "        self.attempts = {}",
    ),
    (
        "regla 3: la evidencia de una solicitud se aplica a todos los comercios",
        RULES,
        "        in_request = case.id in self._request_commerces and self._request_evidence()",
        "        in_request = self._request_evidence()",
    ),
    (
        "regla 3: se pierde la categoría declarada antes de dar el nombre",
        RULES,
        '            self._carry_text = (self._carry_text + " " + self.declared_text)[-2000:]',
        "            pass",
    ),
    (
        "vocabulario: aceptar una recomendación fuera del vocabulario",
        RULES,
        "if not isinstance(recomendacion, str) or recomendacion not in RECOMMENDATIONS:",
        "if not isinstance(recomendacion, str):",
    ),
    (
        "FR-010: habilitar sin identificar al comercio",
        RULES,
        '        if case is None:\n            return _deny_identificacion(_text(data.get("comercio_id")))',
        '        if False:\n            return _deny_identificacion(_text(data.get("comercio_id")))',
    ),
    (
        "escalamiento: el hook Stop no exige nada",
        HOOKS,
        "            pending = book.escalation_reasons()\n",
        "            pending = {}\n",
    ),
    (
        "escalamiento: un error del servidor cuenta como escalado",
        RULES,
        '        if envelope is None or envelope.get("ok") is not True:\n            return\n',
        "        if envelope is None:\n            return\n",
    ),
    (
        "falla cerrado: una excepción del hook PreToolUse permite",
        HOOKS,
        '            return _deny(\n                f"Una regla de negocio no pudo evaluarse',
        '            return {}\n            return _deny(\n                f"Una regla de negocio no pudo evaluarse',
    ),
]

# Cobertura de los frentes (ticket #4). Los fragmentos llevan saltos de línea reales.
_RESET = """        self.risk_observations = []
        self.attempts = {}"""

MUTATIONS += [
    (
        "reintentos: registro y noticias se cuentan por redacción de la consulta",
        RULES,
        """    return (frente, _subject(frente, tool_input) if frente == "listas" else "*")""",
        """    return (frente, _subject(frente, tool_input) if frente != "registro" else "*")""",
    ),
    (
        "reintentos: la categoría de riesgo reescrita se cuenta como otra consulta",
        RULES,
        """    return (frente, _subject(frente, tool_input) if frente == "listas" else "*")""",
        """    return (frente, _subject(frente, tool_input) if frente in ("listas", "riesgo") else "*")""",
    ),
    (
        "cobertura: el éxito de un comercio borra el fallo de otro",
        RULES,
        """        for case in self._failure_targets(frente, tool_input):
            case.fallos.pop(key, None)""",
        """        for case in self.commerces.values():
            case.fallos.pop(key, None)""",
    ),
    (
        "cobertura: el identificador del informe no se recorta",
        RULES,
        """        key = commerce_id.strip() if isinstance(commerce_id, str) else None""",
        """        key = commerce_id if isinstance(commerce_id, str) else None""",
    ),
    (
        "cobertura: no registrar los fallos de las fuentes",
        RULES,
        """        if tool in SOURCE_TOOLS:
            self._observe_coverage(SOURCE_TOOLS[tool], tool_input, envelope)""",
        """        if False:
            self._observe_coverage(SOURCE_TOOLS[tool], tool_input, envelope)""",
    ),
    (
        "cobertura: un éxito no borra el fallo del sujeto",
        RULES,
        """            self._clear_failure(frente, tool_input)
            return""",
        """            return""",
    ),
    (
        "cobertura: un éxito de otro sujeto borra el fallo del frente",
        RULES,
        """            case.fallos.pop(key, None)""",
        """            for other in [k for k in case.fallos if k[0] == key[0]]:
                case.fallos.pop(other)""",
    ),
    (
        "cobertura: el sujeto no se normaliza",
        RULES,
        """    return normalize(data.get("categoria"))""",
        """    return str(data.get("categoria"))""",
    ),
    (
        "cobertura: la respuesta ilegible cuenta como cubierta",
        RULES,
        """        if envelope is None:
            self._record_failure(frente, tool_input, "ilegible", False, {})
            return""",
        """        if envelope is None:
            return""",
    ),
    (
        "cobertura: los fallos huérfanos no los adopta el comercio",
        RULES,
        """                case.fallos[key] = failure
                del self.orphan_failures[key]""",
        """                del self.orphan_failures[key]""",
    ),
    (
        "cobertura: el fallo de un comercio se mezcla con el de otro",
        RULES,
        """        failures = [*(case.fallos.values() if case else ()), *self.orphan_failures.values()]""",
        """        failures = [
            *(f for c in self.commerces.values() for f in c.fallos.values()),
            *self.orphan_failures.values(),
        ]""",
    ),
    (
        "cobertura: el fallo del comercio no persiste entre solicitudes",
        RULES,
        _RESET,
        _RESET
        + """
        for case in self.commerces.values():
            case.fallos.clear()""",
    ),
    (
        "cobertura: los fallos huérfanos se pierden con la solicitud siguiente",
        RULES,
        _RESET,
        _RESET
        + """
        self.orphan_failures = {}""",
    ),
    (
        "reintentos: no se limitan",
        RULES,
        """        if seguidos >= MAX_ATTEMPTS:""",
        """        if False:""",
    ),
    (
        "reintentos: se repite lo no reintentable",
        RULES,
        """        if not retryable:
            return _deny_reintento(frente, "la falla no es reintentable")""",
        """        if False:
            return _deny_reintento(frente, "la falla no es reintentable")""",
    ),
    (
        "reintentos: los intentos no se reinician con la solicitud",
        RULES,
        _RESET,
        """        self.risk_observations = []""",
    ),
    (
        "reintentos: las fuentes no pasan por el tope en el hook",
        HOOKS,
        """            if tool in SOURCE_TOOLS:
                decisions.append(book.check_fuente(tool, tool_input))""",
        """            if False:
                decisions.append(book.check_fuente(tool, tool_input))""",
    ),
    (
        "declaración: un informe que omite el frente caído se acepta",
        RULES,
        """        return _deny_cobertura(missing) if missing else None""",
        """        return None""",
    ),
    (
        "declaración: `cubierto` cuenta como declarar el frente sin cubrir",
        RULES,
        '        and value.get("estado") == "sin_cubrir"',
        """        and value.get("estado") in ("sin_cubrir", "cubierto")""",
    ),
    (
        "declaración: escalar no exige declarar los frentes caídos",
        RULES,
        """            or self._check_cobertura(data)
""",
        "",
    ),
    (
        "habilitar: no se exige la consulta de listas del comercio",
        RULES,
        """        if "comercio" not in case.listas:""",
        """        if False:""",
    ),
    (
        "habilitar: no se exige la consulta de listas del representante",
        RULES,
        """        if case.representante_id is not None and "persona" not in case.listas:""",
        """        if False:""",
    ),
    (
        "habilitar: la cobertura de listas no se evalúa",
        RULES,
        """        if faltan := self._listas_faltantes(case):
            return _deny_cobertura_habilitar(case, faltan)""",
        """        if False:
            return _deny_cobertura_habilitar(case, [])""",
    ),
    (
        "hook: PostToolUseFailure no registra la falla",
        HOOKS,
        """            book.observe_failure(input_data.get("tool_name"), input_data.get("tool_input"))""",
        """            pass""",
    ),
]

# Procedencia, conflictos y ambigüedad (ticket #5).
MUTATIONS += [
    (
        "procedencia: no se observan las fuentes que respondieron",
        RULES,
        """            self._observe_responded(SOURCE_TOOLS[tool], envelope)""",
        """            pass""",
    ),
    (
        "procedencia: se acepta una fuente que no respondió",
        RULES,
        """    if not all(any(source in text for source in responded) for text in texts):""",
        """    if False:""",
    ),
    (
        "procedencia: se acepta la fuente de otro frente",
        RULES,
        """            problem = _finding_problem(finding, self.responded.get(frente, {}))""",
        """            problem = _finding_problem(
                finding, {k: v for d in self.responded.values() for k, v in d.items()}
            )""",
    ),
    (
        "procedencia: no se exige la fecha de la consulta",
        RULES,
        """    if not any(_text(finding.get(key)) for key in _DATE_KEYS):""",
        """    if False:""",
    ),
    (
        "procedencia: no se exige una fuente legible",
        RULES,
        """    if not texts or not all(texts):""",
        """    if False:""",
    ),
    (
        "procedencia: no se exime el frente declarado sin cubrir",
        RULES,
        """            if frente is None or frente in uncovered:""",
        """            if frente is None:""",
    ),
    (
        "procedencia: se exime todo frente de la comprobación",
        RULES,
        """            if frente is None or frente in uncovered:""",
        """            if True:""",
    ),
    (
        "conflicto: no se registran las contradicciones",
        RULES,
        """        case.conflictos = _contradictions(match.get("conflicts"), match.get("fuentes_registro"))""",
        """        case.conflictos = {}""",
    ),
    (
        "conflicto: se ignora uno de los valores",
        RULES,
        """            for valor, fuente in pares
""",
        """            for valor, fuente in pares[:1]
""",
    ),
    (
        "conflicto: no se comprueba la fuente de cada valor",
        RULES,
        """            names_source = normalize(fuente) in normalize(item.get("fuente"))""",
        """            names_source = True""",
    ),
    (
        "conflicto: un informe sin conflictos se acepta",
        RULES,
        """        return _deny_conflicto(case, missing) if missing else None""",
        """        return None""",
    ),
    (
        "conflicto: el conflicto de un comercio se exige en otro",
        RULES,
        """        wanted = (_text(data.get("comercio_id")) or "").strip().upper()
        case = next((c for cid, c in self.commerces.items() if cid.upper() == wanted), None)""",
        """        case = next((c for c in self.commerces.values() if c.conflictos), None)""",
    ),
    (
        "conflicto: el identificador del informe distingue mayúsculas",
        RULES,
        """        wanted = (_text(data.get("comercio_id")) or "").strip().upper()
        case = next((c for cid, c in self.commerces.items() if cid.upper() == wanted), None)""",
        """        wanted = (_text(data.get("comercio_id")) or "").strip()
        case = next((c for cid, c in self.commerces.items() if cid == wanted), None)""",
    ),
    (
        "conflicto: el nombre del dato no se normaliza",
        RULES,
        """_norm_dato(entry.get("dato")) != _norm_dato(dato)""",
        """entry.get("dato") != dato""",
    ),
    (
        "ambigüedad: no se registran los candidatos",
        RULES,
        """                self.candidates.add(candidate)""",
        """                pass""",
    ),
    (
        "ambigüedad: un candidato identificado sigue siendo candidato",
        RULES,
        """        self.candidates.discard(commerce_id)""",
        """        pass""",
    ),
    (
        "ambigüedad: los candidatos no persisten entre solicitudes",
        RULES,
        _RESET,
        _RESET
        + """
        self.candidates = set()""",
    ),
    (
        "ambigüedad: solo se comprueba para habilitar",
        RULES,
        """        if (ambiguo := self._check_ambiguedad(data)) is not None:""",
        """        if recomendacion == "habilitar" and (ambiguo := self._check_ambiguedad(data)):""",
    ),
    (
        "ambigüedad: el escalamiento no la comprueba",
        RULES,
        """            self._check_ambiguedad(data)
            or self._check_cobertura(data)""",
        """            self._check_cobertura(data)""",
    ),
    (
        "procedencia: la clave del hallazgo solo reconoce el nombre exacto del frente",
        RULES,
        """    return first if first in FRENTES else None""",
        """    return None""",
    ),
    (
        "ambigüedad: el identificador del candidato distingue mayúsculas",
        RULES,
        """        wanted = (_text(data.get("comercio_id")) or "").strip().upper()""",
        """        wanted = (_text(data.get("comercio_id")) or "").strip()""",
    ),
    (
        "procedencia: el escalamiento no la comprueba",
        RULES,
        """            or self._check_procedencia(data)
""",
        "",
    ),
]


def run_tests() -> bool:
    """True si las pruebas pasan."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-x", "due_diligence"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def main() -> int:
    originals = {path: path.read_text(encoding="utf-8") for path in (RULES, HOOKS)}
    if not run_tests():
        print("Las pruebas no pasan sin mutar: arréglalas antes de verificar por mutación.")
        return 1
    problems = 0
    try:
        for name, path, old, new in MUTATIONS:
            text = originals[path]
            if old not in text:
                print(f"NO APLICABLE  {name}")
                problems += 1
                continue
            path.write_text(text.replace(old, new, 1), encoding="utf-8")
            detected = not run_tests()
            path.write_text(text, encoding="utf-8")
            print(f"{'DETECTADA' if detected else 'SOBREVIVIÓ':13s} {name}")
            problems += 0 if detected else 1
    finally:
        for path, text in originals.items():
            path.write_text(text, encoding="utf-8")
    print(f"{len(MUTATIONS) - problems} de {len(MUTATIONS)} detectadas")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
