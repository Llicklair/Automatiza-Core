# Inbox /forja — SEGURIDAD en services/documents (2026-06-25, barrido #5) ⚠️ PRIORIDAD ALTA

El loop arregló el filtro de tenant de `semantic_search` (#6, PR #50). El resto es un
**cluster de seguridad** que NO auto-arreglé: el fix correcto toca varios sitios y depende
de cómo se almacena `file_path` (patchear a ciegas puede romper descargas legítimas). Merece
una pasada de seguridad humana y enfocada.

## Path traversal (×3) — [alta]
El único saneamiento es `os.normpath()`, que NO contiene rutas dentro de `UPLOAD_DIR`.
1. **`service.py:~307` `export_all`**: si `doc.file_path` (de BD) es `/etc/passwd` o cualquier
   ruta del sistema, se empaqueta en el ZIP de `/documents/export` → exfiltración.
2. **`service.py:~384-391` `_resolve_file_path`/`prepare_download`**: sirve `doc.file_path` por
   `FileResponse`; el fallback usa `doc.file_name` con posibles `../` → lectura fuera de dir.
3. **`service.py:~540` `update_content` fallback**: escribe en `UPLOAD_DIR/doc.file_name` sin
   sanear → un `file_name` con `../` sobreescribe ficheros del servidor.
**Fix recomendado (unificado)**: helper que resuelva con `os.path.realpath` y exija
`startswith(realpath(UPLOAD_DIR)+os.sep)`; aplicarlo en los 3 sitios. ⚠️ Explotabilidad real
depende de si `file_path`/`file_name` son controlables por el usuario (verifica `save_file_to_disk`):
si siempre se fijan server-side bajo UPLOAD_DIR, es defensa en profundidad; si no, es P0.

## ZIP bomb — [alta]
4. **`_file_ops.py:~105-125` `extract_zip_entries`**: descomprime sin límite de tamaño
   expandido ni nº de entradas. `MAX_FILE_SIZE` solo mira el ZIP comprimido. Un 42.zip agota
   la RAM. Fix: acumulador de bytes descomprimidos con tope (p.ej. 200 MB) → `ValueError`.

## Validación ausente — [media]
5. ✅ RESUELTO (PR #51, 527cc48): **`scan_single` saltaba `validate_upload`**. Ahora valida
   extensión/tamaño con `validate_upload` igual que `upload_single` (verificado: los tipos de scan
   ⊆ ALLOWED_EXTENSIONS, no rompe casos legítimos). El endpoint /scan rechaza .exe/.sh/.php y >50MB.
