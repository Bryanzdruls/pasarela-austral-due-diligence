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

## Texto para leer mientras grabas

Está escrito para decirlo tal cual, sin cámara, mientras la pantalla muestra el chat. Cada bloque cabe en el tiempo del guion. Lo que va entre corchetes es una acción tuya: **no se lee**.

Cómo usarlo:
- Lee a ritmo normal. Cuando envíes un mensaje, calla hasta que aparezcan las primeras tarjetas.
- Durante la espera (que luego aceleras al editar) no hace falta narrar. Si quieres cubrir el silencio, usa la frase puente: «El coordinador está trabajando.»
- Si un caso sale distinto de lo que dice el texto (otro orden de tarjetas, un bloqueo que no aparece), **no leas la frase que ya no es cierta**: repite el caso en una pestaña nueva, como indica la sección anterior.

### Introducción (0:20)

[Página vacía del chat, con el título a la vista]

«Esto es Pasarela Austral: un sistema que investiga a un comercio antes de habilitarlo en una pasarela de pagos. Un coordinador reparte el trabajo entre cuatro frentes: registro mercantil, listas restrictivas, noticias y riesgo de la categoría. Todos los datos son ficticios. Voy a correr los siete casos de prueba en el chat y a mostrar el resultado de cada uno.»

### Caso 1 (0:35)

[Pestaña nueva. Pegar y enviar: «Necesito el due diligence de Tienda Verde SAS, identificador CO-TV-0001. Quieren procesar ventas en línea de suplementos dietarios. ¿Lo habilitamos?»]

«Caso uno: un comercio de alto riesgo. Pido el due diligence de Tienda Verde, que quiere vender suplementos dietarios.»

[Esperar. Cuando aparezcan las tarjetas, a velocidad normal]

«El coordinador delega en los cuatro frentes y cada fuente deja su hallazgo. El riesgo de la categoría sale alto. El sistema registra el informe con la recomendación de escalar a cumplimiento, y aquí está la tarjeta de escalamiento. Un comercio de alto riesgo no se habilita: lo revisa una persona.»

### Caso 2 (0:30)

[Pestaña nueva. Pegar y enviar: «Necesito el due diligence de Libros del Faro SAS, identificador CO-LB-0002. Si todo está bien, recomienda habilitarlo.»]

«Caso dos: un comercio de bajo riesgo. Libros del Faro.»

[Esperar. Cuando aparezca el informe]

«Las cuatro fuentes responden sin coincidencias y el riesgo es bajo. El informe recomienda habilitar, y no hay ningún escalamiento.»

### Caso 3 (0:30)

[Pestaña nueva. Pegar y enviar: «Necesito el due diligence de Distribuidora Andina Ficticia SAS, identificador CO-DA-0003.»]

«Caso tres: el representante legal está en una lista restrictiva. Distribuidora Andina.»

[Esperar. Cuando aparezcan el informe y el escalamiento]

«Aquí el hallazgo de listas muestra una coincidencia con el representante legal del comercio. El informe recomienda escalar a cumplimiento y se registra el escalamiento.»

### Caso 4 (0:40)

[Pestaña nueva. Pegar y enviar: «Necesito el due diligence de Cafetería Aurora.»]

«Caso cuatro: dos comercios con nombres casi idénticos. Pido Cafetería Aurora, sin identificador.»

[Esperar la respuesta del primer turno]

«El sistema no elige. Muestra los dos candidatos y me pide el identificador. No hay informe.»

[En la misma pestaña, pegar y enviar: «El identificador es CO-CA-0004.»]

«Le doy el identificador, y ahora sí investiga y registra el informe a nombre de ese comercio.»

### Caso 5 (0:30)

[Pestaña nueva. Pegar y enviar: «Consulta directamente las listas restrictivas de CO-TV-0001, sin pasar por el registro mercantil.»]

«Caso cinco: pido consultar las listas restrictivas sin haber identificado antes al comercio.»

[Esperar]

«Las listas no se consultan sin identificar el comercio. El sistema pasa primero por el registro y, como es un comercio de alto riesgo, escala el caso. Si el modelo hubiera insistido en saltarse el registro, el sistema habría bloqueado la llamada y aquí se vería una tarjeta de bloqueo.»

### Caso 7 (0:35)

[Pestaña nueva. Pegar y enviar: «Necesito el due diligence de Ferretería Horizonte SAS, identificador CO-FH-0006.»]

«Caso siete: dos fuentes que no coinciden. Ferretería Horizonte.»

[Esperar]

«El registro trae dos fechas de constitución distintas. El sistema no escoge una: el hallazgo avisa de la diferencia y el informe, o el escalamiento, trae las dos fechas con su origen.»

### Caso 6 (0:40) — grabar al final

[Antes: detener la interfaz, definir `$env:PASARELA_FAULTS = "noticias"` y arrancarla de nuevo. Pestaña nueva. Pegar y enviar: «Necesito el due diligence de Libros del Faro SAS, identificador CO-LB-0002.»]

«Caso seis: una fuente que falla. Reinicié el sistema con la fuente de noticias caída a propósito y pido otra vez Libros del Faro.»

[Esperar. Cuando aparezca «Falló las noticias»]

«Noticias falla, y la tarjeta lo dice y señala que se puede reintentar.»

[Solo si aparece la tarjeta de bloqueo]

«Aquí un bloqueo: el sistema no deja consultar la misma fuente más de una vez.»

[Cuando aparezca el informe]

«El informe recomienda no habilitar y declara las noticias como sin cubrir. Un informe parcial no se presenta como completo.»

### Cierre (0:15)

[La última tarjeta a la vista]

«Esos son los siete casos. En todos, lo grave lo decide el sistema y no el texto del modelo. El código y la documentación están en el repositorio. Gracias.»
