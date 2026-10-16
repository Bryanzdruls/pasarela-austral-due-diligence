---
paths:
  - "mcp_server/data/**"
---

# Datos ficticios del servidor de fuentes

- Todo dato es **inventado**; ninguno corresponde a una persona, empresa, noticia o lista reales.
- Identificadores de comercio con la forma `CO-XX-000N` (`CO-TV-0001`); personas `PE-000N`; documentos y NIT con la forma `FICT-000N`. Nunca un número que parezca un documento, un NIT o una tarjeta.
- Los nombres de fuente terminan en `_ficticio` o `_ficticia` (`noticias_ficticias`).
- Las fechas van en formato ISO (`2026-10-16`).
- Los casos de prueba del enunciado deben seguir siendo reproducibles con estos datos: alto riesgo, bajo riesgo sin hallazgos, representante en listas, nombres casi idénticos y fechas de constitución distintas entre fuentes.
- Un hook bloquea escribir contenido con forma de dato real; si te bloquea, cambia el valor por un identificador ficticio, no esquives el hook.
