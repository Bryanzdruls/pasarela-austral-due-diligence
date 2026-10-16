# Research: Automatización del GitHub Project y plugin reutilizable

Cada decisión lleva su alternativa descartada: alimentan `docs/ECOSISTEMA.md` y `DECISIONES.md`.

## Flujo de tickets

### D1. Skills de proyecto para el flujo, no hook ni subagente
- **Decisión**: dos skills, `siguiente-ticket` y `sincronizar-tickets`, con `allowed-tools` limitadas a las herramientas del MCP de GitHub y a `git`/`gh` de solo lectura.
- **Por qué**: el flujo necesita llamar al servidor MCP; un hook de Claude Code corre un script y no puede invocar herramientas MCP. Una skill acota exactamente qué herramientas usa y se invoca por nombre (`/siguiente-ticket`).
- **Alternativas descartadas**: (a) hook de sesión: no puede llamar al MCP y sería invisible; (b) subagente: añade un contexto aparte sin necesidad, las skills ya pueden restringir herramientas; (c) GitHub Action que mueve a Done al fusionar: exige un token con permiso sobre projects guardado como secreto del repositorio y no pasa por el MCP, que es lo que pide el enunciado; queda fuera de alcance (supuesto del spec).

### D2. Dos skills y no una
- **Decisión**: `sincronizar-tickets` (reconciliar estados, idempotente) separada de `siguiente-ticket` (elegir y arrancar), y `siguiente-ticket` ejecuta primero la sincronización.
- **Por qué**: la sincronización se necesita sola (tras fusionar) y al arrancar; cada skill tiene un propósito y una descripción clara.
- **Alternativa descartada**: una sola skill con un argumento `sync`: mezcla dos intenciones y oscurece la descripción que el modelo usa para elegirla.

### D3. Nombres de estado exactos del Project
Las opciones reales del campo `Status` del Project nº 4 son `Todo`, `In Progress`, `In review` y `Done` (con esa capitalización). Los contratos y las skills las usan tal cual; una discrepancia haría fallar la actualización.

