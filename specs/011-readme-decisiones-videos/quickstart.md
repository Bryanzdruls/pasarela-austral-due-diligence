# Quickstart: validar el ticket #11 de punta a punta

## Requisitos
Python 3.12, `git` y la herramienta de dependencias del proyecto (`python -m uv`). La clave de acceso al modelo solo hace falta para el paso 5.

## 1. Los comprobadores y sus pruebas
```bash
python -m uv run pytest scripts/tests/test_verify_delivery.py scripts/tests/test_docs.py -q
```
Esperado: en verde. Cada condición prohibida del zip (archivo de entorno, credencial, entorno virtual, tamaño excesivo, sin historial, árbol distinto del último commit) falla con su causa.

## 2. Los documentos
```bash
python scripts/verify_docs.py
```
Esperado: `OK` en todo, con el estado del video `pendiente` hasta que la persona lo publique.

## 3. El zip
```bash
python scripts/verify_delivery.py --build
```
Esperado: construye `../pasarela-austral-due-diligence.zip` y lo verifica: historial incluido, sin dependencias, bastante por debajo de 50 MB, sin secretos ni credenciales, coincide con el último commit.

## 4. La copia limpia (SC-001): el README, cronometrado
```bash
git clone <repositorio> <directorio temporal>      # o descomprimir el zip
cd <directorio temporal>
python -m uv sync
python -m uv run pytest -q
python -m uv run python -m due_diligence.web      # y abrir la dirección que imprime
```
Esperado: todo en menos de cinco minutos. Se registra el tiempo de cada paso en `verification.md`.

## 5. La interfaz con el modelo real (ensayo del guion)
Con la clave en el entorno, recorrer los siete casos de `docs/VIDEO.md` en la interfaz y comprobar que cada uno muestra lo que el guion anuncia.

## 6. Antes de entregar
```bash
python scripts/verify_delivery.py --build --final
```
Falla mientras el enlace del video siga `PENDIENTE`. Pasa cuando la persona lo ha pegado en el README y se ha vuelto a generar el zip.
