# Data Model: README, DECISIONES.md, guion de video y zip de entrega

No hay datos persistentes; estas son las entidades que los scripts leen y producen.

## Hallazgo de comprobación (`Check`)
Mismo tipo que `scripts/verify_ecosystem.py`.
- `name`: texto estable (constante del módulo), usado por las pruebas y por la salida JSON.
- `ok`: booleano.
- `detail`: frase que dice qué se comprobó y, si falla, qué pieza concreta falla. **Nunca contiene el valor de una credencial**: solo el nombre del archivo o el identificador corto del commit.

## Archivo de entrega (zip)
- `ruta`: ubicación del zip (por defecto, fuera del repositorio).
- `miembros`: lista de rutas dentro del zip, con una carpeta raíz común que se ignora al comprobar.
- `tamaño`: bytes del archivo comprimido; desglose en `.git` y resto (informativo).
- **Reglas de validación**:
  - R1 historial: existen `.git/HEAD` y `.git/objects/`.
  - R2 dependencias: ningún componente de ruta es `.venv`, `venv`, `node_modules`, `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache` o `site-packages`, y ningún miembro termina en `.pyc`.
  - R3 tamaño: `tamaño ≤ 50.000.000`.
  - R4 archivos de secretos: ningún miembro cuyo nombre sea `.env`, `.env.*` (salvo `.env.example`), `*.pem`, `*.key`, `credentials*.json` o `id_rsa*`; `.env.example` no puede traer valores (solo `NOMBRE=` o comentarios).
  - R5 contenido: ningún archivo contiene una clave de Anthropic, un token de GitHub ni un marcador de clave privada, tampoco dentro de `.git` (salvo `objects/`, `*.pack` y `*.idx`) ni escrito en UTF-16 o UTF-32.
  - R5b estructura: sin miembros repetidos ni fuera de la carpeta raíz (se rechaza con código 2).
  - R6 historial: el historial extraído (`git log --all`) no contiene esas formas.
  - R7 coincidencia: los archivos del zip fuera de `.git` son exactamente los del último commit (`git ls-tree -r HEAD`) **y el contenido de cada uno es el del commit** (comparado con `git show HEAD:<ruta>`, normalizando los saltos de línea). Un archivo versionado con cambios sin confirmar falla nombrándolo.
  - R8 (solo `--final`): el README tiene un enlace real al video.
  - R9 (solo `--final`): las comprobaciones de documentos de `verify_docs.py` pasan (FR-013: una sola verificación final).

## Documento de cara al evaluador
### README
Secciones obligatorias (por encabezado): qué es, requisitos, cómo correrlo, cómo correr las pruebas, los siete casos, enlaces (Project y video), mapa de piezas y límites conocidos.
- **Validaciones**: las rutas citadas existen; cita el enlace del GitHub Project; la sección del video muestra `PENDIENTE` o una URL.

### DECISIONES
- Tabla con exactamente once filas numeradas del 1 al 11, cada una con cinco celdas con contenido.
- **Validaciones**: ≤ 1000 palabras (sin sintaxis ni bloques de código); las rutas citadas existen.

### Guion del video (`docs/VIDEO.md`)
- Tabla de siete casos con mensaje, resultado esperado y tiempo (`m:ss`), más introducción y cierre.
- **Validaciones**: suma de tiempos ≤ 5:00; aparecen los siete casos y el identificador ficticio de cada uno según `docs/CASOS.md`.

## Estados del enlace del video
`pendiente` (la sección contiene `PENDIENTE` y ninguna URL) → `publicado` (contiene una URL `https://` y no `PENDIENTE`). `verify_docs.py` informa el estado; solo `--final` lo exige publicado.
