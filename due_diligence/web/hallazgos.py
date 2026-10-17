"""Hallazgo de cada fuente en una frase, redactado a partir del sobre que devolvió el servidor.

Función pura: no depende del modelo (lo que el modelo cuente de la fuente no es una prueba) y no
inventa: si el contenido no tiene la forma esperada devuelve `None` y no se muestra nada.
"""

from typing import Any

from due_diligence.events import FrontName
from due_diligence.rules import LISTAS, NOTICIAS, REGISTRO, RIESGO

FRENTE_DE = {
    REGISTRO: FrontName.REGISTRO_MERCANTIL,
    LISTAS: FrontName.LISTAS_RESTRICTIVAS,
    NOTICIAS: FrontName.NOTICIAS,
    RIESGO: FrontName.RIESGO_CATEGORIA,
}


_MAX_SUJETO = 80


def _cadena(valor: Any) -> str:
    return valor.strip() if isinstance(valor, str) else ""


def _plano(texto: str) -> str:
    """Una sola línea y de tamaño acotado: lo preguntado lo escribe el modelo."""
    texto = " ".join(texto.split())
    return texto if len(texto) <= _MAX_SUJETO else texto[:_MAX_SUJETO].rstrip() + "…"


def _sujeto_listas(consulta: dict[str, Any]) -> str:
    tipo, referencia = _cadena(consulta.get("tipo")), _cadena(consulta.get("referencia"))
    if not referencia:
        return ""
    if tipo == "comercio":
        return f"el comercio {_plano(referencia)}"
    if tipo == "persona":
        return f"la persona {_plano(referencia)}"
    return ""


def _registro(contenido: dict[str, Any], consulta: dict[str, Any]) -> str | None:
    encontrados = contenido.get("matches")
    if not isinstance(encontrados, list) or not all(isinstance(c, dict) for c in encontrados):
        return None
    if not encontrados:
        return "Ningún comercio coincide con la consulta."
    if len(encontrados) > 1:
        candidatos = ", ".join(
            f"{_cadena(c.get('id'))} ({_cadena(c.get('razon_social'))})" for c in encontrados
        )
        return (
            f"{len(encontrados)} comercios con nombre parecido: {candidatos}. "
            "Hace falta el identificador para continuar."
        )
    (comercio,) = encontrados
    id_, razon = _cadena(comercio.get("id")), _cadena(comercio.get("razon_social"))
    if not id_ or not razon:
        return None
    frase = f"{id_}, {razon}"
    if estado := _cadena(comercio.get("estado")):
        frase += f", estado {estado}"
    frase += "."
    representante = comercio.get("representante_legal")
    if nombre := _cadena(representante.get("nombre") if isinstance(representante, dict) else None):
        frase += f" Representante legal: {nombre}."
    if "fecha_constitucion" in (comercio.get("conflicts") or []):
        frase += " Las fuentes del registro reportan fechas de constitución distintas."
    return frase


def _listas(contenido: dict[str, Any], consulta: dict[str, Any]) -> str | None:
    coincide = contenido.get("match")
    if not isinstance(coincide, bool):
        return None
    sujeto = _sujeto_listas(consulta)
    para = f" para {sujeto}" if sujeto else ""
    if not coincide:
        return f"Sin coincidencias en las listas restrictivas{para}."
    entradas = contenido.get("entradas")
    partes = []
    for entrada in entradas if isinstance(entradas, list) else []:
        if isinstance(entrada, dict) and (lista := _cadena(entrada.get("nombre_lista"))):
            desde = _cadena(entrada.get("fecha_inclusion"))
            partes.append(f"{lista} (desde {desde})" if desde else lista)
    return (
        f"Coincidencia en las listas restrictivas{para}"
        + (": " + "; ".join(partes) if partes else "")
        + "."
    )


def _noticias(contenido: dict[str, Any], consulta: dict[str, Any]) -> str | None:
    menciones = contenido.get("menciones")
    if not isinstance(menciones, list):
        return None
    buscado = _cadena(consulta.get("consulta"))
    para = f' para "{_plano(buscado)}"' if buscado else ""
    if not menciones:
        return f"Sin menciones en las noticias{para}."
    cuantas = len(menciones)
    return f"{cuantas} {'mención' if cuantas == 1 else 'menciones'} en las noticias{para}."


def _riesgo(contenido: dict[str, Any], consulta: dict[str, Any]) -> str | None:
    categoria, nivel = _cadena(contenido.get("categoria")), _cadena(contenido.get("riesgo"))
    if not categoria or not nivel:
        return None
    return f"Categoría {categoria}: riesgo {nivel.replace('_', ' ')}."


_RESUMEN = {REGISTRO: _registro, LISTAS: _listas, NOTICIAS: _noticias, RIESGO: _riesgo}


def resumen_de(herramienta: str, contenido: dict[str, Any], consulta: Any = None) -> str | None:
    """La frase del hallazgo de `herramienta`, o `None` si el contenido no es el esperado.

    `consulta` es lo que se preguntó a la fuente (la entrada de la herramienta): sirve para decir
    a quién o a qué se refiere el hallazgo; si no es utilizable, la frase sale sin ese dato.
    """
    resumir = _RESUMEN.get(herramienta)
    pregunta = consulta if isinstance(consulta, dict) else {}
    return resumir(contenido, pregunta) if resumir else None
