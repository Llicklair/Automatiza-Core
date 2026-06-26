# Inbox /forja v2 — procesamiento de documentos (2026-06-26, lente errores+recursos)

Flujo: subida/extracción/parseo de ficheros. FIX #4 (validar extensión de entradas ZIP en `upload_bulk` +
test de regresión) ya hecho → PR #52, 53 tests verde. El finder auto-descartó su #2 (el `finally` de
OpenDataLoader limpia bien). Quedan dos objetivos menores:

## Media — tempfile puede filtrarse si falla la escritura (Windows)
1. **`services/pdf/parser.py:186-194`** — patrón
   `tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False); tmp.write(...); tmp.close(); ...; finally: os.unlink(tmp.name)`.
   Si `tmp.write()`/`tmp.close()` lanzan (disco lleno, E/S) antes del `close`, el handle queda abierto y en
   Windows `os.unlink` del `finally` falla silenciosamente → el .pdf temporal queda en disco. Fix objetivo:
   `with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp: tmp.write(file_bytes)` (cierra el
   handle al salir del `with`) y dejar el `os.unlink(tmp.name)` en el `finally` externo. Bajo riesgo; toca
   ruta de parseo PDF → verificar que no rompe el flujo OpenDataLoader/pypdf.

## Baja — `_update_doc_status` sin filtro de tenant (mitigado por RLS)
3. **`agents/documents/tools.py:326-341`** — `select(TenantDocument).where(TenantDocument.id == UUID(document_id))`
   sin `tenant_id`. La función abre su propia `AsyncSessionLocal()` y confía en que RLS (fail-closed) ya está
   activo, así que NO es explotable vía HTTP; pero es inconsistente con el resto de selects del fichero que sí
   filtran. Fix objetivo (defensa en profundidad/consistencia): añadir
   `TenantDocument.tenant_id == UUID(tenant_id)` al where (`tenant_id` ya está en el scope). Severidad real
   baja (no inflar — RLS cubre el caso).
