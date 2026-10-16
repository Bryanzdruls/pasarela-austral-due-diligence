# Pasarela Austral — Due Diligence de Comercios: Constitución

## Core Principles

### I. Reglas de negocio garantizadas, no sugeridas (NON-NEGOTIABLE)
Las cinco reglas de la pasarela son parte del enunciado y no se negocian:
1. Ninguna consulta a listas restrictivas se hace sin que el comercio esté identificado de forma unívoca en el registro mercantil.
2. Una coincidencia en listas restrictivas (comercio o representante legal) impide recomendar la habilitación y escala el caso a un oficial de cumplimiento.
3. Un comercio en categoría de alto riesgo (apuestas, criptoactivos, suplementos dietarios, venta de medicamentos) nunca recibe habilitación automática; decide un oficial de cumplimiento.
4. Cada afirmación del informe tiene su fuente. Si dos fuentes se contradicen, se muestran ambas; nunca se elige una.
5. Si una fuente no responde, el informe declara qué frente quedó sin cubrir; nunca se presenta como completo.

Las reglas 1, 2 y 3 se implementan con **hooks del Agent SDK**. Una instrucción en un prompt nunca es suficiente por sí sola.

### II. Datos exclusivamente ficticios (NON-NEGOTIABLE)
Ningún dato real de comercios, personas, noticias o listas restrictivas, ni en código, datos, logs, tests, specs ni configuración. Identificadores con formato `CO-XX-000N`; NIT, cédulas y tarjetas claramente inventados. Ninguna credencial ni archivo `.env` en el repositorio; los secretos llegan por variables de entorno.

### III. Hooks para lo que debe cumplirse, instrucciones para lo que orienta
Criterio de ubicación: si incumplirlo causa daño o invalida la entrega, se hace cumplir con un hook (determinista, bloquea). Si es una convención o preferencia de estilo, va en `CLAUDE.md` o `.claude/rules/`. Cada regla va en un solo lugar y se justifica en `DECISIONES.md`.

### IV. Spec primero
No se escribe código de producción sin especificación, plan y lista de tareas del ticket en `specs/`. Cada issue de GitHub se convierte en una feature con su carpeta de Spec Kit.

### V. Agentes con contexto explícito y herramientas mínimas
Cada subagente solo tiene las herramientas de su frente y recibe de forma explícita todo el contexto que necesita; no hereda la conversación. Sus resultados separan contenido y metadatos (fuente, fecha). Los errores son estructurados e indican qué se obtuvo y si es reintentable. El ciclo agéntico continúa o termina según la razón de parada del modelo, no por un número fijo de iteraciones ni por buscar palabras en el texto.

### VI. Pruebas junto al código
Los tests viven junto al código que prueban, siguen las mismas convenciones y cubren los siete casos obligatorios del enunciado. Una funcionalidad no está terminada si sus pruebas no pasan.

### VII. Trazabilidad en GitHub
El backlog vive en GitHub y el estado de cada ticket refleja el avance real: In progress al iniciar, In review al abrir el PR, Done al fusionarlo. Cada PR referencia y cierra su issue y el issue recibe comentarios de avance. El historial no se reescribe.

### VIII. Ecosistema de Claude Code primero (NON-NEGOTIABLE)
Antes de implementar cualquier ticket de funcionalidad MUST existir configurado, versionado y funcionando el ecosistema de Claude Code que protege la construcción:
- `CLAUDE.md` con jerarquía (proyecto y por subdirectorio o `@import`), separado de las preferencias personales (`CLAUDE.local.md` y `settings.local.json` ignorados por git).
- Reglas en `.claude/rules/` con alcance por ruta (`paths`).
- Hooks que bloquean antes de ejecutar: escribir código de un ticket sin su especificación en `specs/`; leer o modificar archivos de secretos y variables de entorno; escribir datos con forma de documento de identidad, NIT o tarjeta reales. Y un hook posterior a cada edición que formatea el código.
- Subagentes de revisión independiente y de cumplimiento con herramientas restringidas a su rol, skills con `context: fork`, `allowed-tools` y `argument-hint`, y al menos un comando propio compartido.
- Servidores MCP: el oficial de GitHub con el toolset `projects` habilitado y el propio del escenario, sin credenciales en el repositorio.
- Un plugin que empaqueta subagente, skill y hook reutilizables por otro equipo.

El ecosistema es parte del producto que se entrega y se defiende; no es trabajo posterior. Si una pieza falta, se configura antes de seguir con funcionalidad.

Orden y excepción acotada:
- El ecosistema completo, **incluidos el plugin reutilizable y la automatización del flujo de tickets**, MUST estar configurado antes de que empiece cualquier ticket de funcionalidad.
- Los tickets de configuración del entorno de Claude Code, #9 y #10, se ejecutan primero y en ese orden.
- El ticket #9 se implementa antes de que exista el plugin únicamente porque el plugin empaqueta piezas que el #9 crea y porque ambos son configuración del entorno, no funcionalidad. Es una excepción acotada a esos dos tickets, decidida por el autor el 2026-10-16.
- Esa excepción no vuelve a aplicarse: ningún ticket de funcionalidad (#2 y siguientes) comienza hasta que el #9 y el #10 estén fusionados.

## Restricciones adicionales
- Lenguaje: Python. Servidor MCP propio con datos locales (sin base de datos real). Interfaz de chat web simple.
- Alcance: MVP sólido; ante falta de tiempo se priorizan los comportamientos obligatorios.
- Pocas piezas bien ubicadas antes que muchas decorativas.

## Flujo de desarrollo y revisión
0. Ecosistema de Claude Code completo y fusionado (principio VIII), plugin y automatización incluidos: los tickets #9 y #10 se cierran antes de empezar cualquier ticket de funcionalidad. Sin esto no se empieza ninguno.
1. Tomar el siguiente ticket del Project y moverlo a In progress.
2. `/speckit-specify` (con `/speckit-clarify` si hay ambigüedad) → `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement`.
3. Revisión independiente del código y revisión de cumplimiento de reglas de negocio antes de abrir el PR.
4. PR que cierra el issue; ticket a In review y luego a Done al fusionar.
5. Al cerrar cada ticket, validar lo construido contra el enunciado de la prueba (el PDF) y anotar cualquier brecha.

## Governance
Esta constitución prevalece sobre otras prácticas. Se establece con `/speckit-constitution` una vez por proyecto y toda enmienda se hace con ese mismo comando, documentando su motivo y versión. Los PR verifican cumplimiento de las reglas I y II y del principio VIII. La validación contra el enunciado de la prueba (PDF) se hace al cerrar cada ticket. La complejidad añadida debe justificarse contra una necesidad real. Guía de operación en `CLAUDE.md`.

**Version**: 1.1.1 | **Ratified**: 2026-10-14 | **Last Amended**: 2026-10-16
