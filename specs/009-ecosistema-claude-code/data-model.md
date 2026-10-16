# Data Model: Ecosistema de Claude Code

## Inventario de piezas (`docs/ECOSISTEMA.md`)

Cada pieza del ecosistema tiene exactamente una fila (SC-007):

| Campo | Notas |
|---|---|
| `Pieza` | ruta relativa al repositorio (clave única) |
| `Tipo` | memoria · regla · subagente · skill · comando · hook · permiso · servidor MCP · script |
| `Necesidad` | `N1` … `N9`, o `E*` para un mínimo del enunciado |
| `Ubicación` | dónde vive |
| `Por qué ahí` | motivo de la ubicación |
| `Alternativa descartada` | qué otra opción se evaluó y por qué no |

La verificación automática falla si hay una pieza en disco sin fila, o una fila cuya ruta ya no existe.

## Feature activa (para el hook de especificación)

| Dato | Origen |
|---|---|
| Número de ticket | prefijo numérico de la rama actual (`NNN-…`); si no lo tiene, el puntero `.specify/feature.json` |
| Carpeta de especificación | la única `specs/NNN-*` con ese número |
| Artefactos exigidos | `spec.md`, `plan.md`, `tasks.md` |

Sin número de ticket, o sin carpeta, o con algún artefacto ausente → "especificación incompleta".

## Código de producción (para el hook de especificación)

Es código de producción todo archivo `.py` cuya ruta relativa **no** contenga ninguno de estos directorios: `tests`, `scripts`, `.claude`, `.specify`, `.venv`, `docs`, `specs`. El criterio es por exclusión: un directorio de código nuevo queda protegido sin tocar la configuración. No son código de producción: documentos, datos JSON, configuración y pruebas.

Para `Bash`, se trata como escritura de código de producción una orden que escribe (redirección `>` o `>>`, `tee`, `Set-Content`, `Out-File`, `sed -i`, `cp` o `mv` hacia, o `python` que abre para escribir) un archivo `.py` que cumple lo anterior.

## Reglas de detección de datos reales

| Tipo | Forma detectada | Se excluye |
|---|---|---|
| Tarjeta | 13 a 19 dígitos contiguos o en grupos de 4 separados por espacio o guion, que pasen la comprobación de Luhn | cadenas que no pasan Luhn; identificadores `FICT-NNNN` y `CO-XX-NNNN` |
| NIT | `NNN.NNN.NNN-D` o `NNNNNNNNN-D` | los NIT ficticios `FICT-NNNN` |
| Documento de identidad | etiqueta (`cédula`, `cedula`, `CC`, `NIT`, `documento`, `identificación`) seguida de 6 a 10 dígitos | número sin etiqueta |

## Archivos de secretos (para el hook de secretos)

Se protegen: `.env`, `.env.*` (excepto `.env.example`), cualquier archivo bajo `secrets/`, `*.pem`, `*.key`, `credentials*.json`, `id_rsa*`. Se permite: `.env.example`. Las rutas se normalizan (barras, mayúsculas, rutas relativas o absolutas) antes de comparar.

## Resultado de un hook

| Salida | Significado |
|---|---|
| código 0 | permitir (o, en `PostToolUse`, terminado sin problemas) |
| código 2 + mensaje en stderr | bloquear; el mensaje explica qué se detectó y qué hacer |
| cualquier otro código | error no bloqueante: **los scripts de bloqueo lo evitan** capturando sus errores y saliendo con 2 |