### D4. Orden de los tickets
- **Decisión**: primero los tickets de configuración del entorno (#9 y #10, principio VIII de la constitución), después el resto por número ascendente. Si el primero candidato depende de uno abierto, se advierte y se propone el correcto.
- **Por qué**: lo fija la constitución v1.1.1; el Project no tiene etiquetas propias para distinguirlos (solo las etiquetas por defecto de GitHub).
- **Alternativa descartada**: etiqueta `entorno` o campo propio en el Project: añade una convención más que mantener para dos tickets.

### D5. Cómo se detecta "fusionado" para marcar Done
- **Decisión**: para cada ticket en `In review` (y para los que aún estén `In Progress` con un PR), se busca el pull request cuyo cuerpo contiene `Closes #N` (número completo) y, solo si ninguno lo cierra, el de la rama que empieza por el número del ticket; un pull request que solo dice `Refs #N` no cierra el ticket (hallazgo del PR #14, rama `009-fix-…`); si `merged_at` no es nulo, el ticket pasa a `Done`. Un PR cerrado sin fusionar no cambia nada y se informa.
- **Por qué**: ambas señales las usa ya el repositorio (ramas `NNN-…`, `Closes #N`) y cubren fusiones hechas a mano en GitHub.
- **Alternativa descartada**: confiar solo en que el issue esté cerrado: GitHub cierra el issue al fusionar, pero un issue cerrado a mano sin PR no es "fusionado".

### D6. Ampliación de `/abrir-pr`
- **Decisión**: el paso 5 pasa a exigir el movimiento a `In review` por el MCP (con `mcp__github__projects_write`) y un comentario de avance con tres partes fijas (Especificado, Decidido, Pendiente) construido desde `spec.md`, `tasks.md`, `verification.md` y los veredictos. Si el MCP o el toolset no están disponibles, se detiene y lo dice, sin fingir.
- **Por qué**: ya describía el paso; hoy dependía de la memoria de quien lo ejecuta.
- **Alternativa descartada**: un comando nuevo `/cerrar-ticket`: duplicaría `/abrir-pr`, que ya es el punto donde nace el PR.

## Plugin

### D7. Contenido del plugin
- **Decisión**: `pasarela-revision` con el subagente `compliance-reviewer` (genérico), la skill `revisar-cumplimiento` y el hook `real_data_guard`.
- **Por qué**: son las piezas del #9 que otro equipo de la pasarela reutilizaría tal cual: revisar el cumplimiento de las cinco reglas y no escribir datos con forma de reales. El enunciado permite reutilizar los recursos de los requisitos anteriores.
- **Alternativas descartadas**: empaquetar `spec_gate` (depende de la convención `specs/NNN-*` y de la rama de este repositorio) o `secrets_guard` (heurística con límites ya declarados, peor ejemplo de pieza reutilizable); y `code-reviewer`, que revisa contra convenciones de este repositorio.

### D8. Hook autónomo con prueba de paridad
- **Decisión**: `plugins/pasarela-revision/hooks/real_data_guard.py` no importa `common.py` ni nada del repositorio; reimplementa lo mínimo (leer el payload, detectar tarjeta con Luhn, NIT y documento, enmascarar, bloquear con código 2, fallar cerrado). Una prueba compara su detección con la de `.claude/hooks/real_data_guard.py` sobre las mismas entradas.
- **Por qué**: un plugin se copia a otra máquina; no puede depender de `.claude/hooks/common.py`.
- **Alternativa descartada**: que el repositorio use el hook del plugin y borrar el suyo: cambia el comportamiento ya verificado del #9 por razones de orden, y obliga a instalar el plugin para trabajar aquí.

### D9. Ruta de los scripts del hook
Los comandos del hook usan `${CLAUDE_PLUGIN_ROOT}` (la raíz del plugin instalado) con `python` y `args`, el mismo formato que `.claude/settings.json`. Se comprueba al validar el plugin y al instalarlo en un repositorio temporal.

### D10. Catálogo en el mismo repositorio
- **Decisión**: `.claude-plugin/marketplace.json` en la raíz, con el plugin por ruta relativa (`./plugins/pasarela-revision`). Otro equipo lo añade con `claude plugin marketplace add <ruta|owner/repo>` y lo instala con `claude plugin install pasarela-revision@<catálogo>`.
- **Por qué**: cumple "instalable desde un marketplace" sin un segundo repositorio que mantener, y el repositorio privado ya se comparte con los evaluadores.
- **Alternativa descartada**: repositorio de catálogo aparte: más superficie, más historia que mantener, nada que ganar en un MVP.

### D11. `agent:` de la skill dentro del plugin
La skill del plugin usa `context: fork` y `agent: pasarela-revision:compliance-reviewer`, el nombre completo (`<plugin>:<agente>`) con el que la documentación oficial identifica a los agentes de plugin. **Resolución (T021):** la documentación oficial de skills solo describe `agent` para los agentes built-in y los de `.claude/agents/`; no dice cómo resuelve un agente de plugin ni qué pasa si el nombre no coincide, y no se pudo probar con el modelo (`Credit balance is too low`). Se eligió el nombre completo por ser el único documentado y **Verificado en una sesión real** (ver `verification.md`): la skill lanzó el subagente `pasarela-revision:compliance-reviewer`. Alternativa descartada: quitar `agent:` y dejar que la skill se ejecute con el agente por defecto, porque perdería la restricción a solo lectura del subagente, que es lo que hace independiente la revisión.

## Verificación y documentación

### D12. Ampliar `verify_ecosystem.py`
- **Decisión**: tres comprobaciones nuevas (plugin, catálogo, automatización del flujo) en el mismo verificador de biblioteca estándar, con pruebas sobre árboles sintéticos, como las demás (SC-006).
  - Plugin: manifiesto válido; al menos un subagente, una skill y un hook; el hook referenciado existe; ninguna pieza referencia rutas de fuera del plugin.
  - Catálogo: nombre, plugin listado y fuente relativa que existe.
  - Automatización: skills `siguiente-ticket` y `sincronizar-tickets` con herramientas del MCP en `allowed-tools`.
- **Por qué**: ya comprueba los mínimos del enunciado; el plugin es uno de ellos.
- **Alternativa descartada**: que el verificador llame a `claude plugin validate`: exige la CLI instalada y se vuelve lento y frágil en CI; la validación con la CLI queda como paso documentado del quickstart.

### D13. Modelo de amenaza y revisión
Los hooks del plugin son barreras contra descuidos del asistente, no contra ofuscación deliberada (igual que en el #9, `docs/ECOSISTEMA.md` lo declara). Para este ticket hay **una sola** revisión independiente, con el modelo de amenaza escrito y entradas reproducibles.

## Límites conocidos (para `docs/ECOSISTEMA.md`)

- La transición a Done se registra al sincronizar, no en el instante de la fusión.
- El hook del plugin hereda los límites del de datos reales (formatos con prefijo o separadores raros, falsos positivos de Luhn).
- El plugin asume la disposición de Spec Kit (`specs/NNN-*`, `.specify/memory/constitution.md`) para revisar cumplimiento; sin ella, la skill lo dice y revisa solo lo que se le indique.
- Las skills del flujo dependen del Project nº 4 y de los nombres de estado actuales.
