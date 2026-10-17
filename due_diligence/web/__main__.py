"""Arranque del chat: `python -m due_diligence.web` (escucha solo en 127.0.0.1 por defecto)."""

import argparse
import os
from collections.abc import Callable, Mapping, Sequence
from typing import Any

LOCALES = ("127.0.0.1", "localhost", "::1")


def main(
    argv: Sequence[str] | None = None,
    run: Callable[..., Any] | None = None,
    env: Mapping[str, str] | None = None,
    write: Callable[[str], Any] = print,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m due_diligence.web", description=__doc__)
    parser.add_argument("--puerto", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--permitir-red",
        action="store_true",
        help="permite escuchar fuera de esta máquina (la interfaz no tiene autenticación)",
    )
    args = parser.parse_args(argv)
    env = os.environ if env is None else env

    if args.host not in LOCALES and not args.permitir_red:
        write(
            f"Rechazado: '{args.host}' no es local. La interfaz no tiene autenticación y solo debe "
            "escucharse en esta máquina; si de verdad lo necesitas, añade --permitir-red."
        )
        return 2
    if not env.get("ANTHROPIC_API_KEY"):
        write(
            "Aviso: falta la variable de entorno ANTHROPIC_API_KEY (nunca en el repositorio). "
            "La interfaz arranca, pero los turnos fallarán hasta que la definas."
        )
    write(f"Chat de due diligence en http://{args.host}:{args.puerto} (Ctrl+C para terminar).")

    if run is None:
        import uvicorn

        run = uvicorn.run
    from due_diligence.web.app import crear_app

    run(crear_app(), host=args.host, port=args.puerto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
