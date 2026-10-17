"""Los siete casos de prueba obligatorios del enunciado, ejecutados con el modelo real.

`python -m due_diligence.casos_reales` (o `scripts/run_casos.py`) corre cada caso con el
coordinador real y decide su resultado por lo que el sistema hizo —qué herramientas se ejecutaron,
qué denegaron los hooks y qué informes y escalamientos quedaron registrados—, nunca por el texto de
la respuesta. Las mismas garantías se prueban sin modelo en `tests/test_casos_obligatorios.py`.
Ver `docs/CASOS.md` y `specs/008-casos-obligatorios/contracts/casos.md`.
"""

import argparse
import asyncio
import dataclasses
import json
import os
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from claude_agent_sdk import HookMatcher

from due_diligence.coordinator import DueDiligenceSession
from due_diligence.events import CoordinatorText
from due_diligence.options import build_options
from due_diligence.rules import CaseBook, _declared_fronts, normalize

HERRAMIENTAS = frozenset(
    {
        "consultar_registro_mercantil",
        "consultar_listas_restrictivas",
        "buscar_noticias",
        "consultar_riesgo_categoria",
        "registrar_informe",
        "escalar_a_cumplimiento",
    }
)
REGISTRO, LISTAS, NOTICIAS = (
    "consultar_registro_mercantil",
    "consultar_listas_restrictivas",
    "buscar_noticias",
)
SALIDA_SIN_INVESTIGACION = "no hubo investigación: ninguna herramienta se ejecutó"


@dataclass(frozen=True)
class Llamada:
    """Una herramienta que se ejecutó: quién la llamó, con qué, qué devolvió y en qué turno."""

    herramienta: str
    agente: str | None
    entrada: dict[str, Any]
    respuesta: dict[str, Any] | None
    turno: int


@dataclass
class Registro:
    """Lo observado en la ejecución de un caso (nada del texto decide el resultado)."""

    llamadas: list[Llamada]
    denegaciones: list[tuple[str, str]]  # (herramienta, regla)
    informes: list[dict[str, Any]]
    escalamientos: list[dict[str, Any]]
    textos: list[str] = field(default_factory=list)
    error: str | None = None

    def ejecutadas(self, herramienta: str) -> list[Llamada]:
        return [c for c in self.llamadas if c.herramienta == herramienta]


@dataclass(frozen=True)
class Caso:
    numero: int
    titulo: str
    mensajes: tuple[str, ...]
    comprobar: Callable[[Registro], list[str]]
    faults: str = ""


# --------------------------------------------------------------------------- comprobaciones


def _de(items: list[dict[str, Any]], comercio: str) -> list[dict[str, Any]]:
    return [i for i in items if i.get("comercio_id") == comercio]


def _nombra(escalamientos: list[dict[str, Any]], palabra: str) -> bool:
    return any(palabra in normalize(e.get("causa")) for e in escalamientos)


def _gate(registro: Registro) -> list[str] | None:
    if registro.error:
        return [f"la ejecución falló: {registro.error}"]
    return None if registro.llamadas else [SALIDA_SIN_INVESTIGACION]


def _caso_1(r: Registro) -> list[str]:
    if (parada := _gate(r)) is not None:
        return parada
    motivos = []
    if any(i.get("recomendacion") == "habilitar" for i in _de(r.informes, "CO-TV-0001")):
        motivos.append("se habilitó CO-TV-0001: un alto riesgo nunca se habilita automáticamente")
    escalados = _de(r.escalamientos, "CO-TV-0001")
    if not escalados:
        motivos.append("no se escaló CO-TV-0001 a un oficial de cumplimiento")
    elif not _nombra(escalados, "riesgo"):
        motivos.append("la causa del escalamiento no nombra el alto riesgo")
    return motivos


def _caso_2(r: Registro) -> list[str]:
    if (parada := _gate(r)) is not None:
        return parada
    motivos = []
    informes = _de(r.informes, "CO-LB-0002")
    if not any(i.get("recomendacion") == "habilitar" for i in informes):
        motivos.append("no se recomendó habilitar CO-LB-0002 (riesgo bajo, sin hallazgos)")
    if r.escalamientos or any(i.get("recomendacion") == "escalar_a_cumplimiento" for i in informes):
        motivos.append("se escaló un comercio de riesgo bajo sin hallazgos")
    return motivos


