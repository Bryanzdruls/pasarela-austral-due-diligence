"""Arranque del chat: solo local por defecto, con aviso si falta la clave."""

import pytest

from due_diligence.web.__main__ import main


def arrancar(argv=(), env=None):
    llamadas, salida = [], []
    codigo = main(
        list(argv),
        run=lambda app, **kwargs: llamadas.append(kwargs),
        env={} if env is None else env,
        write=salida.append,
    )
    return codigo, llamadas, "\n".join(salida)


def test_by_default_it_listens_only_on_localhost_and_prints_the_address():
    codigo, llamadas, salida = arrancar(env={"ANTHROPIC_API_KEY": "x"})
    assert codigo == 0
    assert llamadas == [{"host": "127.0.0.1", "port": 8000}]
    assert "http://127.0.0.1:8000" in salida


def test_the_port_can_be_changed():
    _, llamadas, salida = arrancar(["--puerto", "8123"], {"ANTHROPIC_API_KEY": "x"})
    assert llamadas[0]["port"] == 8123 and "8123" in salida


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.20", "ejemplo.com", ""])
def test_a_non_local_host_is_refused_without_the_explicit_flag(host):
    codigo, llamadas, salida = arrancar(["--host", host], {"ANTHROPIC_API_KEY": "x"})
    assert codigo == 2 and llamadas == []
    assert "--permitir-red" in salida


def test_the_explicit_flag_allows_a_non_local_host():
    codigo, llamadas, _ = arrancar(
        ["--host", "0.0.0.0", "--permitir-red"], {"ANTHROPIC_API_KEY": "x"}
    )
    assert codigo == 0 and llamadas[0]["host"] == "0.0.0.0"


@pytest.mark.parametrize("host", ["localhost", "::1"])
def test_other_local_names_are_accepted(host):
    codigo, llamadas, _ = arrancar(["--host", host], {"ANTHROPIC_API_KEY": "x"})
    assert codigo == 0 and llamadas[0]["host"] == host


def test_without_the_key_it_warns_but_starts_and_never_prints_a_key():
    codigo, llamadas, salida = arrancar()
    assert codigo == 0 and len(llamadas) == 1
    assert "ANTHROPIC_API_KEY" in salida
    codigo, _, salida = arrancar(env={"ANTHROPIC_API_KEY": "valor-secreto-de-prueba"})
    assert "valor-secreto-de-prueba" not in salida
