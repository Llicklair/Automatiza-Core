# Estado — Declaración responsable / conformidad VeriFactu

_Última actualización: 2026-07-21 (tarde). **Auditado adversarialmente contra el
código** (workflow de 10 verificadores + síntesis, master `60a73852`). Esta
versión CORRIGE la anterior, que afirmaba que "solo quedaba remisión": el cotejo
encontró 17 bloqueantes de código. La lista de abajo es la verificada._

La **declaración responsable** (art. 13 RD 1007/2023 + art. 15 Orden HAC/1177/2024)
se firma cuando el código cumple Y están hechos los pasos legales. Firmarla
antes = exposición al art. 201 bis LGT.

## HECHO y verificado contra código (no contra documentos)

| Área | Estado verificado |
|---|---|
| expedición-cadena | Chokepoint `update_status` con guardas + rectificativa R1 + recurrentes + 4 rutas huérfanas cerradas vía draft + delete bloqueado + fail-closed sin NIF |
| tickets-F2 | Completo: mapeo F2, `FacturaSinIdentifDestinatarioArt61d`, XSD oficial, límite 3000, walk-in, serie T, endpoint TPV, idempotencia, tests |
| F3 sustitutiva | Capacidad completa (columna+migración 0075+mapeo+XML+tests XSD); falta solo flujo de usuario |
| eventos-SIF | Cadena de eventos con advisory-lock + 6 tipos operativos + scheduler 6h + ARRANQUE/PARADA/CAMBIO_MODO/EXPORTACION cableados |
| declaración-doc | Documento a)-l) con manifestación legal + endpoint admin + tab frontend con descarga |
| QR-cotejo | URL oficial `ValidarQR` 4 params en orden, QR en PDF/ticket 80mm/TPV, leyendas literales exactas |
| export-conservación | `export_periodo` JSON + XML ap. 3 (RegistroAlta pelado) + eventos EXPORTACION + triggers WORM de verifactu_chain intactos |
| remisión (gates) | Dry-run por defecto, guard NIF placeholder, cert obligatorio, XAdES, acuse estricto 'Correcto', scheduler 10min/lotes 1000 |
| modo-default | `no_remission` default confirmado, `should_remit` correcto, CAMBIO_MODO atómico |

## BLOQUEANTES para firmar (código, verificados con file:line)

Esfuerzo: S = horas, M = 1-3 días, L = 1+ semana.

### ✅ P1 — CERRADO (commit `14497303`, 2026-07-21)

Guardas de expedición centralizadas en `ensure_verifactu_on_expedition()`
(único punto de decisión). Suite completa 2623✓ + 10 tests nuevos
(`test_verifactu_expedicion_guards.py`).

| # | Cierre |
|---|---|
| 1 | Banking: conciliar (manual/auto) un borrador lo expide → **encadena antes del commit** |
| 2 | Anulación: `cancelled` **bloqueado** si hay registro → fuerza rectificativa (política = delete) |
| 3 | `create_invoice` con guardas: nunca recibidas/demo; borrador encadena al expedirse |
| 4 | `bulk_import`: con VeriFactu activo las emitidas se **rechazan** (anti-bypass); históricas en no_remission siguen sin encadenar (no las expidió este SIF — decisión documentada) |

### ✅ P2 — CERRADO (commits `597f38fa` + `d25ba60d`, 2026-07-21)

| # | Cierre |
|---|---|
| 5 | **Destinatarios** en F1/F3/R1 (NombreRazon+NIF del cliente, posición XSD); fail-closed sin NIF; R5 sin NIF → indicador art. 61.d |
| 6 | **Calificación real**: tipo>0 → S1; 0% → `exencion_causa` (migración 0077): E1-E6 → OperacionExenta, N1/N2 → no sujeta; sin causa → bloqueo |
| 7 | R5 para rectificativas de simplificadas |
| 8 | Huso fijo Europe/Madrid (`TZ_EXPEDICION`) |

### ✅ P3 — CERRADO (commit `597f38fa`, 2026-07-21)

| # | Cierre |
|---|---|
| 9 | Payload de eventos con los **8 campos** del art. 13.1.c (antes 3/8); compat con eventos antiguos |
| 10 | Evento **RESTAURACIÓN** + endpoint `POST /backup-local/restore-event` |
| 11 | Migración **0076**: triggers WORM (append-only) en `sif_events` |
| 12 | `verify_events_integrity` valida enlace columna↔payload + cadena única sin ciclos/bifurcaciones |

### P4 — Remisión + default (el bloque ya conocido)

