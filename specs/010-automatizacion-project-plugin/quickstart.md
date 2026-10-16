# Quickstart: validar el ticket #10

Prerrequisitos: Claude Code instalado (`claude --version`), el servidor `github` conectado con el toolset `projects`, y el repositorio en la rama del ticket. Contratos en [contracts/](contracts/), datos en [data-model.md](data-model.md).

## 1. Verificación automática

```text
python scripts/verify_ecosystem.py
python -m pytest -q
python -m ruff check . ; python -m ruff format --check .
```

Esperado: código 0; las comprobaciones de plugin, catálogo y automatización aparecen como `OK`.

## 2. Validar el plugin y el catálogo con la CLI

```text
claude plugin validate plugins/pasarela-revision
claude plugin validate .
```

Esperado: sin errores (los avisos se anotan en `verification.md`).

## 3. Instalarlo en un repositorio ajeno (SC-004)

En una carpeta temporal vacía (`git init`):

```text
claude plugin marketplace add <ruta de este repositorio>
claude plugin install pasarela-revision@pasarela-austral --scope project
claude plugin list
```

Esperado: el plugin aparece con su subagente, su skill y su hook. Probar el hook escribiendo un archivo con un número con forma de tarjeta generado en el momento: debe bloquearse. Después:

```text
claude plugin uninstall pasarela-revision@pasarela-austral
claude plugin marketplace remove pasarela-austral
```

Esperado: no queda ninguna pieza del plugin.

## 4. Flujo de tickets

1. `/sincronizar-tickets`: informa de cada cambio o de que todo está al día; repetirlo no cambia nada (SC-003).
2. `/siguiente-ticket`: elige el siguiente por el orden de `data-model.md` y lo pasa a `In Progress`.
3. Con el servidor desconectado: ambas skills se detienen y dicen qué falta, sin cambios (SC-005).
4. `/abrir-pr <n>` en un ticket de prueba: pull request que cierra el issue, comentario de avance de tres partes y ticket en `In review`.
5. Fusionar el pull request y ejecutar `/sincronizar-tickets`: el ticket pasa a `Done`.

## 5. Quitar una pieza (SC-006)

Renombrar `plugins/pasarela-revision/hooks/hooks.json` y ejecutar `python scripts/verify_ecosystem.py`: falla nombrando el plugin. Restaurarlo.
