# Contrato: plugin `pasarela-revision` y catálogo

## Disposición

```text
.claude-plugin/marketplace.json            # catálogo "pasarela-austral"
plugins/pasarela-revision/
├── .claude-plugin/plugin.json
├── agents/compliance-reviewer.md
├── skills/revisar-cumplimiento/SKILL.md
├── hooks/hooks.json
├── hooks/real_data_guard.py
├── tests/test_real_data_guard.py
└── README.md
```

## Catálogo

```json
{
  "name": "pasarela-austral",
  "owner": { "name": "Equipo de riesgo - Pasarela Austral" },
  "plugins": [
    {
      "name": "pasarela-revision",
      "source": "./plugins/pasarela-revision",
      "description": "Revisión de cumplimiento de las reglas de la pasarela y protección contra datos con forma de reales"
    }
  ]
}
```

## Manifiesto del plugin

`name`, `version` (`0.1.0`), `description`, `author` (sin datos personales). Los componentes se descubren por su carpeta (`agents/`, `skills/`, `hooks/`).

## Subagente

`compliance-reviewer`: `tools: Read, Grep, Glob`. Revisa las cinco reglas contra la especificación y el código que se le indiquen; si el repositorio no usa Spec Kit, lo dice y revisa lo que se le pase. No edita ni ejecuta.

## Skill

`revisar-cumplimiento`: `context: fork`, `allowed-tools: Read Grep Glob`, `argument-hint: <ticket>`. Lanza el subagente en un contexto aislado.

## Hook

- Evento `PreToolUse`, matcher `Edit|Write|Bash|PowerShell`.
- Comando: `python` con `args: ["${CLAUDE_PLUGIN_ROOT}/hooks/real_data_guard.py"]`.
- Entrada: el JSON del hook por stdin (`tool_name`, `tool_input`).
- Salida: código 0 si no hay nada; código 2 con "Contenido con forma de <tarjeta|NIT|documento> reales: <fragmento enmascarado>" por stderr si lo hay; ante un error propio, código 2 (falla cerrado).
- Autocontenido: solo biblioteca estándar, sin importar nada del repositorio.

## Instalación (la que verifica el quickstart)

```text
claude plugin marketplace add <ruta o owner/repo>
claude plugin install pasarela-revision@pasarela-austral --scope project
claude plugin uninstall pasarela-revision@pasarela-austral
claude plugin marketplace remove pasarela-austral
```

`claude plugin validate plugins/pasarela-revision` y `claude plugin validate .` deben terminar sin errores.

## Verificación automática (`scripts/verify_ecosystem.py`)

| Comprobación | Falla si |
|---|---|
| plugin | falta el manifiesto, o no hay al menos un subagente, una skill y un hook, o el hook referenciado no existe, o una pieza referencia fuera del plugin |
| catálogo | falta `marketplace.json`, no lista el plugin o su `source` no existe |
| automatización del flujo | falta `siguiente-ticket` o `sincronizar-tickets`, o sus `allowed-tools` no incluyen las herramientas del MCP de GitHub |
