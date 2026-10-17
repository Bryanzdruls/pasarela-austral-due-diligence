# Implementation Plan: README, DECISIONES.md, guion de video y zip de entrega

**Branch**: `011-readme-decisiones-videos` | **Date**: 2026-10-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/011-readme-decisiones-videos/spec.md`

## Summary

Cierra los entregables de documentación y de entrega del enunciado sin tocar el comportamiento del sistema: un `README.md` que un evaluador pueda seguir en menos de cinco minutos, un `DECISIONES.md` de dos páginas como máximo con las once necesidades del ecosistema, un guion del video de funcionamiento (`docs/VIDEO.md`) y dos comprobadores automáticos: `scripts/verify_delivery.py` (el zip de entrega no lleva secretos ni dependencias, lleva el historial y cabe en 50 MB) y `scripts/verify_docs.py` (las rutas citadas existen, la extensión se respeta, las once necesidades están y el enlace del video está en su estado correcto). Los comprobadores se prueban primero con casos prohibidos construidos en el momento; los documentos se escriben después y se miden de verdad (una copia limpia y un reloj).

El plan sigue la lección de #9: lo que garantiza un mínimo del enunciado se hace con una comprobación ejecutable, no con una promesa en un documento.

## Technical Context

**Language/Version**: Python 3.12; solo biblioteca estándar en `scripts/` (convención del proyecto).

**Primary Dependencies**: ninguna nueva. Los comprobadores usan `zipfile`, `subprocess` (para `git`), `re`, `json`, `argparse`, `tempfile`, `pathlib`. Reutilizan el patrón de `scripts/verify_ecosystem.py` (`Check`, salida `OK`/`FALLA`, `--json`, código 0/1).

**Storage**: archivos. El zip se escribe fuera del repositorio por defecto (carpeta superior) para que nunca se versione ni se incluya a sí mismo.

**Testing**: `pytest` en `scripts/tests/`; zips y repositorios sintéticos en directorios temporales; los valores con forma de credencial se **construyen en tiempo de ejecución** (convención del proyecto). Una prueba contra el repositorio real vigila los documentos.

**Target Platform**: Windows (Git Bash y PowerShell) y Linux/macOS para quien evalúe; sin dependencias del sistema salvo `git`.

**Project Type**: documentación y herramientas de verificación del repositorio (no es código del sistema).

**Performance Goals**: construir y verificar el zip en segundos (el historial pesa ~5 MB); el recorrido del README, en menos de cinco minutos.

**Constraints**: zip ≤ 50 MB (se usa el límite decimal de 50.000.000 bytes, el más estricto); ningún `.env` ni credencial (falta grave); datos ficticios; sin reescribir el historial; `DECISIONES.md` ≤ 2 páginas (medido como ≤ 1000 palabras).

**Scale/Scope**: 3 documentos, 2 scripts, 2 archivos de pruebas, 2 líneas nuevas en `.gitignore` (`dist/` y `*.zip`) y la actualización de `docs/TRAZABILIDAD.md`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumplimiento |
|---|---|
| I. Reglas de negocio garantizadas, no sugeridas | No se toca ninguna regla ni hook. El README declara lo abierto (reglas 4 y 5 parciales en lo que muestra la interfaz) sin presentarlo como completo. |
| II. Datos exclusivamente ficticios | Los documentos solo citan identificadores ficticios (`CO-XX-000N`); las pruebas construyen en tiempo de ejecución cualquier valor con forma de credencial; el comprobador del zip no repite nunca un valor encontrado. |
| III. Hooks para lo que debe cumplirse, instrucciones para lo que orienta | Lo grave (secretos y credenciales en el zip) lo hace cumplir un comprobador con código de salida y pruebas, no una frase del README. |
| IV. Spec primero | `spec.md`, este plan y `tasks.md` existen antes de escribir los scripts. |
| V. Agentes con contexto explícito | No aplica (no toca el sistema multi-agente). |
| VI. Pruebas junto al código | `scripts/tests/test_verify_delivery.py` y `test_docs.py`; primero se escriben y se ven fallar. |
| VII. Trazabilidad en GitHub | Ticket #11 en In Progress; el PR cierra el issue con `Closes #11`; la trazabilidad se actualiza. |
| VIII. Ecosistema de Claude Code primero | Ya completo (#9 y #10 fusionados). Se reutiliza `scripts/verify_ecosystem.py` y `/abrir-pr`. |

**Resultado**: sin violaciones. Complejidad adicional: ninguna que justificar.

## Project Structure

### Documentation (this feature)

```text
specs/011-readme-decisiones-videos/
├── plan.md              # Este archivo
├── research.md          # Decisiones D1 a D10 con alternativas descartadas
├── data-model.md        # Las entidades y sus reglas de validación
├── quickstart.md        # Cómo validar de punta a punta (incluida la copia limpia)
├── contracts/
│   ├── cli.md           # Contrato de scripts/verify_delivery.py y scripts/verify_docs.py
│   └── documentos.md    # Estructura exigida a README.md, DECISIONES.md y docs/VIDEO.md
├── checklists/requirements.md
└── tasks.md             # Lo genera /speckit-tasks
```

### Source Code (repository root)

```text
README.md                          # nuevo: la puerta de entrada
DECISIONES.md                      # nuevo: 11 necesidades, mecanismo, porqué, alternativa
docs/VIDEO.md                      # nuevo: guion del video de funcionamiento
scripts/
├── verify_delivery.py             # nuevo: construye y verifica el zip de entrega
├── verify_docs.py                 # nuevo: comprueba README, DECISIONES.md y VIDEO.md
└── tests/
    ├── test_verify_delivery.py    # nuevo: casos prohibidos sintéticos
    └── test_docs.py               # nuevo: lógica del comprobador y documentos reales
.gitignore                         # dos líneas: dist/ y *.zip (el zip nunca se versiona)
docs/TRAZABILIDAD.md               # D2, D3, D5, D6 y la nota de lo que queda en manos de la persona
specs/011-readme-decisiones-videos/verification.md   # medición de la copia limpia y mutaciones
```

**Structure Decision**: los comprobadores viven en `scripts/` junto a `verify_ecosystem.py` y siguen su forma; los documentos de cara al evaluador van en la raíz (`README.md`, `DECISIONES.md`, como pide el enunciado) y el guion en `docs/` junto a `CASOS.md` e `INTERFAZ.md`. No se crea ningún paquete nuevo.

## Complexity Tracking

Sin violaciones de la constitución que justificar.
