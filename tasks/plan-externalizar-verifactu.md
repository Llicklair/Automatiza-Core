# Plan — Externalizar la emisión de facturas y salir del régimen de fabricante de SIF (VeriFactu)

> Objetivo: que **AutomatizaCore deje de ser el productor de un SIF** (Sistema Informático
> de Facturación, RD 1007/2023 / Ley Antifraude), eliminando la responsabilidad de
> fabricante (art. 201 bis LGT, multa hasta 150.000 €) **sin amputar el producto**.
> Todo lo verificado abajo está contra el código real (commits a fecha del plan).

---

## 0. El hecho que define el plan (verificado en código)

- `create_invoice()` (`backend/app/services/billing/commands.py:94,136`) **asigna el número
  correlativo oficial y marca la factura como `issued`** en una sola transacción.
  **Ese acto —emitir el documento fiscal con número de serie— es lo que convierte al
  ERP en un sistema que "expide facturas" = SIF.** Con cadena o sin cadena.
- El flag `VerifactuConfig.mode` (`db/models/billing.py:155`) por defecto es
  `"no_remission"`. En ese estado: NO se escribe la cadena de huellas
  (`verifactu_chain.py:293`) y el envío es no-op (`NoRemissionSubmitter`).
- El envío real a la AEAT **no está cableado**: `send_to_verifactu`
  (`routes/invoices.py:521-539`) fuerza `confirmed=False` → dry-run, sin POST.
  El endpoint de producción es `None`.

**Traducción:** apagar la cadena/envío (ya apagados) **no basta**. Hay que mover el
**acto de emisión** (numeración correlativa + estado `issued`) fuera de nuestro código.

---

## 1. Las dos metas limpias (misma protección legal)

| Opción | Qué es | Producto | Responsabilidad SIF |
|---|---|---|---|
| **A. Totalmente fuera** | El ERP no emite facturas. El usuario factura con su herramienta certificada o la app gratuita de la AEAT. | Menos "redondo" | Cero. No hay SIF. |
| **B. Externalizado** (recomendado) | El ERP integra un **motor de facturación certificado de terceros** para el instante de emisión. | Redondo (facturas desde el ERP) | Del tercero, no nuestra. *Composición de SIF*: cada fabricante responde de su parte. |

**Recomendación: B.** Mismo alivio legal, producto entero. La norma permite componer un
SIF de varios componentes; mientras **nuestro código no produzca el registro/huella/QR/envío**,
no somos el fabricante de esa parte.

---

## 2. Plan técnico (opción B)

1. **Congelar la superficie regulada** (ya casi está): `mode=no_remission` permanente,
   `verifactu_submit` no se cablea a producción. Nada se encadena, nada se remite.
2. **Degradar `create_invoice()` a borrador:** que **NO** asigne número correlativo
   oficial ni marque `issued`. Lo que hoy produce pasa a **borrador/proforma** —
   contenido completo, importes, IVA, todo— pero **sin número fiscal ni valor fiscal**.
3. **Adaptador de emisión** (`emission_provider`), dos implementaciones:
   - `ExternalSifAdapter` → llama al SIF certificado; recibe número, huella, QR y los
     guarda. El registro lo produce el tercero.
   - `AeatAppHandoff` → exporta el borrador para emitir en la app gratuita de la AEAT.
4. **Neutralizar el núcleo SIF** (los 3 call sites de `maybe_append_verifactu_record`,
   en `commands.py:136,254,662`): se sustituyen por la llamada al adaptador o se quitan.
   Ficheros a borrar o dejar tras flag como "no distribuido":
   `verifactu_chain.py`, `verifactu_submit.py`, `registro_facturacion.py`,
   `verifactu_mode.py`, `routes/verifactu_config.py`, migraciones VerifactuRecord/Config.
   - ⚠️ **`xades_signer.py` NO se borra entero:** lo comparten la firma de facturas (fuera)
     y la **presentación de modelos AEAT 303/130/347/390/190** (se queda — es legítima y
     NO es SIF). Se retira solo su uso para firmar registros de factura.
5. **Frontend:** el botón "emitir" deja de disparar la cadena; dispara el handoff/adaptador.
   Ocultar paneles `configuracion/verifactu`, `firma-digital`, `apoderamiento`.
6. **Contabilidad:** `auto_accounting.py` sigue posteando asientos, pero aguas abajo del
   resultado del proveedor externo (o del borrador confirmado), no de nuestro registro.
7. **Gate legal:** 1 hora con gestoría/asesor fiscal que conozca VeriFactu para confirmar
   por escrito que, con la emisión delegada, el producto **no es SIF**.

---

## 3. Módulos que quedan funcionales (inventario verificado)

Todo el ERP **salvo** el núcleo de emisión SIF:

- ✅ **RRHH / nóminas** — siempre fuera del RRSIF.
- ✅ **Contabilidad / asientos** — fuera del perímetro al delegar la emisión.
- ✅ **Remesas / SEPA / tesorería / cobros** — dependen del modelo `Invoice`, no del núcleo SIF.
- ✅ **Documentos / OCR / scanner**.
- ✅ **Dashboards / analytics / reports / RAG / Excel**.
- ✅ **Orquestador / workflows / workers**.
- ✅ **CRM, inventario, marketing, email, POS, productos**.
- ✅ **Presupuestos, proformas, albaranes, borradores de factura (contenido)** — los genera
  la IA libremente. Estos NO disparan el RRSIF (solo la factura completa/simplificada lo hace).
- ✅ **Modelos AEAT (303/130/347/390/190)** — presentación de modelos, NO es SIF (reutiliza
  `xades_signer` para firmar la presentación; ese uso se conserva).

