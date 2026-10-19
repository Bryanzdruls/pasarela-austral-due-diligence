# Contrato: estructura de los documentos

Lo que los comprobadores exigen de cada documento. Escribir bien está por encima de cumplir la forma, pero la forma se comprueba por máquina.

## `README.md` (raíz)

Encabezados obligatorios (se buscan por palabra clave, sin distinguir mayúsculas):

| Sección | Palabra clave | Contenido |
|---|---|---|
| Qué es | `qué es` | dos o tres frases: el escenario, el sistema y que los datos son ficticios |
| Requisitos | `requisitos` | Python 3.12, la herramienta de dependencias, `git`; Node opcional; la clave de acceso al modelo solo para el chat y la ejecución real |
| Cómo correrlo | `correr` | clonar, instalar, definir la clave **como variable de entorno** (nunca en un archivo del repositorio), arrancar la interfaz y abrir la dirección local |
| Pruebas | `pruebas` | el comando y qué esperar (cuántas y que no necesitan clave) |
| Los siete casos | `casos` | cómo recorrerlos en la interfaz (`docs/CASOS.md`, `docs/INTERFAZ.md`) y sin modelo |
| Enlaces | `enlaces` | el GitHub Project y el video de funcionamiento |
| Mapa | `mapa` | dónde vive el sistema, el servidor de fuentes, el ecosistema de Claude Code, las especificaciones y la trazabilidad |
| Límites | `límites` | lo abierto o sin verificar, sin presentarlo como completo |

**Video**: la sección de enlaces lleva `**Video de funcionamiento**: PENDIENTE` o una URL `https://…`. Nunca los dos, nunca ninguno.

## `DECISIONES.md` (raíz)

- Un párrafo inicial de dos o tres líneas.
- Una tabla con cabecera `| # | Necesidad | Mecanismo | Por qué | Alternativa descartada |` y exactamente once filas, numeradas del 1 al 11 en el orden del enunciado:

| # | Necesidad del enunciado |
|---|---|
| 1 | Convenciones del equipo al clonar el repositorio |
| 2 | Preferencias personales que no afectan a los compañeros |
| 3 | Pruebas junto al código, con las mismas convenciones |
| 4 | No escribir código de un ticket sin su especificación |
| 5 | Ningún dato con forma de documento, NIT o tarjeta reales |
| 6 | Archivos de secretos y de entorno sin leer ni modificar |
| 7 | Código formateado tras cada edición |
| 8 | Revisión independiente antes del pull request |
| 9 | Revisión de cumplimiento de las reglas de negocio |
| 10 | Estado de los tickets sincronizado sin intervención manual |
| 11 | Piezas reutilizables por otro equipo |

- Cada mecanismo cita al menos una ruta que existe.
- Una nota final de límites conocidos (máximo tres líneas).
- Tope de 1000 palabras en total.

## `docs/VIDEO.md`

- Lista previa de preparación (clave en el entorno, servidor en marcha, navegador limpio, nada de claves a la vista, conversación nueva por caso).
- Tabla `| Caso | Mensaje | Qué debe verse | Tiempo |` con siete filas, más filas de introducción y cierre; el tiempo en formato `m:ss`.
- Total de tiempos ≤ 5:00.
- Cada caso nombra el identificador ficticio que le corresponde en `docs/CASOS.md`.
- Sección "Qué no mostrar" y sección "Si el modelo varía" (repetir el caso, no editar el video para ocultarlo).
