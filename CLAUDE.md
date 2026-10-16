# Pasarela Austral — Due diligence de comercios

Prueba técnica: sistema multi-agente (Claude Agent SDK) que investiga a un comercio antes de habilitarlo en una pasarela de pagos **ficticia**. Un coordinador delega en cuatro subagentes (registro mercantil, listas restrictivas, noticias, riesgo de categoría) que consumen un servidor MCP propio con datos locales. Quien conversa con él es un analista interno.

La constitución (`.specify/memory/constitution.md`) manda sobre todo lo demás. Resumen operativo abajo; el detalle está en `docs/convenciones.md`:

@docs/convenciones.md

## Comandos

```bash
python -m uv sync                      # instalar dependencias
python -m uv run pytest -q             # pruebas (todas, sin modelo ni API key)
python -m uv run ruff check .          # lint
python -m uv run ruff format .         # formato (los hooks ya lo hacen tras cada edición)
python -m uv run python -m mcp_server  # servidor MCP de fuentes por stdio
```

`uv` puede no estar en el PATH: usa `python -m uv ...`.

## Reglas de oro

1. **Datos solo ficticios.** Nada con forma de tarjeta, NIT o documento reales; ninguna credencial en el repositorio.
2. **Spec primero.** No se escribe código de producción sin `spec.md`, `plan.md` y `tasks.md` del ticket en `specs/`.
3. **Pruebas primero** y verlas fallar antes de implementar.
4. **Lo grave va en un hook, no en un prompt.** Las reglas de negocio 1 a 3 de la pasarela se garantizan con hooks del Agent SDK.
5. **No saltarse los hooks.** Si uno bloquea, el mensaje dice qué falta; se corrige la causa, no se esquiva.

## Orden de los tickets

El ecosistema de Claude Code se configura **antes** de cualquier funcionalidad: **#9 → #10 → #2** y siguientes (constitución v1.1.1). Ningún ticket de funcionalidad empieza hasta que #9 y #10 estén fusionados.

## Dónde mirar

| Para… | Mira |
|---|---|
| El servidor de fuentes | `mcp_server/CLAUDE.md` |
| El coordinador y los subagentes | `due_diligence/CLAUDE.md` |
| Estado frente al enunciado | `docs/TRAZABILIDAD.md` |
| Por qué cada pieza de Claude Code está donde está | `docs/ECOSISTEMA.md` |
| Cómo se hace cumplir lo grave | `.claude/hooks/` y `.claude/settings.json` |

Tus preferencias personales van en `CLAUDE.local.md` y `.claude/settings.local.json`; ninguno se versiona.
