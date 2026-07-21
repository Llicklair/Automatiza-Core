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