**Se externaliza / deja de ser responsabilidad nuestra:** el acto de emisión (correlativo +
`issued`), la cadena de huellas, el envío a la AEAT, el registro alta/anulación, y la firma
XAdES *de facturas*.

---

## 4. Riesgos legales que quedan (honesto)

1. **La frontera debe ser real, no cosmética.** El borrador no puede funcionar como la
   factura entregada. Si el "borrador" es de facto el justificante fiscal que el cliente usa
   para deducirse el IVA, se vuelve a "software de doble uso". → Mitigación: la emisión SIEMPRE
   pasa por el componente certificado; el borrador va marcado "sin valor fiscal".
2. **Composición de SIF:** la integración debe ser limpia — nosotros pasamos datos, el tercero
   produce registro/huella/QR/envío. Mientras nuestro código no produzca el registro, no somos
   el fabricante de esa parte.
3. **Forma jurídica** para comercializar (autónomo tarifa plana ~80 €/mes, o SL con 1 € de
   capital por la Ley Crea y Crece). Necesaria para **vender**, NO para terminar ni pilotar.
   No es un riesgo VeriFactu.
4. **RGPD** — aplica igual (datos personales/fiscales). Vía separada, independiente de esto.
5. **Reglamento de IA (UE)** — según qué haga la IA. Un ERP de facturación/contabilidad
   normalmente no es alto riesgo; si tomara decisiones consecuentes (RRHH/crédito), análisis
   aparte. Vía separada.
6. **Modelos AEAT (303, etc.)** — si el ERP los presenta, conlleva responsabilidad de
   exactitud (civil frente al cliente), gestionable con disclaimers. NO es el régimen de
   fabricante de SIF ni los 150.000 €.

**Desaparece:** el riesgo de los 150.000 € del art. 201 bis LGT para la parte de facturación
— el que motivó todo esto.

---

## 5. ¿VeriFactu queda totalmente fuera o externalizado?

- **Externalizado** (opción B, recomendada): sí, pero **no como responsabilidad tuya** — lo
  hace un motor certificado de terceros integrado. Tú NO eres el fabricante del SIF.
- **Totalmente fuera** (opción A): el ERP ni siquiera integra emisión; el usuario factura por
  su cuenta.

En ambos casos, la **responsabilidad de SIF no es tuya**. La diferencia es de integración de
producto, no de exposición legal.

---

## 6. Orden de ejecución sugerido (reversible primero)

1. (Gratis, ahora) Confirmar con este plan qué se toca. Nada se borra aún.
2. (1 h, barato) Consulta legal: validar que "emisión delegada ⇒ no SIF".
3. Elegir A o B. Si B, elegir motor certificado (o app AEAT como puente).
4. Rama de trabajo: degradar `create_invoice()` a borrador + adaptador de emisión.
5. Neutralizar núcleo SIF tras flag (reversible) antes de borrar nada definitivamente.
6. Verificar suite completa: que remesas/contabilidad/dashboards siguen verdes sin el núcleo.

---

## 7. Proveedores "VeriFactu como API" y coste (verificado, mediados 2026)

Categoría: un tercero produce registro + huella encadenada + QR + envío a la AEAT; tú
llamas a su API. Fuentes con URL abajo.

| Proveedor | Qué ofrece | Precio | Notas |
|---|---|---|---|
| **Verifacti** ([verifacti.com](https://www.verifacti.com/en)) — *recomendado* | API REST: registro, cadena, QR, validación censo AEAT, envío, webhooks. VeriFactu + TicketBAI. | **desde 2,9 €/NIF/mes** (por emisor), −10% anual, overage ≈0,2 cént/factura >3.000/mes | Precio público en €, self-service. **1 NIF de prueba = 0 €** → construir/probar gratis. |
| **Fiskaly SIGN ES** ([fiskaly.com](https://www.fiskaly.com/signes/verifactu)) | Una API VeriFactu/TicketBAI/e-invoice, ISO-cert. Clientes: SumUp, Shopify, Uber. | **Sin precio público** (ventas) | Más enterprise. |
| **B2Brouter** ([b2brouter.net](https://www.b2brouter.net/es/api-verifactu/)) | API: registro, hash, QR, log eventos, envío. | API a consultar + ~800 € setup. Web app: 0 € / 110 € / 300 € año | **Marca blanca** + **Startup Program (100% dto.)** para SaaS. |
| **App gratuita AEAT** ([sede AEAT](https://sede.agenciatributaria.gob.es/Sede/iva/sistemas-informaticos-facturacion-verifactu.html)) | Emisión VeriFactu manual. | **0 €**, sin límite de volumen | **NO es API** — hand-off manual, sin tickets, sin integración. = opción A. |

**Quién paga:** modelo integrado → **paga el ISV** (~2,9 €/NIF/mes con Verifacti = por
cliente de pago) y lo **incluye en la suscripción**; el cliente final paga solo tu ERP.
Marginal por factura ≈ 0. Escala con ingresos: solo pagas cuando ya cobras.

**⚠️ Matiz de declaración responsable (arquitectura mixta):** el tercero produce el
componente fiscal, pero la declaración responsable **NO se transfiere entera** de forma
automática. Verifacti facilita una **plantilla de declaración responsable para arquitectura
mixta con componente externo** → **probablemente sigas firmando una declaración más ligera
por TU parte** (la que no emite). Lo que se externaliza a la certificadora del tercero es la
parte dura (cadena, envío, XAdES), donde caería la no-conformidad y los 150 k. **Confirmar el
alcance exacto en la consulta legal de 1 h.**
