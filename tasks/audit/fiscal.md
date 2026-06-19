# Auditoría de corrección fiscal (AEAT + VeriFactu)

Fecha: 2026-06-19 · HEAD `2a2075d` · rama `chore/cleanup-stale-reports`
Auditor: revisión automatizada (conservadora). Marcas: 🔴 alto · 🟠 medio · 🟢 ok · ❓ requiere verificación humana.

---

## Resumen ejecutivo

| Área | Estado |
|---|---|
| Gating VeriFactu (no envío accidental) | 🟢 SÓLIDO |
| Invariante BORRADOR en PDFs | 🟢 se mantiene en `pdf_reports/` |
| Acuse dry-run con CSV ficticio (vía antigua) | 🟠 riesgo de presentar CSV falso como real |
| Modo de redondeo (ROUND_HALF_UP) | 🟠 inconsistente: casillas usan HALF_EVEN |
| Tipo IVA 5% (y exentos/0%) no mapeados en 303 | 🔴/❓ posible infradeclaración |
| Retención a profesionales en 111 | 🔴 diferida (TODO v1.1) — infradeclara si aplica |
| Cadena hash VeriFactu | 🟢 correcta, validada contra vector AEAT |
| float() en dinero | 🟠 solo en reports/display, no en cálculo de casillas |

---

## 1. Corrección de cálculo por modelo

### 303 IVA — `casillas_303.py`
- 🟢 Tipos 4/10/21 con cuota desde `fiscal.py` (que sí usa ROUND_HALF_UP). Totales 27/45/46/64/66/69/71 encadenados correctamente. Intra (10/11/36/37) e ISP (12/13) y recargo (16-24) bien estructurados.
- 🔴/❓ **Tipo 5% (y 0%/exento) se pierden.** L101-113: `collected_by_rate.get(4.0/10.0/21.0)`. Una fila con `rate=5.0` (tipo temporal 2023-2024 energía/alimentos) NO se asigna a ninguna casilla 01-09 y, como el total devengado (27) suma solo cuotas 03/06/09/11/13/18/21/24, **su cuota desaparece del devengado** → IVA repercutido infradeclarado. Igual para tipos no contemplados. NEEDS HUMAN VERIFICATION de si `fiscal.py` puede emitir filas a 5%/0%; si puede, es 🔴.
- 🟠 Casillas editables (28/30/31/67) por defecto a 0: la base 28 mete TODO lo soportado (incluye bienes de inversión salvo ajuste manual). Documentado con `nota`, aceptable como borrador.
- 🟢 Signo del resultado: `expediente_303.py:124-130` clasifica >0 ingresar / <0 compensar / =0 cero. Correcto.

### 130 IRPF — `casillas_130.py`
- 🟢 c03 = c01−c02; c04 = 20% de c03 si positivo (tipo correcto estimación directa); c12 clamp a 0 si negativo (correcto: el negativo va a casilla 15 del trimestre siguiente, no se arrastra como negativo en 12). c19 puede ser negativo (correcto).
- 🟠 c04 = `_round2(c03 * Decimal("0.20"))` usa quantize **sin ROUND_HALF_UP** (ver §4).

### 111 — `modelos_aeat.py` (~L228) y `casillas_111.py`
- 🔴 **Retenciones a profesionales (Art. 95 LIRPF, 15%/7%) NO se computan**: requieren `Invoice.retencion_irpf`, campo inexistente; diferido a v1.1. El 111 solo suma retenciones de nóminas (`Payroll.irpf`). Un cliente que pague a profesionales con retención **infradeclarará el 111**. Es un diferimiento documentado, pero de alto impacto si el cliente tiene ese caso. Debe bloquearse/avisarse en UI.

### 115 / 190 / 347 / 390 — `casillas_115/190/347/390.py`
- 🟢 Sumas simples de bases/retenciones ya calculadas aguas arriba; sin tipos hardcodeados peligrosos. 190 toma `total_retencion_practicada` o suma perceptores (consistente). 390 = resumen anual, espejo del 303.

