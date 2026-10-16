# Plugin `pasarela-revision`

Piezas reutilizables de Claude Code para equipos de la pasarela (due diligence de comercios). Datos y ejemplos ficticios.

## Qué incluye

| Pieza | Qué hace |
|---|---|
| Subagente `compliance-reviewer` | Revisa, solo leyendo (Read, Grep, Glob), si las cinco reglas de negocio de la pasarela están especificadas, implementadas y probadas. Marca como falta grave una regla 1, 2 o 3 que dependa solo de un prompt. |
| Skill `revisar-cumplimiento` | `/pasarela-revision:revisar-cumplimiento <ticket>` lanza ese subagente en un contexto aislado (`context: fork`). |
| Hook `real_data_guard` | Antes de `Edit`, `Write`, `Bash` o `PowerShell`, bloquea contenido con forma de tarjeta (con Luhn), NIT o documento de identidad reales. Los identificadores ficticios (`FICT-NNNN`, `CO-XX-NNNN`) pasan. |

## Instalación

Desde el repositorio donde quieras usarlo (`<ruta>` es la carpeta de este repositorio o `owner/repo` en GitHub):

```text
claude plugin marketplace add <ruta>
claude plugin install pasarela-revision@pasarela-austral --scope project
claude plugin list
```

Reinicia la sesión de Claude Code para que cargue el plugin. Necesita `python` en el PATH (solo biblioteca estándar).

## Uso

- Revisar cumplimiento antes de un pull request: `/pasarela-revision:revisar-cumplimiento 12`.
- El hook actúa solo: si escribes algo con forma de dato real, la acción se bloquea y el mensaje muestra el valor enmascarado.

## Desinstalación

```text
claude plugin uninstall pasarela-revision@pasarela-austral
claude plugin marketplace remove pasarela-austral
```

## Límites y modelo de amenaza

- El hook es una barrera contra **descuidos** del asistente, no contra ofuscación deliberada: una orden que construya el valor en tiempo de ejecución puede eludirlo.
- No reconoce una tarjeta pegada a un prefijo (`prefijo_<dígitos>`) ni con puntos como separador, y puede bloquear un número largo con suma de verificación válida que no es una tarjeta (por ejemplo, una marca de tiempo).
- El subagente usa la disposición de Spec Kit (`specs/NNN-*`, `.specify/memory/constitution.md`) si existe; si no, revisa solo lo que se le indique y lo dice.
- La revisión de cumplimiento no sustituye a una persona: es una segunda mirada independiente.
