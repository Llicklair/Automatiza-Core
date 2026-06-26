# Inbox /forja (run-2, híbrido) — header injection en Content-Disposition (2026-06-26, seguridad)

Hallazgo SISTÉMICO del escaneo de hermanas: ~20 rutas construyen `Content-Disposition: ...filename="{x}"`
con `x` derivado de datos de usuario/entidad SIN sanear → header injection (`\r\n`/`"` en el nombre inyecta
cabeceras). FIX parcial hecho → PR #56: helper `safe_content_disposition_filename` (en `core/security.py`)
+ aplicado a **contrato** (`_contracts.py`) y **nómina** (`_payroll.py`, 2 sitios: descarga + persistencia),
con test. El helper ya está listo para reutilizar.

## ⚠️ Media — barrido completo pendiente (PR DEDICADO, blast radius ancho)
Aplicar `from app.core.security import safe_content_disposition_filename` a TODOS los sitios que derivan el
filename de datos de usuario. Lista del escaneo (revisar cuáles llevan dato de usuario vs literal/numérico
seguro):
- `routes/accounting.py:258,275,292` (`fname`)
- `routes/admin.py:113`, `routes/client_portal.py:240` (`file_name` — fichero subido por usuario)
- `routes/documents.py:521` (contrato — ya cubierto en servicio) y `:325` (`safe_filename` — verificar si ya
  está saneado)
- `routes/hr_documents.py:99`, `routes/hr_employees.py:145,191,214,237`, `routes/hr_expenses.py:170`,
  `routes/hr_time.py:64`
- `routes/invoices.py:419,444` (`file_name`)
- Seguros (NO tocar): `albaranes.py:122` (`albaran-{number}`), `documents.py:265` (literal),
  `aeat_presentation.py:323` (verificar).
Por qué PR dedicado: tocar ~15 rutas = blast radius ancho → revisión humana + suite COMPLETA (varios tests
afirman cabeceras). El kit veta auto-fix masivo a ciegas.

## Del flujo de contratos (mismo turno)
- **#1 [media→baja]** `documents/_contracts.py:177` `DocxTemplate(tpl_doc.file_path)` sin validar que el path
  esté bajo `TEMPLATES_DIR`. Mitigado por tenant-scope en BD (no es fuga cross-tenant); defensa en
  profundidad si el valor en BD ya fuera malo. Fix opcional: `Path(file_path).resolve().is_relative_to(BASE)`.
- **#4 [media, delicado]** `crm/queries.py:99` `"salario_base": str(employee.base_salary or "")` → un contrato
  legal con `"1500.0"` en vez de `"1.500,00 €"`. Correctitud legal real, pero el formato depende de
  locale/moneda del tenant → revisión humana, no auto-fix.
- **#2 [baja]** `entity_type: str` sin `Literal` en la ruta (ya validado aguas abajo → 400). Higiene.
