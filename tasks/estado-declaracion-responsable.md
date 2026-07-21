# Estado — Declaración responsable / conformidad VeriFactu

_Última actualización: 2026-07-21. Rama de trabajo: `feat/verifactu-eventos-declaracion`
(stack sobre `fix/verifactu-doble-uso-registro` → `feat/verifactu-tickets-f2`), todo
subido a `origin`, sin mergear a master._

La **declaración responsable** (art. 13 RD 1007/2023 + art. 15 Orden HAC/1177/2024) es
una declaración jurada del **productor** de que el SIF cumple. **Es el último paso**:
se firma cuando el código cumple Y están hechos los pasos legales. Firmarla antes = art.
201 bis LGT.

## HECHO y verificado (esta sesión)

| Área | Estado | Commit |
|---|---|---|
| Doble uso: registro en la expedición + bloqueo sin NIF | ✅ suite completa 2598✓ | `07ef51cf` |
| Tickets **F2** (registro TipoFactura F2) | ✅ | `0e339bfe` |
| Puente POS → factura simplificada + endpoint + frontend + QR ticket | ✅ | `a43f671e`,`f315045a`,`cf18d651`,`34d44ce7` |
| Registro de **eventos** (cadena huella) + `CAMBIO_MODO` | ✅ | `6e7b9c34`,`19c25ac4` |
| Eventos: **resumen 6h** + **detección de anomalías** (scheduler) | ✅ | `0e10af69` |
| **Remate F2**: `FacturaSinIdentifDestinatario` (valida XSD) + límite 3000€ | ✅ | `019d58dc` |
| **F3** sustitutiva (`FacturasSustituidas`, valida XSD) | ✅ | `dc8d4582` |
| **Documento** de la declaración (art. 15) + endpoint `/verifactu/config/declaracion-responsable` | ✅ | `fea847b9` |
| **QR → cotejo AEAT** (`ValidarQR` + 4 params) + leyendas "QR tributario:"/"VERI*FACTU" | ✅ | `076a5a9c` |
| **Exportación/conservación** por periodo + eventos `EXPORTACION` (art. 9.1 h/i) | ✅ | `707b67ec` |
| Eventos **ARRANQUE/PARADA** (ciclo de vida app, por tenant) | ✅ | `17be2494` |
| **Frontend**: visor/descarga del documento (tab en Config › Verifactu, art. 15.3) | ✅ | `5d6e4ff0` |
| Export en formato **anexo** (`RegistroAlta` "pelado", ap. 3) | ✅ | `b3d94328` |

Specs verificadas verbatim contra BOE / doc técnico AEAT.

## PENDIENTE — código

1. **Remisión robusta + quitar `no_remission`** — **el ÚNICO bloque de código que queda.**
   Dos piezas:
   - (a) **Remisión a la AEAT sólida**: control de flujo (espera entre envíos), lotes
     de máx. 1000, remisión por requerimiento.
   - (b) **Flipar el default** a VeriFactu (eliminar `no_remission`).
   - ⚠️ Flipar (b) SIN (a) = limbo no conforme (registros que ni remiten ni firman).
     Hacer **remisión-primero**, en sesión propia. Toca default + ~10 tests + frontend.
2. _Residual mínimo (no bloquea nada)_: el `RegistroEvento` del anexo (ap. 5) en el
   export — hoy los eventos se exportan como payload + huella (íntegro); falta su XML
   exacto (requiere la estructura de campos del ap. 5).

## PENDIENTE — NO código (de Marcos; es la puerta real para firmar)

- **Consulta legal** por escrito (conformidad + responsabilidad del productor).
- **SL productora** (la sociedad que suscribe la declaración, no la persona física).
- **Certificado electrónico** o **Colaboración Social** con la AEAT + alta en el portal
  de pruebas (preportal) para la beta y luego producción.
- **NIF real del productor** en el SIF: hoy es placeholder (`VERIFACTU_SIF_NIF` en
  settings, `B00000000`). Debe ser el de la SL antes de presentar nada real.

## Secuencia hasta la firma

Cerrar remisión (1) → beta **sombra** con Pascual contra preportal → pasos legales
(SL + consulta + certificado + NIF real) → **firmar la declaración** → producción.
