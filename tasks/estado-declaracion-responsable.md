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

### P1 — La garantía central ("todo lo expedido queda encadenado") es hoy falsa

| # | Bloqueante | Evidencia | Esf. |
|---|---|---|---|
| 1 | **Bypass banking**: la conciliación pasa facturas `draft`→`paid` directo, sin `update_status` → factura expedida SIN registro. Puentea el chokepoint. | `state_machine.py:52`, `banking/service.py:186-187,444,473-474` | S/M |
| 2 | **Anulación sin registro**: `update_status` permite `cancelled` sobre factura con VerifactuRecord sin generar RegistroAnulacion (builders existen, huérfanos). | `commands.py:264-305`, `verifactu_chain.py:84` | M |
| 3 | `create_invoice` encadena INCONDICIONAL (sin `EMITTED_INVOICE_TYPES` ni `is_demo`) → `received`/demo contaminarían la cadena en voluntary. | `billing/commands.py:134-136` | S |
| 4 | `bulk_import` crea facturas `issued`/`paid` sin registro ni marca de excepción. | `migration/bulk_import.py:369-381` | S/M |

### P2 — Contenido del registro (anexo Orden)

| # | Bloqueante | Evidencia | Esf. |
|---|---|---|---|
| 5 | Falta bloque **`Destinatarios`** (NIF/nombre cliente) en RegistroAlta para F1. | `registro_facturacion.py:256-309` | M |
| 6 | **`CalificacionOperacion` fija S1**: exentas E1-E6, N1/N2, S2 se calificarían mal. | `registro_facturacion.py:52,236` | M |
| 7 | Rectificativa de simplificada mapea a R1, no **R5**. | `verifactu_chain.py:243-244` | S |
| 8 | Huso horario depende de la tz del SO, no fija Europe/Madrid. | `verifactu_chain.py:262`, `sif_events.py:77` | S |

### P3 — Eventos SIF por debajo del mínimo

| # | Bloqueante | Evidencia | Esf. |
|---|---|---|---|
| 9 | Payload de evento con 3 de 8 campos exigidos (faltan productor, ID SIF, versión, instalación, NIF obligado). | `sif_events.py:43-50` | S/M |
| 10 | Falta evento **RESTAURACIÓN** de copia de seguridad. | `sif_events.py:24-38` | S |
| 11 | `sif_events` SIN triggers append-only (verifactu_chain sí los tiene). | `0074_sif_events.py` vs `0011:52-77` | S |
| 12 | `verify_events_integrity` no valida el enlace `huella_anterior`. | `sif_events.py:100-108` | S |

### P4 — Remisión + default (el bloque ya conocido)

| # | Bloqueante | Evidencia | Esf. |
|---|---|---|---|
| 13 | POST crudo sin sobre SOAP; URL preproducción POR CONFIRMAR; producción `None`. Se homologa contra preportal (necesita certificado — paso legal). | `verifactu_submit.py:15-16,35-38,199-214` | M/L |
| 14 | `TiempoEsperaEnvio` ni persistido ni respetado; `error` terminal (sin backoff); sin subsanación por línea; sin remisión por requerimiento; anulaciones no se remiten. | `verifactu_submit.py:368-392`, `tasks_scheduler.py:131,142-151` | L |
| 15 | Quitar `no_remission` / default voluntary (~25 ficheros; todo tenant necesitará NIF). | `verifactu_mode.py:17-18` | M |

### P5 — Operativa mínima

| # | Bloqueante | Evidencia | Esf. |
|---|---|---|---|
| 16 | Export sin endpoint HTTP ni UI (la capacidad de volcado del art. 9 no es accesible al usuario/AEAT). | grep `export_periodo` → 0 rutas | M |
| 17 | **Ningún `VERIFACTU_SIF_*` declarado en Settings** (`extra='ignore'` los descarta): la declaración imprime SIEMPRE placeholders (NIF B00000000, dirección "pendiente"). | `core/config.py` (0 matches) | S |

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