### 100 / 200
- ❓ No auditados en profundidad (IRPF/IS anuales, alta complejidad). Tienen tests. NEEDS HUMAN VERIFICATION antes de confiar en producción.

### 131 (módulos)
- ❓ No implementado (solo 130 estimación directa). Si se ofrece a clientes en módulos, falta.

---

## 2. VeriFactu — envío real (commit 2a2075d)

🟢 **Gating correcto y defensivo:**
- `verifactu_mode.py`: `DEFAULT_MODE = "no_remission"`. Sin fila → no_remission. `should_remit` solo True si `voluntary`.
- `verifactu_submit.py`: `get_submitter` devuelve `NoRemissionSubmitter` (no-op) salvo modo voluntary. `PreproduccionSubmitter.submit` con `confirmed=False` (default) → `dry_run`, **NO hay POST** (L263-268). Sin certificado → `CertificateError`. Firma *stub* (sin libxmlsec1) → `VerifactuSubmitError`, **aborta sin enviar** (L278-283).
- `VerifactuAck.csv` solo se rellena en `parse_acuse` desde respuesta real (`dry_run=False`). No se finge CSV. 🟢 Invariante respetado en esta vía.
- Endpoint `produccion` no está en `VERIFACTU_ENDPOINTS` (solo preproducción / POR CONFIRMAR) → no puede golpear producción por accidente. 🟢

🟢 **Firma XAdES** (`aeat/xades_signer.py`): sin libs → stub con `<UnsignedDraft>` y `signed=False`; nunca se presenta como válido. Camino real usa signxml `enveloped` rsa-sha256/sha256. (`billing/xades_signer.py` es firma FacturaE 3.2.2 separada, manual c14n+sha256, coherente.)

🟢 **mTLS** (`HttpxVerifactuTransport`): `ssl.create_default_context()` (verifica cert servidor) + `load_cert_chain` desde PEM temporal `mkstemp` (0600) borrado tras cargar. HTTP≥400 → error, no parsea acuse falso.

🟢 **Cadena hash** (`verifactu_chain.py`): payload canónico con orden de campos AEAT, `Huella=huella_anterior`, SHA-256 hex MAYÚSCULAS (`compute_huella`), validado contra vector oficial AEAT en tests. Orden por enlace hash (no `created_at`). `pg_advisory_xact_lock` por tenant evita huella_anterior duplicada. `verify_chain_integrity` recomputa y valida enlaces. Idempotente por `invoice_id`.

🟠 NEEDS HUMAN VERIFICATION: el sobre SOAP, endpoint exacto y perfil XAdES de VeriFactu están marcados "POR CONFIRMAR" — no verificables sin certificado + preproducción. No usar en producción hasta validar contra AEAT.

---

## 3. Invariante BORRADOR / no falsificar justificante

🟢 **PDFs de modelos** (`pdf_reports/_aeat_layout.py` `_draft_badge`, `_fiscal_modelos.py`): banda "BORRADOR — NO VÁLIDO PARA PRESENTACIÓN ANTE LA AEAT", disclaimer "No sustituye la presentación oficial". Docstrings explícitos: "NO genera número de justificante, CSV ni código de barras: solo nacen al presentar". No se encontró PDF417/CSV/justificante fabricado en los generadores PDF.