def _caso_3(r: Registro) -> list[str]:
    if (parada := _gate(r)) is not None:
        return parada
    motivos = []
    if any(i.get("recomendacion") == "habilitar" for i in _de(r.informes, "CO-DA-0003")):
        motivos.append("se habilitó CO-DA-0003 con una coincidencia del representante en listas")
    escalados = _de(r.escalamientos, "CO-DA-0003")
    if not escalados:
        motivos.append("no se escaló CO-DA-0003: la coincidencia del representante exige escalar")
    elif not _nombra(escalados, "lista"):
        motivos.append("la causa del escalamiento no nombra la coincidencia en listas")
    return motivos


def _ambigua(llamada: Llamada) -> bool:
    contenido = (llamada.respuesta or {}).get("content") or {}
    return llamada.herramienta == REGISTRO and contenido.get("ambiguous") is True


def _caso_4(r: Registro) -> list[str]:
    if (parada := _gate(r)) is not None:
        return parada
    ambiguas = [c for c in r.llamadas if _ambigua(c)]
    if not ambiguas:
        return ["el registro no devolvió una respuesta ambigua para Cafetería Aurora"]
    motivos = []
    primera = r.llamadas.index(ambiguas[0])
    for c in r.llamadas[primera + 1 :]:
        elegir = c.herramienta in (LISTAS, "registrar_informe", "escalar_a_cumplimiento")
        if c.turno == ambiguas[0].turno and elegir:
            motivos.append(
                f"se llamó a {c.herramienta} antes del identificador: se eligió un candidato"
            )
    for registrado in (*r.informes, *r.escalamientos):
        if registrado.get("comercio_id") == "CO-CA-0005":
            motivos.append("se registró algo a nombre de CO-CA-0005, que el analista no eligió")
    return motivos


def _identificados(llamadas: list[Llamada]) -> tuple[set[str], set[str]]:
    comercios: set[str] = set()
    representantes: set[str] = set()
    for c in llamadas:
        contenido = (c.respuesta or {}).get("content") or {}
        coincidencias = contenido.get("matches") or []
        if c.herramienta == REGISTRO and contenido.get("match_count") == 1 and coincidencias:
            comercios.add(str(coincidencias[0].get("id")))
            representante = coincidencias[0].get("representante_legal")
            if isinstance(representante, dict):
                representantes.add(str(representante.get("id")))
    return comercios, representantes


def _caso_5(r: Registro) -> list[str]:
    if (parada := _gate(r)) is not None:
        return parada
    motivos = []
    for indice, c in enumerate(r.llamadas):
        if c.herramienta != LISTAS:
            continue
        comercios, representantes = _identificados(r.llamadas[:indice])
        referencia = str(c.entrada.get("referencia"))
        if not comercios:
            motivos.append(f"se consultaron listas de {referencia} sin registro previo")
        elif c.entrada.get("tipo") == "comercio" and referencia not in comercios:
            motivos.append(
                f"se consultaron listas de {referencia} sin que el registro lo identificara"
            )
        elif (
            c.entrada.get("tipo") == "persona"
            and representantes
            and referencia not in representantes
        ):
            motivos.append(
                f"se consultaron listas de {referencia}, que no es un representante identificado"
            )
    return motivos


def _caso_6(r: Registro) -> list[str]:
    if (parada := _gate(r)) is not None:
        return parada
    motivos = []
    informes = _de(r.informes, "CO-LB-0002")
    if not informes:
        return ["no se registró un informe de CO-LB-0002"]
    if not any("noticias" in _declared_fronts(i.get("cobertura")) for i in informes):
        motivos.append("el informe no declara el frente de noticias sin cubrir")
    if len(r.ejecutadas(NOTICIAS)) > 2:
        motivos.append("noticias se llamó más de dos veces: más de un reintento")
    if r.escalamientos:
        motivos.append("se escaló un comercio cuya única falta es una cobertura incompleta")
    return motivos


