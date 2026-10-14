---
description: "Tareas del servidor de fuentes ficticias de la pasarela"
---

# Tasks: Servidor de fuentes ficticias de la pasarela

**Input**: `specs/001-servidor-mcp-datos-ficticios/` (plan.md, spec.md, research.md, data-model.md, contracts/tools.md, quickstart.md)

**Prerequisites**: plan.md, spec.md

**Tests**: Incluidos. La constitución (principio VI) exige pruebas junto al código y el contrato de descripciones se verifica con tests.

**Organization**: Tareas agrupadas por historia de usuario del spec.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencia pendiente)
- **[Story]**: US1 registro · US2 listas/noticias/riesgo · US3 informe y escalamiento · US4 fallas

## Phase 1: Setup

- [x] T001 Verificar que `uv` esté en el PATH (si no, usar `python -m uv`); crear `pyproject.toml` en la raíz con Python 3.12, dependencias `mcp`, `pydantic`, y `pytest`, `ruff`, y configuración de pytest (`testpaths = ["mcp_server"]`)
- [x] T002 [P] Crear la estructura de paquetes vacía: `mcp_server/__init__.py`, `mcp_server/tools/__init__.py`, `mcp_server/tests/__init__.py`, `mcp_server/tools/tests/__init__.py`
- [x] T003 [P] Añadir `data/runtime/` al `.gitignore` y crear `.env.example` sin valores (`PASARELA_FAULTS=`, `PASARELA_RUNTIME_DIR=`)

## Phase 2: Foundational (bloquea todas las historias)

- [x] T004 Implementar `mcp_server/envelope.py`: `ok(content, source)` → `{ok:true, content, metadata:{source, fetched_at}}` y `error(source, error_code, retryable, partial)` → `{ok:false, source, error_code, retryable, partial}`; `error_code` solo `source_unavailable` o `invalid_input`
- [x] T005 [P] Test del sobre en `mcp_server/tests/test_envelope.py`: éxito separa contenido de metadatos; error trae `source`, `error_code`, `retryable`, `partial`; rechaza un `error_code` no permitido
- [x] T006 Implementar `mcp_server/store.py`: carga de JSON de `mcp_server/data/`, normalización de texto (minúsculas, sin tildes, sin puntuación, sufijo SAS/S.A.S. ignorado) y regla de coincidencia: identificador exacto, o consulta normalizada contenida en la razón social normalizada (research D3) y escritura de registros en `PASARELA_RUNTIME_DIR` (por defecto `data/runtime/`)
- [x] T007 [P] Test de `store.py` en `mcp_server/tests/test_store.py`: normalización ("Cafetería Aurora S.A.S." == "cafeteria aurora sas"), texto vacío rechazado, escritura en un directorio temporal
- [x] T008 Crear `mcp_server/server.py` con la instancia `FastMCP("pasarela-fuentes")` y `mcp_server/__main__.py` que la ejecuta por stdio

**Checkpoint**: sobre, almacén y servidor listos; se pueden construir las historias.

## Phase 3: User Story 1 — Registro mercantil (P1) 🎯 MVP

**Goal**: identificar un comercio por nombre o id; varias coincidencias se devuelven todas sin elegir.

**Independent Test**: `CO-TV-0001` → 1 coincidencia; "Cafetería Aurora" → 2 con `ambiguous=true`; nombre inexistente → 0 coincidencias (no es error).