| # | Bloqueante | Evidencia | Esf. |
|---|---|---|---|
| 13 | POST crudo sin sobre SOAP; URL preproducción POR CONFIRMAR; producción `None`. Se homologa contra preportal (necesita certificado — paso legal). | `verifactu_submit.py:15-16,35-38,199-214` | M/L |
| 14 | `TiempoEsperaEnvio` ni persistido ni respetado; `error` terminal (sin backoff); sin subsanación por línea; sin remisión por requerimiento; anulaciones no se remiten. | `verifactu_submit.py:368-392`, `tasks_scheduler.py:131,142-151` | L |
| 15 | Quitar `no_remission` / default voluntary (~25 ficheros; todo tenant necesitará NIF). | `verifactu_mode.py:17-18` | M |

### ✅ P5 — CERRADO (commits `597f38fa` + `d25ba60d`, 2026-07-21)

| # | Cierre |
|---|---|
| 16 | Export accesible: `GET /verifactu/config/export` (json/xml, admin, evento EXPORTACION) + pestaña "Exportación" en Config › Verifactu |
| 17 | Los 8 `VERIFACTU_SIF_*` declarados en Settings — el `.env` surte efecto en la declaración |

## Re-auditorías adversariales (2026-07-21/22) — 3 rondas, todo cerrado

Tras cerrar P1-P3/P5 se corrieron DOS re-audits adversariales (auditores con
mandato de refutar). Resultado y cierres:

**Ronda 2** (commit `591312b4`): 3 bloqueantes nuevos, cerrados:
- **B1** la tool del agente `update_invoice_status` expedía sin encadenar
  (mutaba status + commit directo) → ahora delega 100% en el chokepoint
  `commands.update_status`.
- **B2** la misma tool anulaba facturas con registro → bloqueado vía chokepoint.
- **B3** `create_rectificativa` con `or 21`: `Decimal('0.00')` falsy → una
  rectificativa de EXENTA nacía con 21% inventado y se encadenaba → coalescing
  `is not None`, hereda `exencion_causa` e `is_demo`.

**Ronda 3** (commit `027a0627`): el barrido de la clase `or 21` estaba
incompleto — cerrado entero:
- **B3-bis** `convert_to_invoice` (presupuesto→factura) persistía exentas al
  21% → contaminaba la cadena. Arreglado + 8 sitios más de la misma clase
  (Facturae, libro fiscal, import, PDF, OCR, bulk, seed).
- **M5** rectificativa de original sin líneas nacía a 0,00 € y la idempotencia
  bloqueaba la buena → línea sintética desde cabecera.
- **M6** el camino de aprobación fabricaba facturas a mano (count()+1 sin lock,
  serie paralela FAC-) → delega en `commands.create_invoice`.
- **Candado permanente**: `test_gate_sin_coercion_falsy_or21` escanea
  `backend/app` y FALLA si el patrón se reintroduce.

**Notas del juez ACEPTADAS y documentadas** (riesgo bajo, sin acción
obligatoria antes de la firma): `create_rectificativa` no filtra facturas
`received`; destinatario solo NIF español (sin rama `IDOtro`); `NIFObligado`
vacío en eventos de tenant sin NIF; TRUNCATE no cubierto por triggers FOR EACH
ROW; reescritura total de cadena indetectable sin ancla externa (inherente
hasta que la remisión P4 dé anclaje en AEAT); backfill con huso +00:00 y tipos
hardcodeados; `run_recurring` encadena el borrador (sobre-encadena, no omite);
export XML aborta entero si un registro histórico está incompleto (debería
degradar por registro).

## No bloqueantes (recomendados, defendibles de posponer)

- `RegistroEvento` XML ap. 5 en el export (eventos ya se conservan íntegros).
- Flujo de usuario F3 (endpoint+UI sobre `substitutes_invoice_id`).
- Página pública externa de la declaración (el art. 15.3 se cumple con el tab del SIF).
- Persistencia por versión + firma del documento (resoluble administrativamente).
- Leyendas QR a 8-9pt (hoy 7pt; "similar" es interpretable).
- PARADA no registrada en shutdown forzoso del desktop (mitigable en el siguiente ARRANQUE).
- Higiene: `mark_verifactu_sent` muerto, comentarios estales, XSD en export, verificación de integridad bajo demanda.

## PENDIENTE — NO código (de Marcos; puerta real para firmar)

- **SL productora** + **consulta legal** por escrito.
- **Certificado electrónico** (o Colaboración Social) + alta en **preportal AEAT** — prerequisito para homologar P4.
- **NIF real + dirección del productor** en configuración (tras cerrar el bloqueante 17).
- **Beta sombra** con Pascual contra preportal.
- Redacción final y **suscripción** del documento (HW real en letra d, firmante, archivo por versión).

## Secuencia hasta la firma

P1+P2+P3+P5 (cerrables ya, sin dependencias externas) → pasos legales (SL,
certificado, preportal) → P4 homologando contra preproducción → beta sombra con
Pascual → **firmar la declaración** → producción.