🟠 **HALLAZGO — vía antigua `presentation_service.py` + `sede_client.py`:**
- `sede_client.submit_signed_xml(dry_run=True)` genera `fake_csv = uuid4().hex[:16].upper()` y lo devuelve como `csv` (L121-130).
- `presentation_service.submit_presentation` con `dry_run=True` marca status `accepted` y guarda ese CSV ficticio en `p.csv_justificante` (L181-184).
- `build_acuse_text` (L206-222) imprime "ACUSE DE RECIBO — PRESENTACIÓN ELECTRÓNICA AEAT … CSV (justificante): {csv} … Verificable en sede.agenciatributaria.gob.es" **sin mencionar dry-run ni BORRADOR**.
- Riesgo: un acuse de dry-run presenta un CSV inventado como justificante verificable. Aunque `SubmissionResult.dry_run=True` existe, `build_acuse_text` lo ignora. **Recomendación:** que `build_acuse_text` y el almacenamiento marquen explícitamente "SIMULACIÓN / dry-run — CSV no válido", o no rellenar `csv_justificante` en dry-run. Severidad 🟠 (línea roja del proyecto).

---

## 4. Modo de redondeo (ROUND_HALF_UP)

🟠 **Inconsistencia de redondeo:**
- `_casilla.py:16`, `casillas_130.py:63`, `casillas_303.py:87` hacen `Decimal(str(x)).quantize(Decimal("0.01"))` **sin `rounding=ROUND_HALF_UP`** → usan el default de Python `ROUND_HALF_EVEN` (redondeo bancario). AEAT exige HALF_UP.
- En contraste, `reports/fiscal.py:37` y `billing/queries.py:42` SÍ usan `ROUND_HALF_UP`.
- Impacto real: las casillas reciben importes ya redondeados a 2dp por `fiscal.py` (HALF_UP), por lo que el re-quantize suele ser no-op. PERO `casillas_130.py:78` (`c04 = c03 * 0.20`) y cualquier producto/suma que aterrice en media unidad de céntimo (x.xx5) redondeará distinto (p.ej. 0.125 → 0.12 en vez de 0.13). **Recomendación:** unificar todos los `_round2`/`round2` con `rounding=ROUND_HALF_UP`. Bajo riesgo de magnitud pero corrección debida.

---

## 5. float() en aritmética monetaria

- 🟢 Cálculo de casillas: usa `Decimal` íntegramente. Los `float(self.valor)` en `to_dict`/XML (`_casilla.py:32`, `casillas_303.py:80`, `modelo_303_xml.py:56` `f"{float(c.valor):.2f}"`) son **solo serialización de un Decimal ya a 2dp** → seguro.
- 🟠 `reports/aggregation.py`, `cashflow.py`, `delinquency.py`, `expediente_303.py:121-123` suman con `float()`. Son dashboards/resúmenes informativos, **no** las casillas presentables. Riesgo bajo, pero idealmente migrar a Decimal para coherencia.

---

## 6. Casos límite

- 🟢 130: rendimiento negativo → c04=0, c12 clamp a 0, c19 puede ser negativo. Correcto.
- 🟢 303: resultado negativo → signo "compensar"; cero → "cero".
- 🟢 111: `quarter` validado ∈{1,2,3,4}; límites de trimestre con `monthrange` (último día correcto).
- ❓ Año bisiesto / periodos a caballo: `monthrange` lo cubre; no auditado para ejercicios partidos.
- 🟠 Recargo equivalencia: solo 0,5 / 1,4 / 5,2% (los generales). Faltan tipos especiales (p.ej. tabaco 1,75%); aceptable para mayoría pymes pero anótese.

---

## Acciones recomendadas (prioridad)

1. 🔴 Verificar/corregir mapeo de tipos IVA 5%/0%/exento en `casillas_303.py` — evitar pérdida de cuota devengada.
2. 🔴 Bloquear/avisar en 111 si el cliente tiene retenciones a profesionales (campo `retencion_irpf` ausente).
3. 🟠 `presentation_service.build_acuse_text` / `sede_client` dry-run: no presentar CSV ficticio como justificante sin marca de simulación.
4. 🟠 Unificar redondeo a `ROUND_HALF_UP` en `_casilla.round2`, `casillas_130._round2`, `casillas_303._round2`.
5. ❓ Revisión humana de 100/200 y del sobre SOAP/endpoint VeriFactu antes de producción.