- [x] T009 [P] [US1] Crear `mcp_server/data/personas.json` con representantes ficticios (`id` `PE-000N`, `nombre` inventado, `documento` `FICT-000N`), incluida la persona que luego estará en listas
- [x] T010 [P] [US1] Crear `mcp_server/data/comercios.json` con los 6 comercios de `data-model.md` (`CO-TV-0001`, `CO-LB-0002`, `CO-DA-0003`, `CO-CA-0004`, `CO-CA-0005`, `CO-FH-0006`); campos: `id` `CO-XX-000N`, `razon_social`, `nit` `FICT-000N`, `estado` ∈ `activo` | `cancelado` | `suspendido`, `categoria`, `volumen_mensual_estimado` (int, pesos; CO-TV-0001 = 80000000), `representante_legal_id`, `fuentes_registro` `[{source, fecha_constitucion}]`; CO-FH-0006 con dos fuentes de fechas distintas
- [x] T011 [US1] Tests en `mcp_server/tools/tests/test_registro.py`: una coincidencia por id; dos coincidencias con `ambiguous=true` para "Cafetería Aurora"; cero coincidencias; `CO-FH-0006` devuelve ambas fechas con origen y `conflicts=["fecha_constitucion"]`; texto vacío → `invalid_input`; la descripción contiene "NO elijas" y "identificador" (escribirlos primero y ver que fallan)
- [x] T012 [US1] Implementar `mcp_server/tools/registro.py` con `consultar_registro_mercantil(consulta)` según `contracts/tools.md` (`match_count`, `ambiguous`, `matches[...]`, `conflicts`) y la descripción literal del contrato
- [x] T013 [US1] Registrar la herramienta en `mcp_server/server.py`

**Checkpoint**: US1 funciona y se prueba sola.

## Phase 4: User Story 2 — Listas, noticias y riesgo (P1)

**Goal**: los tres frentes restantes de la investigación, con descripciones que evitan confusiones.

**Independent Test**: persona sembrada en listas → `match=true`; noticia que menciona a un comercio → mención, nunca coincidencia en listas; las 4 categorías de alto riesgo → `alto`; categoría desconocida → `sin_clasificar`.

- [x] T014 [P] [US2] Crear `mcp_server/data/listas_restrictivas.json` (`id`, `tipo` ∈ `persona` | `comercio`, `referencia`, `nombre_lista` ficticia, `fecha_inclusion`) con el representante legal de `CO-DA-0003`
- [x] T015 [P] [US2] Crear `mcp_server/data/noticias.json` (`id`, `titular`, `fecha`, `fuente` terminada en `_ficticia`, `menciona`, `resumen`): una noticia adversa sobre `CO-TV-0001` y una que menciona a una persona que NO está en listas
- [x] T016 [P] [US2] Crear `mcp_server/data/categorias.json` (`nombre`, `riesgo` ∈ `alto` | `bajo`): alto = apuestas, criptoactivos, suplementos dietarios, venta de medicamentos; bajo = librería, cafetería, ferretería
- [x] T017 [US2] Tests en `mcp_server/tools/tests/test_listas.py`, `test_noticias.py` y `test_riesgo.py`: coincidencia de persona; comercio sin coincidencia; mención de noticia no aparece en listas; 4 categorías en `alto`; desconocida → `sin_clasificar`; las descripciones: la de noticias contiene "NO es una coincidencia en listas" y la de listas indica que se usa con comercio ya identificado; texto vacío → `invalid_input` también en listas y noticias
- [x] T018 [P] [US2] Implementar `mcp_server/tools/listas.py` con `consultar_listas_restrictivas(tipo, referencia)`
- [x] T019 [P] [US2] Implementar `mcp_server/tools/noticias.py` con `buscar_noticias(consulta)`
- [x] T020 [P] [US2] Implementar `mcp_server/tools/riesgo.py` con `consultar_riesgo_categoria(categoria)`
- [x] T021 [US2] Registrar las tres herramientas en `mcp_server/server.py`

**Checkpoint**: US1 y US2 operan; ya se cubren los casos 1-4 y 6 del quickstart.

## Phase 5: User Story 3 — Informe y escalamiento (P2)

**Goal**: guardar el informe o el caso escalado; rechazar escalamientos incompletos.

**Independent Test**: registrar informe → `informe_id` y archivo; escalar completo → `escalamiento_id`; sin `causa` → `invalid_input` con `campos_faltantes`.

