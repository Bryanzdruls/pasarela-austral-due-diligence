# Verificación del ticket #10

Fecha: 2026-10-16. Rama `010-automatizacion-project-plugin`. Cada resultado dice qué se comprobó de verdad y qué no.

## T020: validación con la CLI

| Comando | Resultado |
|---|---|
| `claude plugin validate plugins/pasarela-revision --strict` | Pasa, sin avisos |
| `claude plugin validate . --strict` (catálogo) | Pasa, sin avisos. La primera pasada (sin `--strict`) avisó de que faltaba la descripción del catálogo; se añadió |

## T026: pruebas, estilo y mutación

| Comprobación | Resultado |
|---|---|
| `python -m pytest -q` (todo el repositorio) | 643 pruebas en verde |
| `ruff check .` y `ruff format --check .` | Limpios |
| `python scripts/verify_ecosystem.py` | Código 0, con las tres comprobaciones nuevas (`plugin`, `catálogo de plugins`, `automatización del flujo`) |

Mutación del hook del plugin (`plugins/pasarela-revision/hooks/real_data_guard.py`), restaurando el archivo tras cada una (comprobado con `git diff`):

| Mutación | Resultado |
|---|---|
| Permitir siempre (no salir con 2 al encontrar un valor) | Detectada |
| No enmascarar el valor en el mensaje | Detectada |
| Ignorar `PowerShell` | Detectada |
| Aceptar entrada inválida (fallar abierto) | Detectada |
| No comprobar Luhn | Detectada |

## T027: `/sincronizar-tickets` contra el Project real

Se ejecutó la skill sobre el Project nº 4 con las herramientas del MCP de GitHub (`projects_list`, `list_pull_requests`).

- Estado leído: #1 y #9 en `Done` (PR #12 y #13 fusionados), #2 y #10 en `In Progress` (sin pull request), #3 a #8 y #11 en `Todo`.
- Resultado: ninguna transición aplicable; `Todo está al día`.
- **Idempotencia (SC-003):** una segunda lectura devolvió el mismo estado y las mismas marcas `updated_at`; la skill no escribió nada.
- **Hallazgo propio:** el PR #14 (rama `009-fix-lanzamiento-mcp`) comparte el prefijo `009` con el #9 pero solo lo referencia con `Refs #9`. Con la regla original (rama o `Closes`) la sincronización habría podido marcar `Done` un ticket por un pull request de corrección. Se corrigió la skill: la señal principal es `Closes #N` y el prefijo de rama solo es respaldo; un pull request que solo referencia con `Refs` no cierra el ticket. Hay una prueba nueva.

## T028: `/siguiente-ticket`

- Con el #2 y el #10 en `In Progress`, la skill se detuvo y pidió confirmación antes de tomar otro ticket, sin mover ninguna tarjeta. También advirtió de que el siguiente candidato (#3, de funcionalidad) exige fusionar antes el #10 (principio VIII).
- **No se pudo comprobar** el caso "servidor o toolset no disponibles" (SC-005): no se puede desconectar el MCP desde dentro de la propia sesión. Solo está verificado el texto de la skill (pruebas de `test_flow_skills.py`).

## T029: instalación del plugin en un repositorio ajeno

En una carpeta temporal vacía con `git init`, fuera del proyecto. Línea base antes: sin plugins instalados y solo los dos catálogos oficiales.

| Paso | Resultado |
|---|---|
| `claude plugin marketplace add <ruta>` | Añadido el catálogo `pasarela-austral` |
| `claude plugin install pasarela-revision@pasarela-austral --scope project` | Instalado, versión 0.1.0, habilitado |
| `claude plugin details` | 1 skill (`revisar-cumplimiento`), 1 subagente (`compliance-reviewer`), 1 hook (`PreToolUse`) |
| Tiempo total de añadir, instalar y listar | **5 segundos** (SC-004: menos de 5 minutos) |
| `claude plugin uninstall` y `claude plugin marketplace remove` | Hechos; sin plugins, el catálogo ya no figura y la configuración del repositorio temporal queda vacía |

**No se pudo comprobar** el bloqueo del hook de extremo a extremo con una sesión real: `claude -p` devolvió `Credit balance is too low` y no hubo llamada al modelo. El hook sí está verificado por sus pruebas (subproceso real, paridad con el hook del proyecto y mutaciones), el manifiesto valida en modo estricto y el formato de registro es el mismo que el de los hooks del proyecto, que sí se comprobaron en una sesión real en el ticket #9. Queda pendiente verlo disparar en una sesión con crédito.

Observación: el catálogo se añadió por ruta local, y la CLI lo lee en el sitio (`Read from: …/plugins/pasarela-revision`); instalado desde GitHub se clonaría.

## T021: `agent:` en la skill del plugin

La documentación oficial no aclara cómo resuelve `agent:` una skill de plugin (solo describe los agentes built-in y los de `.claude/agents/`). La skill usa el nombre completo `pasarela-revision:compliance-reviewer`, el documentado para agentes de plugin. **Sin verificar** con una sesión real: hay que comprobarlo con `/agents` y lanzando la skill cuando haya crédito. `claude plugin validate --strict` sigue pasando.

## Revisión independiente (T031)

Una sola revisión de código, con el modelo de amenaza escrito, y una de cumplimiento.

- **compliance-reviewer: `cumple parcialmente`.** Sin faltas graves: el ticket no da por cumplida ninguna regla de negocio. Las reglas 1-3 siguen abiertas hasta el #3, la 4 hasta el #5 y la 5 hasta el #4.
- **code-reviewer: `aprobar`.** Sin bloqueantes. Un importante y nueve menores.

### Corregido
- **Importante (real):** los hooks leían la entrada con la codificación local. En Windows, un `Write` con la etiqueta `Cédula` seguida de un número de ocho dígitos **no se bloqueaba**, tanto en el hook del plugin como en el del proyecto (heredado del #9). Se reprodujo con `test_utf8_input.py` antes de corregir (2 fallos) y ahora lee UTF-8 crudo en ambos (`.claude/hooks/common.py` y el hook del plugin).
- `siguiente-ticket`: un argumento que no está en `Todo` ya no mueve nada.
- `sincronizar-tickets`: el número de `Closes #N` debe coincidir completo y "fusionado" exige fecha de fusión.
- Documentos de diseño y textos obsoletos alineados con las skills.

### Declarado y sin corregir (menores)
- `/abrir-pr` paso 5.4 no repite todos los parámetros de la llamada y no comprueba el estado de origen; su paso 4 no dice qué hacer si la segunda ronda sigue devolviendo `corregir`.
- `siguiente-ticket` invoca `sincronizar-tickets` sin `Skill` en `allowed-tools`; la autorización de los `Done` que escribiría queda bajo la de `siguiente-ticket`.
- `check_flow` del verificador solo exige alguna herramienta `projects` (quitar solo `projects_write` no lo hace fallar), `check_catalog` acepta cualquier carpeta existente como fuente y `check_plugin` no comprueba que el subagente sea de solo lectura ni `context: fork`; una prueba del catálogo usa una comprobación débil.
