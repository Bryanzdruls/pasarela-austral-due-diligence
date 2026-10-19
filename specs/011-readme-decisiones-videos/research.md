# Research: README, DECISIONES.md, guion de video y zip de entrega

Cada decisión registra *qué se eligió, por qué y qué alternativa se descartó*; es insumo directo de `DECISIONES.md`.

## D1. Cómo se arma el zip: `git ls-files` más la carpeta `.git`
- **Decisión**: `--build` escribe un zip con los archivos que devuelve `git ls-files` (el árbol versionado) y todo el contenido de `.git`, bajo una carpeta raíz con el nombre del repositorio.
- **Por qué**: el enunciado exige "el repositorio completo, con la carpeta `.git`" y excluir dependencias instaladas. Partir de lo versionado deja fuera por construcción el entorno virtual, las cachés y cualquier archivo local sin versionar (incluido un archivo de entorno con secretos); `.git` va aparte porque `git ls-files` no lo lista.
- **Alternativas descartadas**: `git archive` (no incluye `.git`: incumple el enunciado); comprimir la carpeta del proyecto tal cual (arrastra `.venv`, cachés y, si existiera, un archivo de entorno: el error que hay que evitar); una lista de exclusiones a mano (se desactualiza).

## D2. La verificación abre el zip y usa `git` sobre lo extraído
- **Decisión**: `--zip` extrae el archivo a un directorio temporal y comprueba allí: que existe un repositorio válido (`HEAD` y objetos), que el árbol versionado de ese historial coincide con los archivos del zip, y que el historial completo (`git log --all`) no contiene credenciales.
- **Por qué**: dentro de `.git` los objetos están comprimidos; un escaneo de texto del zip no vería una credencial que alguna vez se confirmó y luego se borró, y esa sigue siendo una credencial entregada. Con el repositorio extraído, `git log --all -G<patrón>` sí la encuentra.
- **Además**: se compara el contenido de cada archivo del zip con el del último commit. `--build` empaqueta el árbol de trabajo; sin esta comparación, un cambio sin confirmar entraría en el zip con un contenido que no está en el historial entregado.
- **Alternativa descartada**: escanear solo los archivos del árbol actual (deja pasar una credencial en el historial).

## D3. Límite de tamaño: 50.000.000 bytes
- **Decisión**: se compara el tamaño del zip con 50.000.000 bytes (decimal), no con 50 MiB.
- **Por qué**: el enunciado dice "50 MB" sin precisar; el límite decimal es el más estricto, así que cumplirlo cumple cualquier lectura. Se informa el desglose (`.git` y resto) para saber qué recortar.
- **Alternativa descartada**: 50 MiB (52.428.800 bytes): deja casi 2,4 MB de margen que una lectura estricta no concede.

## D4. Credenciales: los mismos patrones estrictos del proyecto, el detalle nunca repite el valor
- **Decisión**: claves de Anthropic, tokens de GitHub y marcadores de claves privadas, armados por partes para que el script no contenga ninguna; el mensaje nombra el archivo (o el commit) y la clase de hallazgo, nunca el valor. Además se bloquean por nombre `.env` y `.env.*` (salvo `.env.example` exacto), `*.pem`, `*.key`, `credentials*.json` e `id_rsa*`, coherente con el hook de secretos.
- **Por qué**: es la misma barrera que usan los hooks (#9) y el escaneo manual antes de cada commit, ahora automática y aplicada al artefacto que se entrega. Repetir el valor en el mensaje filtraría la credencial a la terminal y a los registros.
- **Alternativa descartada**: reutilizar el hook de secretos: es de Claude Code (protege el desarrollo), no inspecciona un zip.

## D5. Qué es "dos páginas": 1000 palabras
- **Decisión**: `DECISIONES.md` se mide por su número de palabras (sin sintaxis de Markdown ni bloques de código) con un tope de 1000.
- **Por qué**: una página impresa en cuerpo 11 con tabla densa admite unas 450 a 500 palabras; 1000 deja margen y es medible sin dependencias. Contar líneas o caracteres depende del ancho y de la fuente.
- **Límite declarado**: es un sustituto de la medida de página impresa; no se genera un PDF para contarla.
- **Alternativa descartada**: generar un PDF y contar páginas (exige una dependencia o una herramienta del sistema).

## D6. Formato de `DECISIONES.md`: una tabla con las once necesidades
- **Decisión**: una tabla `# | Necesidad | Mecanismo | Por qué | Alternativa descartada`, con una fila por necesidad del enunciado, más un párrafo inicial de dos o tres líneas y una nota final de límites.
- **Por qué**: el evaluador contrasta "necesidad → mecanismo → alternativa" y la tabla lo muestra de un vistazo; se comprueba por máquina (once filas, cinco celdas con contenido).
- **Alternativa descartada**: secciones con prosa (más cómodas de escribir, pero se desordenan y no se comprueban con facilidad).

## D7. El enlace del video: aviso visible hasta que exista, y la verificación final lo exige
- **Decisión**: la sección del README muestra `PENDIENTE` mientras no haya un enlace. `verify_docs.py` informa el estado sin fallar; `verify_delivery.py --final` falla si sigue pendiente o si el enlace no es una URL.
- **Por qué**: nunca debe haber un enlace inventado (el enunciado pide que se vea sin pedir acceso), pero tampoco puede olvidarse antes de entregar: la verificación final es la red de seguridad.
- **Alternativa descartada**: un enlace de ejemplo (un evaluador lo seguiría y vería un fallo).

## D8. Los comprobadores de documentos son un script aparte, con pruebas contra el repositorio real
- **Decisión**: `scripts/verify_docs.py` independiente de `verify_ecosystem.py`; `test_docs.py` ejecuta sus comprobaciones sobre el repositorio real, de modo que `pytest` vigila que los documentos no se rompan en el futuro.
- **Por qué**: separa lo que verifica el ecosistema (#9) de lo que verifica la entrega; cada uno falla por su causa. Integrarlo en el verificador del ecosistema era opcional y se descarta por no mezclar mínimos de Claude Code con documentación.
- **Alternativa descartada**: ampliar `verify_ecosystem.py` (mezcla dos responsabilidades y alarga un script que ya tiene doce comprobaciones).

## D9. Las rutas citadas se comprueban por máquina
- **Decisión**: toda ruta entre comillas invertidas con barra o con una extensión conocida (`.md`, `.py`, `.json`, `.js`, `.html`, `.toml`) debe existir (con fragmento `#` permitido); se ignoran los comandos con espacios y los patrones con comodines.
- **Por qué**: el enunciado avisa que la defensa contrasta la explicación con el código; un documento que cita un archivo inexistente resta credibilidad.
- **Alternativa descartada**: revisión a mano (se pierde el día de la entrega).

## D10. El tiempo del README se mide, no se estima
- **Decisión**: `verification.md` registra un recorrido real en una copia limpia (`git clone` a un directorio temporal, instalar dependencias, ejecutar las pruebas, arrancar la interfaz y comprobar que responde), con el tiempo de cada paso.
- **Por qué**: SC-001 es medible; una estimación no lo demuestra y el primer evaluador lo comprobaría. Si supera cinco minutos se acortan los pasos (por ejemplo, ejecutar solo un subconjunto de pruebas rápido y declararlo).
- **Alternativa descartada**: declarar "menos de cinco minutos" sin medir.

## Resuelto: no quedan "NEEDS CLARIFICATION"
El enlace del video y la lectura de "dos páginas" eran los dos puntos abiertos; se resuelven en D7 y D5.
