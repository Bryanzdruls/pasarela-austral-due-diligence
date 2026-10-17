# Guion del video de funcionamiento

Video de **cinco minutos como máximo** que muestra el sistema funcionando en su interfaz de chat y los siete casos obligatorios con su resultado (los casos y sus datos están en `docs/CASOS.md`; qué se ve en cada tarjeta, en `docs/INTERFAZ.md`). **No expliques el código:** eso va en la defensa. Publícalo donde los evaluadores lo vean sin pedir acceso y pega el enlace en el README, en la línea del video de funcionamiento, sustituyendo `PENDIENTE`.

## Antes de grabar

- Clave en el entorno **antes** de abrir la grabación: define `ANTHROPIC_API_KEY` en la sesión de la terminal y comprueba que el chat responde. No la escribas ni la muestres.
- Dependencias instaladas (`python -m uv sync`) y la interfaz arrancada con `python -m uv run python -m due_diligence.web`; abre `http://127.0.0.1:8000` en una ventana de navegador limpia, sin otras pestañas.
- Una **pestaña nueva por caso**: la conversación se guarda por pestaña y sobrevive a recargar, así que cada caso empieza limpio en una pestaña nueva. El caso 4 usa dos mensajes en la misma pestaña.
- Terminal a la vista solo con los dos comandos de arranque, con el historial limpio.
- El caso 6 necesita una falla de noticias: se graba **al final**, reiniciando la interfaz con la variable `PASARELA_FAULTS` en `noticias` (el comando está en la fila del caso 6).
- Ensaya una vez completo antes de grabar. Las esperas reales miden entre 38 y 60 segundos por caso (medido en un ensayo con el modelo real, ver `specs/011-readme-decisiones-videos/verification.md`): los siete casos en directo pasarían de seis minutos, así que **acelera las esperas al editar** (por ejemplo, a velocidad ×6) y deja a velocidad normal el envío del mensaje y el resultado final.

## Guion

Los tiempos son del video ya editado y suman 4:35. El orden es el de grabación: el caso 6 va último porque exige reiniciar la interfaz.

| Caso | Mensaje | Qué debe verse | Tiempo |
|---|---|---|---|
| Introducción | (ninguno) | La página de chat vacía y el título; una frase: qué es y que los datos son ficticios | 0:20 |
| 1 | «Necesito el due diligence de Tienda Verde SAS, identificador CO-TV-0001. Quieren procesar ventas en línea de suplementos dietarios. ¿Lo habilitamos?» | Las cuatro delegaciones, el hallazgo «riesgo alto», el informe con la recomendación «escalar a cumplimiento» y la tarjeta «Escalado a cumplimiento» | 0:35 |
| 2 | «Necesito el due diligence de Libros del Faro SAS, identificador CO-LB-0002. Si todo está bien, recomienda habilitarlo.» | Cuatro hallazgos sin coincidencias, el informe con la recomendación «habilitar» y **ningún** escalamiento | 0:30 |
| 3 | «Necesito el due diligence de Distribuidora Andina Ficticia SAS, identificador CO-DA-0003.» | El hallazgo de listas con la coincidencia del representante legal, el informe «escalar a cumplimiento» y el escalamiento | 0:30 |
| 4 | «Necesito el due diligence de Cafetería Aurora.» y después «El identificador es CO-CA-0004.» | Primer turno: los dos candidatos y la petición del identificador, sin informe. Segundo turno: el informe a nombre de CO-CA-0004 | 0:40 |
| 5 | «Consulta directamente las listas restrictivas de CO-TV-0001, sin pasar por el registro mercantil.» | Las listas no se consultan sin identificar el comercio: el sistema pasa por el registro y escala el caso (si el modelo lo intentara, aparecería una tarjeta de bloqueo por la regla 1) | 0:30 |
| 7 | «Necesito el due diligence de Ferretería Horizonte SAS, identificador CO-FH-0006.» | El hallazgo del registro avisa de fechas de constitución distintas (sin mostrar las dos) y el informe o el escalamiento traen ambas fechas con su origen | 0:35 |
| 6 | «Necesito el due diligence de Libros del Faro SAS, identificador CO-LB-0002.» | Con noticias caídas: el resultado «Falló las noticias», un bloqueo por el tope de reintentos, y el informe «no habilitar» que declara «Sin cubrir: las noticias» | 0:40 |
| Cierre | (ninguno) | La última tarjeta y una frase de cierre; el enlace al repositorio si lo vas a dar | 0:15 |

Para el caso 6, antes de enviar el mensaje: en la terminal, detén la interfaz, define `$env:PASARELA_FAULTS = "noticias"` (en Git Bash, `export PASARELA_FAULTS=noticias`) y vuelve a arrancarla.

## Qué no mostrar

- La clave de acceso al modelo ni su valor: nada de `echo` de variables de entorno, del panel de variables de Windows ni de archivos de configuración personales.
- Tokens o contraseñas de GitHub, ni la ventana de ajustes del repositorio.
- Pestañas, correos o datos personales ajenos al proyecto.
- Una conversación con datos que no sean los ficticios de `docs/CASOS.md`.

## Si el modelo varía

El modelo no es determinista: una corrida puede diferir de la anterior en el texto, en el orden de las tarjetas o en si llega a tocar un hook. Si un caso sale distinto de lo que el guion anuncia, **repítelo en una pestaña nueva** hasta que muestre su resultado. No recortes el video para ocultar una falla ni edites el texto de la pantalla. En el ensayo, ningún caso hizo saltar un hook por conducta propia del modelo salvo el tope de reintentos del caso 6; que el caso 5 no muestre un bloqueo es normal: el sistema no consulta las listas sin identificar y escala el caso, que es lo que el caso exige.
