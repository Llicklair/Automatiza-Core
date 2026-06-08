# Revisión de completitud por módulo (agentes)

**Proyecto:** AutomatizaPyme · **Fecha:** 7 jun 2026
**Enfoque:** ¿cumple cada agente su función? ¿Dónde necesita iterar?
**Lente principal:** "preguntar antes de actuar" — acciones con efectos que deberían
previsualizarse/confirmarse (patrón **preview/confirm en la tool**, como el agente de stock),
y campos que el agente debería **preguntar** en vez de auto-rellenar.

---

## Estado de la confirmación hoy

Ya hay un mecanismo grueso de **aprobación humana** (`requires_human_approval` +
`services/workflow/approval_actions.create_action_approval`) que usan **accounting,
banking, billing y hr** para acciones sensibles (p. ej. factura de venta >5.000€,
nóminas). Encima de eso, el agente de **stock** estrena el patrón ligero
**preview/confirm en la tool** (`confirm=false` → resumen, `confirm=true` → ejecuta).

El hueco no está en que falte tecnología, sino en que **dos de las acciones más
irreversibles no tienen ninguna confirmación** (enviar email, integrar stock al
importar compras) y en que el agente de documentos **trabaja en silencio**.

---

## Cuadro por agente

| Agente | Función | Completitud | Acciones consecuentes | ¿Confirma? | Iteración recomendada |
|---|---|---|---|---|---|
| **email** | Leer bandeja y enviar correos | Funcional | `send_email` (irreversible) | 🔴 **No** | preview/confirm obligatorio antes de enviar |
| **documents** | Asimilar/clasificar docs, importar facturas de compra, búsqueda | Funcional pero "silencioso" | `import_invoice_document`, `classify_document` | 🔴 **No** | preview de datos extraídos + preguntar "¿registro? ¿actualizo stock?" |
| **billing** | Facturación de VENTA (facturas, albaranes, envío, estados) | Alta | `send_invoice_by_email`, `update_invoice_status`, `create_invoice` | 🟡 Parcial (>5.000€) | preview/confirm en envío y en anular/cambiar estado |
| **hr** | Empleados + nóminas | Alta | `generate_all_payrolls` (masivo), `approve_payroll` | 🟡 Parcial | preview del lote antes de `generate_all_payrolls` |
| **inventory** | Stock: consultas + modificación por lotes | Alta (nuevo) | `batch_adjust_stock`, `batch_update_products` | ✅ Sí | añadir tools de transferencia entre almacenes y lotes/caducidad |
| **accounting** | Asientos, saldos, P&G, activos | Alta | `create_journal_entry` | ✅ Sí (approval) | conciliación con banca (hoy manual) |
| **banking** | Saldos, transacciones, conciliación | Alta | `reconcile_transactions` | ✅ Sí (approval) | — |
| **crm** | Oportunidades + clientes | Suficiente | `create_client`, `update_opportunity_stage` | 🟡 No (bajo riesgo) | confirm ligero en alta de cliente (evitar duplicados) + actividades/seguimiento |
| **excel** | Importar/exportar/modificar datos | Suficiente | `import_excel`, `modify_excel` | 🔴 No | preview de qué crea/actualiza en el ERP antes de importar |
| **recruitment** | Selección: puestos, candidatos, CV | Suficiente | writes de bajo riesgo | 🟡 No | (ya reforzado en errores) confirm opcional al descartar candidatos |
| **compliance** | Asesoría fiscal (solo lectura) | Completo para su alcance | — | n/a | — |
| **rag** | Búsqueda y respuesta documental | Completo por naturaleza | — | n/a | — |
| **workflow** | Crear/gestionar automatizaciones | Apoyado en servicio profundo | crea reglas | (review previo) | — |
| **marketing** | (previsto: campañas, email mk, redes) | 🔴 Incompleto (stub) | — | — | módulo real pendiente (ya identificado) |

🔴 falta y es de riesgo · 🟡 parcial/mejorable · ✅ cubierto

---

## Los tres focos prioritarios

### 1. `email.send_email` — enviar sin red de seguridad (riesgo ALTO)
Enviar un correo es irreversible y hoy no media ninguna confirmación. Debería
comportarse como las tools de stock: con `confirm=false` devolver un borrador
(destinatario, asunto, cuerpo) para que el usuario lo apruebe, y enviar solo con
`confirm=true`. Es el cambio con mejor relación riesgo/esfuerzo.

### 2. `documents.import_invoice_document` — el caso de la factura de compra
Hoy importa la factura de compra pero fuerza `apply_stock=False` (línea 114) y nunca
pregunta. El servicio `import_received_invoices` ya sabe actualizar el inventario.
Iteración propuesta: con `confirm=false`, mostrar lo extraído por OCR (proveedor, nº,
fecha, base/IVA/total y líneas detectadas) y preguntar dos cosas: **(a)** ¿registro
esta factura de compra?, **(b)** ¿actualizo el stock con sus líneas? Solo con
`confirm=true` (y el flag de stock que elija el usuario) se ejecuta. Esto cierra el
flujo factura-de-compra→stock que mencionaste y de paso resuelve el "que pregunte en
vez de rellenar a ciegas".

### 3. Gestoría documental conversacional (OCR dudoso)
Más allá de la factura, las tools de documentos auto-clasifican y auto-extraen sin
validación. Cuando la confianza del OCR es baja o faltan campos clave (NIF, total),
el agente debería **preguntar** en lugar de asumir. El patrón preview/confirm sirve
también aquí: el `confirm=false` es el momento natural para listar los campos dudosos
y pedir que el usuario los confirme o corrija antes de persistir.

---

## Backlog priorizado (despliegue de preview/confirm)

1. **email.send_email** — borrador + confirmación. (ALTA)
2. **documents.import_invoice_document** — previsualizar OCR + preguntar registro y stock. (ALTA)
3. **billing.send_invoice_by_email** y **update_invoice_status** (anular). (MEDIA)
4. **hr.generate_all_payrolls** — preview del lote (nº de nóminas + total) antes de generar. (MEDIA)
5. **excel.import_excel / modify_excel** — preview de cambios al ERP. (MEDIA)
6. **crm.create_client / update_opportunity_stage** — confirm ligero. (BAJA)

Transversal: para no duplicar mecanismos, conviene **unificar el patrón** — o todo
preview/confirm en la tool (ligero, elegido), o reutilizar el approval gate existente
donde ya está (accounting/banking/billing/hr). Recomiendo preview/confirm en la tool
para las acciones nuevas y dejar el approval gate para los umbrales legales/fiscales
que ya cubre.

---

## Gaps funcionales (no de confirmación)

- **marketing**: sigue siendo un generador de texto; pendiente el módulo real
  (campañas, email marketing, automatización a redes) ya acordado.
- **inventory**: el servicio tiene transferencias entre almacenes y gestión de
  lotes/caducidad (FEFO) que el agente aún no expone como tools.
- **crm**: sin registro de actividades/seguimiento ni reporting de pipeline.
- **accounting**: la conciliación contabilidad↔banca es manual.
