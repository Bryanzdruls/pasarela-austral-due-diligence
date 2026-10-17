# Pasarela Austral · Due diligence de comercios

## Qué es

Prueba técnica de Claude Code y el Agent SDK. Un sistema multi-agente investiga a un comercio antes de habilitarlo en una pasarela de pagos **ficticia**: un coordinador delega en cuatro subagentes (registro mercantil, listas restrictivas, noticias y riesgo de la categoría), que consumen un servidor MCP propio con datos locales, y entrega un informe con fuentes y una recomendación. Sabe cuándo la decisión le corresponde a un oficial de cumplimiento: las reglas de negocio 1 a 3 las hacen cumplir **hooks del Agent SDK**, no el prompt. Quien conversa con él es un analista interno, en una interfaz de chat.

Todos los datos son ficticios (`CO-XX-000N`, `FICT-000N`) y no hay ninguna credencial en el repositorio.

## Requisitos

- **Python 3.12** y **git**.
- La herramienta de dependencias `uv`. Si no está en el `PATH`, todos los comandos de este README funcionan igual con `python -m uv`.
- **Node** (opcional): solo lo necesitan algunas pruebas de la página del chat; sin Node se saltan y el resto pasa.
- **Una clave de acceso al modelo** (`ANTHROPIC_API_KEY`): solo para conversar con el sistema y para ejecutar los casos con el modelo real. Las pruebas **no** la necesitan.

## Cómo correrlo

```bash
git clone <URL del repositorio>      # o descomprimir el zip de entrega
cd pasarela-austral-due-diligence
python -m uv sync                    # instala las dependencias
```

Define la clave **como variable de entorno** de tu sesión, nunca en un archivo del repositorio:

```powershell
$env:ANTHROPIC_API_KEY = "<tu clave>"        # PowerShell
```

```bash
export ANTHROPIC_API_KEY="<tu clave>"        # Git Bash, macOS o Linux
```

Arranca la interfaz de chat y abre la dirección que imprime (por defecto `http://127.0.0.1:8000`):

```bash
python -m uv run python -m due_diligence.web
```

Si el puerto está ocupado, `--puerto 8001`. La interfaz escucha solo en tu máquina y no tiene autenticación. Escribe un mensaje del enunciado, por ejemplo: *«Necesito el due diligence de Tienda Verde SAS, identificador ficticio CO-TV-0001. Quieren procesar ventas en línea de suplementos dietarios y estiman unos $80.000.000 mensuales. ¿Lo podemos habilitar esta semana?»*. Verás qué delega el coordinador, qué responde cada fuente, qué llamada bloquea un hook y qué se registra o se escala. Detalle en `docs/INTERFAZ.md`.

Otras formas de arrancarlo:

```bash
python -m uv run python -m due_diligence    # consola, sin navegador
python -m uv run python -m mcp_server       # el servidor MCP de fuentes por stdio
```

## Pruebas

```bash
python -m uv run pytest -q
```

Son más de 1.500 pruebas, sin modelo y sin clave: usan un cliente falso, los datos ficticios reales y los hooks de producción. Con `python -m uv run ruff check .` se comprueba el estilo.

## Los siete casos

Los siete casos obligatorios del enunciado están en `docs/CASOS.md`, con su mensaje, sus datos y el resultado exigido. Se pueden recorrer de tres formas:

- **En la interfaz de chat**, escribiendo el mensaje de cada caso (lo que verás en cada uno está en `docs/INTERFAZ.md`).
- **Sin modelo**, de extremo a extremo y en segundos: `python -m uv run pytest due_diligence/tests/test_casos_obligatorios.py -q`.
- **Con el modelo real**: `python -m uv run python scripts/run_casos.py` (o `--caso N` para uno solo). Necesita `ANTHROPIC_API_KEY` y decide cada caso por lo que el sistema hizo, no por el texto de la respuesta.

## Enlaces

- **GitHub Project** (el backlog, con su historial): https://github.com/users/Bryanzdruls/projects/4
- **Video de funcionamiento**: PENDIENTE

## Mapa de piezas

| Qué | Dónde |
|---|---|
| Coordinador, subagentes, hooks de reglas del Agent SDK | `due_diligence/` |
| Interfaz de chat | `due_diligence/web/` y `docs/INTERFAZ.md` |
| Servidor MCP de fuentes y sus datos ficticios | `mcp_server/` (datos en `mcp_server/data/`) |
| Ecosistema de Claude Code: memoria, reglas, subagentes, skills, hooks, comando, MCP y plugin | `CLAUDE.md`, `.claude/`, `.mcp.json`, `plugins/pasarela-revision/` |
| Por qué cada pieza está donde está | `docs/ECOSISTEMA.md` y `DECISIONES.md` |
| Constitución y especificaciones de cada ticket (Spec Kit) | `.specify/memory/constitution.md` y `specs/` |
| Estado frente al enunciado, requisito por requisito | `docs/TRAZABILIDAD.md` |
| Comprobadores de la entrega | `scripts/verify_ecosystem.py`, `scripts/verify_docs.py`, `scripts/verify_delivery.py` |

Cada ticket se especificó, planificó y descompuso en tareas antes de escribir código, y se revisó con un revisor de código y uno de cumplimiento independientes; el historial de issues, pull requests y comentarios de avance está en el GitHub Project.

## Límites conocidos

- Las reglas de negocio 1 a 3 están garantizadas por hooks, pero las **reglas 4 y 5 son parciales en lo que muestra la interfaz**: el hallazgo del registro avisa de fechas de constitución distintas sin mostrar las dos, y la tarjeta «Falló» y el «Sin cubrir» salen de lo que declara el modelo. Los hooks del informe sí los hacen cumplir antes de registrarlo.
- Con el modelo real, ningún caso llegó a ejercer una **denegación de hook** porque el modelo respeta el flujo; las denegaciones se demuestran con pruebas y con un prompt de prueba, no con la conducta espontánea del modelo. El modelo varía entre corridas.
- La interfaz es una demostración local: sin autenticación, sin persistencia (reiniciar el proceso pierde las conversaciones) y comprobada en el navegador integrado de Claude Code, no en Chrome, Firefox ni Safari.
- Los hooks de Claude Code reducen el riesgo, no lo eliminan: sus límites están en `docs/ECOSISTEMA.md`.