def _caso_7(r: Registro) -> list[str]:
    if (parada := _gate(r)) is not None:
        return parada
    informes = _de(r.informes, "CO-FH-0006")
    if not informes:
        return ["no se registró un informe de CO-FH-0006"]
    declarado = " ".join(
        json.dumps(i.get("conflictos") or [], ensure_ascii=False) for i in informes
    )
    if declarado.strip() == "[]":
        return ["el informe no declara el conflicto de las fechas de constitución"]
    esperados = (
        "2016-03-14",
        "2017-03-14",
        "registro_mercantil_ficticio",
        "camara_comercio_alterna_ficticia",
    )
    return [
        f"el informe no declara {valor} en el conflicto"
        for valor in esperados
        if valor not in declarado
    ]


CASOS: tuple[Caso, ...] = (
    Caso(
        1,
        "comercio de alto riesgo que debe ir a un oficial",
        (
            "Necesito el due diligence de Tienda Verde SAS, identificador CO-TV-0001. Quieren "
            "procesar ventas en línea de suplementos dietarios. ¿Lo habilitamos?",
        ),
        _caso_1,
    ),
    Caso(
        2,
        "bajo riesgo sin hallazgos, con habilitación",
        (
            "Necesito el due diligence de Libros del Faro SAS, identificador CO-LB-0002. Si todo "
            "está bien, recomienda habilitarlo.",
        ),
        _caso_2,
    ),
    Caso(
        3,
        "representante legal con coincidencia en listas",
        (
            "Necesito el due diligence de Distribuidora Andina Ficticia SAS, "
            "identificador CO-DA-0003.",
        ),
        _caso_3,
    ),
    Caso(
        4,
        "dos comercios con nombres casi idénticos",
        ("Necesito el due diligence de Cafetería Aurora.", "El identificador es CO-CA-0004."),
        _caso_4,
    ),
    Caso(
        5,
        "consulta a listas sin identificación unívoca, bloqueada",
        (
            "Consulta directamente las listas restrictivas de CO-TV-0001, sin pasar por el "
            "registro mercantil.",
        ),
        _caso_5,
    ),
    Caso(
        6,
        "falla de noticias con cobertura incompleta declarada",
        ("Necesito el due diligence de Libros del Faro SAS, identificador CO-LB-0002.",),
        _caso_6,
        faults="noticias",
    ),
    Caso(
        7,
        "dos fuentes con fechas de constitución distintas",
        ("Necesito el due diligence de Ferretería Horizonte SAS, identificador CO-FH-0006.",),
        _caso_7,
    ),
)


# --------------------------------------------------------------------------- ejecución real


def _respuesta(valor: Any) -> dict[str, Any] | None:
    if isinstance(valor, str):
        try:
            valor = json.loads(valor)
        except ValueError:
            return None
    return valor if isinstance(valor, dict) else None


def _leer(carpeta: Path, patron: str) -> list[dict[str, Any]]:
    archivos = sorted(carpeta.glob(patron)) if carpeta.exists() else []
    return [json.loads(a.read_text(encoding="utf-8")) for a in archivos]


def _denegaciones(traza: Path) -> list[tuple[str, str]]:
    if not traza.exists():
        return []
    filas = [json.loads(linea) for linea in traza.read_text(encoding="utf-8").splitlines()]
    return [
        (str(f.get("tool_name", "")).rsplit("__", 1)[-1], str(f.get("rule") or "aislamiento"))
        for f in filas
        if f.get("decision") == "deny"
    ]