- [x] T022 [US3] Tests en `mcp_server/tools/tests/test_informes.py` (directorio temporal vía `PASARELA_RUNTIME_DIR`): informe guardado tal cual con id `INF-0001`; dos informes del mismo comercio → ids distintos; escalamiento completo guardado con `ESC-0001`; falta `causa` o `accion_recomendada` → `invalid_input` con `partial.campos_faltantes`; FR-013: `registrar_informe` acepta la recomendación "habilitar" aunque el comercio tenga coincidencia en listas (el servidor solo guarda, no decide)
- [x] T023 [US3] Implementar `mcp_server/tools/informes.py` con `registrar_informe(...)` y `escalar_a_cumplimiento(...)`; validar con `pydantic` los campos obligatorios `comercio`, `hallazgos` (por frente con fuente), `cobertura`, `causa`, `accion_recomendada`
- [x] T024 [US3] Registrar ambas herramientas en `mcp_server/server.py`

## Phase 6: User Story 4 — Inyección de fallas (P2)

**Goal**: simular que una fuente falla para probar la cobertura incompleta.

**Independent Test**: con `PASARELA_FAULTS=noticias`, `buscar_noticias` devuelve error estructurado y las demás herramientas responden normal.

- [x] T025 [US4] Tests en `mcp_server/tests/test_faults.py`: con `noticias` en `PASARELA_FAULTS` falla solo noticias (`source_unavailable`, `retryable=true`); `noticias:no_reintentable` → `retryable=false`; sin variable todo responde; variable leída en cada llamada
- [x] T026 [US4] Implementar `mcp_server/faults.py` (lee `PASARELA_FAULTS` en cada llamada; fuentes `registro`, `listas`, `noticias`, `riesgo`)
- [x] T027 [US4] Aplicar el guard de fallas al inicio de cada herramienta de consulta en `mcp_server/tools/registro.py`, `listas.py`, `noticias.py` y `riesgo.py`

## Phase 7: Polish y garantías transversales

- [x] T028 [P] Test de datos ficticios en `mcp_server/tests/test_datos_ficticios.py`: recorre `mcp_server/data/*.json`; ids con formato `CO-XX-000N`, documentos/NIT `FICT-000N`, fuentes terminadas en `_ficticio`/`_ficticia`; falla ante cualquier valor con forma de documento, NIT o tarjeta numéricos
- [x] T029 [P] Test del servidor en `mcp_server/tests/test_server.py`: exactamente 6 herramientas registradas con los nombres del contrato (FR-001); cada herramienta, invocada con una entrada válida, devuelve el sobre con `content` y `metadata.source`/`fetched_at` separados (FR-008, SC-002)
- [x] T030 Ejecutar `uv run pytest mcp_server` y `uv run ruff check . && uv run ruff format --check .`; todo en verde
- [x] T031 Recorrer los siete escenarios de `quickstart.md` contra el servidor y anotar el resultado; ajustar el quickstart si algo difiere
- [x] T032 Comentar en el issue #1 lo especificado, lo decidido y lo pendiente (el caso "listas sin identificación unívoca" queda para el ticket #3)

## Dependencies & Execution Order

- Setup (T001-T003) → Foundational (T004-T008) → historias.
- US1 y US2 son independientes entre sí tras la fase 2; ambas P1.
- US3 depende solo de la fase 2. US4 modifica las herramientas de US1 y US2, así que va después de ellas.
- Polish al final.
- Dentro de cada historia: datos → tests (deben fallar) → implementación → registro en `server.py`. T013, T021 y T024 tocan `server.py`: no en paralelo.

## Parallel Examples

- Fase 3: T009 y T010 juntas. Fase 4: T014, T015 y T016 juntas; luego T018, T019 y T020 juntas.
- Fase 7: T028 y T029 juntas.

## Implementation Strategy

- **MVP**: Setup + Foundational + US1 (T001-T013): ya se puede consultar el registro y probar ambigüedad y conflicto de fechas.
- Siguiente: US2 (completa los frentes), US3 (cierre del ciclo), US4 (falla de noticias).
- Cada historia se valida con su "Independent Test" antes de pasar a la siguiente.
