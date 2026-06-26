# Inbox /forja v2 — exportación CSV/Excel (2026-06-26, lente seguridad+correctitud)

Flujo: export a Excel/CSV. FIX #1+#4 (saneado anti-inyección de fórmulas en writer central + horarios,
helper `sanitize_spreadsheet_cell` en `core/security.py`, con test e2e) ya hecho → PR #52, 74+7 tests verde.
Quedan dos objetivos:

## Media — header injection en Content-Disposition (PDF nómina)
2. **`services/hr/_payroll.py:349-351` + `routes/hr_payrolls.py:166`** — el nombre del empleado se incrusta
   en el filename del header HTTP solo reemplazando espacios:
   `emp_name = payroll.employee.name.replace(" ", "_")` → `Content-Disposition: attachment; filename="Nomina_{emp_name}_{period}.pdf"`.
   Un empleado llamado `Juan"\r\nContent-Type: text/html` rompe el header (header splitting / inyección de
   cabeceras). El campo `name` lo escribe RRHH/agente sin validar caracteres de control. Fix objetivo:
   `import re; emp_name = re.sub(r"[^\w\-.]", "_", payroll.employee.name) if payroll.employee else "empleado"`.
   (Revisar si hay OTROS Content-Disposition con nombre de usuario sin sanear — mismo patrón en exports de
   facturas/albaranes si los hubiera.)

## Baja-media — `_fetch_employees` sin `.limit()` (DoS de memoria)
3. **`agents/excel/_fetchers.py:76-80` `_fetch_employees`** — único fetcher SIN `.limit(500)` (el resto sí lo
   tienen). Un tenant con muchos empleados (migración masiva / seed demo) vuelca toda la tabla a RAM y a un
   DataFrame en un solo fetch. Fix objetivo: añadir `.limit(500)` como los demás fetchers. (Relacionado con
   el patrón de cotas que ya se aplicó en `parse_tabular_file`.)
