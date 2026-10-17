"""Arnés de escenario: ejecuta un guion de llamadas como lo haría el SDK, con piezas reales.

Lo único simulado es qué herramienta llama el modelo (el guion). Todo lo demás es el código del
sistema: los hooks son los de `build_options(book)` (el cableado de producción: aislamiento por
rol, reglas, observación y parada), las herramientas son las funciones reales de `mcp_server`
(con sus datos ficticios y la inyección de fallas) y los informes y escalamientos se guardan en un
directorio temporal. Ver `specs/008-casos-obligatorios/contracts/casos.md`.
"""

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from due_diligence.options import build_options
from due_diligence.rules import CaseBook
from mcp_server.tools import informes, listas, noticias, registro, riesgo

PREFIX = "mcp__pasarela-fuentes__"

# herramienta -> (función real del servidor, agente que la usa; None = el coordinador)
HERRAMIENTAS: dict[str, tuple[Any, str | None]] = {
    "consultar_registro_mercantil": (registro.consultar_registro_mercantil, "registro_mercantil"),
    "consultar_listas_restrictivas": (listas.consultar_listas_restrictivas, "listas_restrictivas"),
    "buscar_noticias": (noticias.buscar_noticias, "noticias"),
    "consultar_riesgo_categoria": (riesgo.consultar_riesgo_categoria, "riesgo_categoria"),
    "registrar_informe": (informes.registrar_informe, None),
    "escalar_a_cumplimiento": (informes.escalar_a_cumplimiento, None),
}


@dataclass(frozen=True)
class Resultado:
    """Qué pasó con una llamada: si algún hook la rechazó (y con qué regla) y qué devolvió."""

    permitida: bool
    regla: str | None
    motivo: str | None
    respuesta: dict[str, Any] | None


def _denegacion(salida: dict[str, Any]) -> str | None:
    especifico = salida.get("hookSpecificOutput") or {}
    if especifico.get("permissionDecision") == "deny":
        return str(especifico.get("permissionDecisionReason", ""))
    return None


class Escenario:
    """Una conversación simulada con su propio `CaseBook`, su directorio de registros y su traza."""

    def __init__(
        self,
        directorio: Path,
        monkeypatch: Any,
        faults: str = "",
        sin_hooks: tuple[str, ...] = (),
    ):
        # Un directorio propio por escenario: dos escenarios de una prueba no comparten registros.
        self._directorio = Path(tempfile.mkdtemp(dir=directorio))
        self._traza = self._directorio / "traza.jsonl"
        self._monkeypatch = monkeypatch
        self._faults = faults
        self._aplicar_entorno()
        self.book = CaseBook()
        hooks = build_options(self.book).hooks
        self._pre = self._hooks(hooks, "PreToolUse", sin_hooks, quitar_ultimo="PreToolUse-reglas")
        self._post = self._hooks(hooks, "PostToolUse", sin_hooks)
        self._prompt = self._hooks(hooks, "UserPromptSubmit", sin_hooks)
        self._stop = self._hooks(hooks, "Stop", sin_hooks)
        self.entradas_post: list[dict[str, Any]] = []

    @staticmethod
    def _hooks(
        hooks: dict[str, list[Any]],
        evento: str,
        sin_hooks: tuple[str, ...],
        quitar_ultimo: str | None = None,
    ) -> list[Any]:
        if evento in sin_hooks:
            return []
        lista = [hook for matcher in hooks[evento] for hook in matcher.hooks]
        if quitar_ultimo and quitar_ultimo in sin_hooks:
            lista = lista[:-1]
        return lista

    def _aplicar_entorno(self) -> None:
        """El entorno de este escenario (se reaplica en cada llamada: puede haber otro vivo)."""
        self._monkeypatch.setenv("PASARELA_RUNTIME_DIR", str(self._directorio / "registros"))
        self._monkeypatch.setenv("PASARELA_HOOK_TRACE", str(self._traza))
        if self._faults:
            self._monkeypatch.setenv("PASARELA_FAULTS", self._faults)
        else:
            self._monkeypatch.delenv("PASARELA_FAULTS", raising=False)

    # ------------------------------------------------------------------ entradas del SDK

    def _entrada(self, evento: str, **campos: Any) -> dict[str, Any]:
        base = {"hook_event_name": evento, "session_id": "s1", "transcript_path": "", "cwd": "."}
        return {**base, **campos}

    async def solicitud(self, texto: str) -> None:
        """`UserPromptSubmit`: el texto del analista."""
        self._aplicar_entorno()
        for hook in self._prompt:
            await hook(self._entrada("UserPromptSubmit", prompt=texto), None, None)

    async def parada(self, activo: bool = False) -> dict[str, Any]:
        """`Stop`: `{}` si la respuesta puede cerrarse, o el bloqueo con lo que falta."""
        self._aplicar_entorno()
        for hook in self._stop:
            salida = await hook(self._entrada("Stop", stop_hook_active=activo), None, None)
            if salida:
                return salida
        return {}

    async def llamar(
        self, herramienta: str, entrada: dict[str, Any], agente: str | None = None
    ) -> Resultado:
        """Una llamada del modelo: los hooks deciden; si se permite, corre la herramienta real."""
        funcion, _ = HERRAMIENTAS[herramienta]
        self._aplicar_entorno()
        previas = self._filas_traza()
        datos = self._entrada(
            "PreToolUse",
            tool_name=PREFIX + herramienta,
            tool_input=entrada,
            tool_use_id="tu_1",
            agent_type=agente,
            agent_id="ag_1" if agente else None,
        )
        for hook in self._pre:
            motivo = _denegacion(await hook(datos, "tu_1", None))
            if motivo is not None:
                return Resultado(False, self._regla(previas), motivo, None)
        respuesta = funcion(**entrada)
        post = {
            **datos,
            "hook_event_name": "PostToolUse",
            "tool_response": json.dumps(respuesta, ensure_ascii=False),
        }
        self.entradas_post.append(post)
        for hook in self._post:
            await hook(post, "tu_1", None)
        return Resultado(True, None, None, respuesta)

    # ------------------------------------------------------------------ lo registrado

    def registros(self, prefijo: str) -> list[dict[str, Any]]:
        """Informes (`INF`) o escalamientos (`ESC`) guardados, en orden."""
        carpeta = self._directorio / "registros"
        archivos = sorted(carpeta.glob(f"{prefijo}-*.json")) if carpeta.exists() else []
        return [json.loads(a.read_text(encoding="utf-8")) for a in archivos]

    def _filas_traza(self) -> int:
        if not self._traza.exists():
            return 0
        return len(self._traza.read_text(encoding="utf-8").splitlines())

    def _regla(self, previas: int) -> str | None:
        """La regla de la primera denegación nueva de la traza (el aislamiento no lleva regla)."""
        lineas = self._traza.read_text(encoding="utf-8").splitlines()[previas:]
        for linea in lineas:
            fila = json.loads(linea)
            if fila.get("decision") == "deny":
                return fila.get("rule") or "aislamiento"
        return None