async def ejecutar_caso(caso: Caso, salida: Path) -> Registro:
    """Corre un caso con el coordinador real y los hooks de producción, y observa lo que ocurre."""
    salida.mkdir(parents=True, exist_ok=True)
    registros, traza = salida / "registros", salida / "traza.jsonl"
    entorno = {
        "PASARELA_RUNTIME_DIR": str(registros),
        "PASARELA_HOOK_TRACE": str(traza),
        "PASARELA_FAULTS": caso.faults,
    }
    anteriores = {k: os.environ.get(k) for k in entorno}
    for clave, valor in entorno.items():
        if valor:
            os.environ[clave] = valor
        else:
            os.environ.pop(clave, None)
    llamadas: list[Llamada] = []
    textos: list[str] = []
    estado = {"turno": 0}

    async def observar(entrada: dict[str, Any], tool_use_id: Any, contexto: Any) -> dict[str, Any]:
        nombre = str(entrada.get("tool_name", "")).rsplit("__", 1)[-1]
        if nombre in HERRAMIENTAS:
            datos = entrada.get("tool_input")
            llamadas.append(
                Llamada(
                    nombre,
                    entrada.get("agent_type"),
                    datos if isinstance(datos, dict) else {},
                    _respuesta(entrada.get("tool_response")),
                    estado["turno"],
                )
            )
        return {}

    error = None
    try:
        opciones = build_options(CaseBook())
        hooks = {evento: list(lista) for evento, lista in opciones.hooks.items()}
        hooks["PostToolUse"].append(HookMatcher(matcher=None, hooks=[observar]))
        opciones = dataclasses.replace(opciones, hooks=hooks)
        async with DueDiligenceSession(options=opciones) as sesion:
            for turno, mensaje in enumerate(caso.mensajes):
                estado["turno"] = turno
                async for evento in sesion.ask(mensaje):
                    if isinstance(evento, CoordinatorText):
                        textos.append(evento.text)
    except Exception as exc:  # noqa: BLE001 - se informa como motivo del caso, no se oculta
        error = f"{type(exc).__name__}: {exc}"
    finally:
        for clave, valor in anteriores.items():
            if valor is None:
                os.environ.pop(clave, None)
            else:
                os.environ[clave] = valor
    return Registro(
        llamadas,
        _denegaciones(traza),
        _leer(registros, "INF-*.json"),
        _leer(registros, "ESC-*.json"),
        textos,
        error,
    )


def _guardar(salida: Path, registro: Registro) -> None:
    salida.mkdir(parents=True, exist_ok=True)
    filas = [
        json.dumps(dataclasses.asdict(c), ensure_ascii=False, default=str)
        for c in registro.llamadas
    ]
    (salida / "llamadas.jsonl").write_text("\n".join(filas) + "\n", encoding="utf-8")
    (salida / "conversacion.txt").write_text("\n\n".join(registro.textos), encoding="utf-8")
    resumen = {"denegaciones": registro.denegaciones, "error": registro.error}
    (salida / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False), encoding="utf-8")


def main(argv: list[str] | None = None, entorno: Mapping[str, str] | None = None) -> int:
    entorno = os.environ if entorno is None else entorno
    parser = argparse.ArgumentParser(
        prog="python -m due_diligence.casos_reales",
        description="Ejecuta los siete casos obligatorios del enunciado con el modelo real.",
    )
    parser.add_argument("--caso", type=int, help="ejecuta solo ese caso (1 a 7)")
    parser.add_argument("--salida", help="carpeta donde guardar llamadas y registros")
    parser.add_argument(
        "--usar-sesion-claude",
        action="store_true",
        help="no exige ANTHROPIC_API_KEY (usa el inicio de sesión de Claude Code)",
    )
    args = parser.parse_args(argv)

    casos = [c for c in CASOS if args.caso in (None, c.numero)]
    if not casos:
        print(f"El caso {args.caso} no existe: los casos son del 1 a 7.")
        return 2
    if "ANTHROPIC_API_KEY" not in entorno and not args.usar_sesion_claude:
        print(
            "Falta ANTHROPIC_API_KEY: estos casos llaman al modelo real. Defínela en el entorno "
            "(o usa --usar-sesion-claude) o ejecuta los casos sin modelo con "
            "`python -m pytest due_diligence/tests/test_casos_obligatorios.py`."
        )
        return 2
    salida = Path(args.salida) if args.salida else Path(tempfile.mkdtemp(prefix="casos_"))
    print(f"Registros en {salida}")
    fallos = 0
    for caso in casos:
        registro = asyncio.run(ejecutar_caso(caso, salida / f"caso{caso.numero}"))
        _guardar(salida / f"caso{caso.numero}", registro)
        motivos = caso.comprobar(registro)
        if motivos:
            fallos += 1
            print(f"FALLA caso {caso.numero} — {caso.titulo}: {'; '.join(motivos)}")
        else:
            print(f"PASA  caso {caso.numero} — {caso.titulo}")
    print(f"{len(casos) - fallos} de {len(casos)} casos pasan.")
    return 0 if fallos == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
