# Holded vs. AutomatizaPyme — Análisis 360º

> Fecha: 2026-06-21 · Áreas: Contabilidad/Fiscal · Inventario/ERP · RRHH · CRM/IA/Automatización
> Objetivo: posicionamiento comercial + roadmap de producto + diferenciación técnica.

---

## 0. TL;DR

- **No compites en la misma liga, y eso es bueno.** Holded es un SaaS horizontal cloud, barato, pulido y con red de distribución (900k usuarios, +200 integraciones, +200 gestorías). Ganarle en "todo en uno genérico y barato" es imposible y no deberías intentarlo.
- **Tu foso es la IA agéntica + soberanía del dato.** Holded la IA *sugiere*; la tuya *ejecuta y escribe en la BD*. Y no solo dentro del ERP: tus agentes **trabajan fuera del perímetro de un ERP clásico** — triaje y envío de correo, campañas/publicación en redes, redacción de informes a PDF, generación e importación de Excel, cargas masivas de datos, ajustes masivos de stock. Es una **fuerza de trabajo**, no un asistente de data-entry. Holded es cloud puro; tú ofreces on-prem/escritorio con Postgres embebida. Ahí no te pueden seguir sin reescribir su producto.
- **Precio: juegas en premium (≈180 €/pyme/mes vs. 14,5–49,5 €/mes de Holded).** Eso solo se sostiene vendiendo *trabajo hecho* (automatización + ahorro de horas), no *software*. Tu unidad de venta no es "una licencia", es "un empleado de IA".
- **Tu mayor riesgo no es producto, es validación comercial y el último 5% fiscal** (presentación telemática real a AEAT sigue en `dry_run`). Coherente con tu README: no prometas "presento a Hacienda" — promete "lo dejo calcado y listo, tu gestor presenta".

---

## 1. Holded en una frase

> "El software todo-en-uno en la nube para pymes y autónomos: facturación, contabilidad, CRM, proyectos, inventario y RRHH, con tu gestor incluido gratis."

**Datos clave (jun-2026):**
- +900.000 usuarios · 4,5/5 en G2 y Capterra · +200 integraciones · 99,9% SLA · certificado Verifactu.
- **6 productos**: Facturación · Contabilidad · CRM · Proyectos · Inventario · RRHH/Equipo.
- **Add-ons ("gemas")**: Inventario 25 €/mes, Fabricación 25 €/mes, Team Pro, catálogo B2B…
- **Precios (empresa pequeña, mensual sobre anual)**: Básico 14,50 € · Estándar 29,50 € (popular) · Avanzado 49,50 €. Segmentos: Autónomos / Pequeñas / Medianas / Asesorías. **Acceso del gestor gratis en todos los planes.**
- **Modelo**: cloud puro + apps móviles. Banca conectada (BBVA, Santander, ING, Revolut…), Holded Wallet (tarjetas).

---

## 2. Comparativa por área

Leyenda: ✅ fuerte · 🟡 parcial/básico · ❌ no tiene · 🏆 ventaja clara.

### 2.1 Contabilidad / Fiscal
| Capacidad | Holded | AutomatizaPyme |
|---|---|---|
| Facturación + Verifactu | ✅ certificado, pulido | ✅ cadena hash + audit WORM |
| Contabilidad española (diario, P&G, balance) | ✅ asientos automáticos, analítica | ✅ + activos, plan de cuentas |
| Cálculo de modelos AEAT | 🟡 "modelos listos para enviar" (303/IRPF/Sociedades) | 🏆 **cálculo real de casillas + XML/XAdES** (303,130,111,115,190,200,347,390) |
| Presentación telemática a SEDE AEAT | 🟡 prepara, el gestor presenta | 🟡 infra lista pero **`dry_run` por defecto** (no enviar real sin certificado) |
| Integración SII | ✅ (plan Estándar) | ❌ |
| Conciliación bancaria PSD2 | ✅ reglas, remesas | ✅ auto-match con IA |
| Tesorería / previsión cashflow | ✅ + Wallet/tarjetas | 🟡 beta |

**Lectura:** empatas o ganas en *cálculo fiscal profundo*; pierdes en *integración bancaria/SII madura* y en el último tramo de presentación real. Tu narrativa honesta: "te lo dejo calcado, tu gestor le da a enviar".

### 2.2 Inventario / ERP
| Capacidad | Holded | AutomatizaPyme |
|---|---|---|
| Productos, stock, multi-almacén, lotes | ✅ tiempo real | ✅ Product/Lot/Warehouse/Movement |
| Compras / ventas / albaranes / presupuestos | ✅ | ✅ + sales/purchase orders, quotes |
| POS / TPV | 🟡 (gema) | ✅ módulo POS |
| Analítica de inventario + reorden | 🟡 informes | ✅ analítica + reorden |
| **Órdenes de fabricación (BOM)** | ✅ gema 25 €/mes | ❌ |
| **Sincronización e-commerce (Shopify/Woo)** | 🏆 nativa | ❌ |

**Lectura:** paridad en gestión de stock. **Gaps reales:** fabricación/BOM y sync e-commerce — ahí Holded gana por ecosistema.

### 2.3 RRHH
| Capacidad | Holded | AutomatizaPyme |
|---|---|---|
| Empleados, contratos, documentos | ✅ + app móvil | ✅ + generación IA de contratos/cartas |
| **Cálculo de nómina (IRPF + SS)** | 🟡 *contabilización* de nóminas (importa, no calcula a fondo) | 🏆 **cálculo real IRPF+SS, finiquito** |
| Fichaje / control horario | ✅ digital, móvil | ✅ módulo time |
| Vacaciones / ausencias | ✅ flujo móvil pulido | ✅ |
| Reclutamiento + scoring IA de CVs | ❌ | 🏆 análisis IA candidato↔posición |

**Lectura:** este puede ser tu **frente de ataque más claro**. Holded *contabiliza* nóminas; tú las *calculas*. Para una asesoría laboral, eso es la diferencia entre "ayuda" y "lo hace por mí".

### 2.4 CRM / IA / Automatización
| Capacidad | Holded | AutomatizaPyme |
|---|---|---|
| CRM (embudo, contactos, oportunidades) | ✅ visual, integrado | ✅ agente CRM |
| Proyectos / rentabilidad | ✅ | ✅ |
| Integraciones / API | 🏆 +200 (Stripe, Shopify, HubSpot, Zapier, Make) | 🟡 OAuth cifrado, importador Holded, marketplace propio |
| IA: ¿qué hace? | 🟡 sugiere (categoría, revisión del asesor) | 🏆 **ejecuta**: NL → clasifica/planifica/valida/despacha a 14 agentes que escriben en BD |
| Workflows persistentes + scheduler | ❌ (usa Zapier/Make externos) | 🏆 parser NL→workflow + cron/eventos + recovery + approvals |
| Empleados IA configurables | ❌ | 🏆 45 skills, budget guard, autonomía granular |
| RAG documental con citas a página | ❌ | 🏆 pgvector + citas exactas |
| **On-prem / soberanía del dato** | ❌ cloud puro | 🏆 Electron + Postgres embebida |

**Lectura:** aquí no hay comparación. Toda tu ventaja defendible vive en esta fila.

### 2.5 Capacidades operativas de los agentes (la fuerza de trabajo)
Esto es lo que un ERP de registro como Holded **no hace por sí mismo** — lo delega a humanos o a Zapier/Make. Tus agentes lo ejecutan dentro del producto:

| Capacidad | Holded | AutomatizaPyme | Evidencia |
|---|---|---|---|
| Triaje + envío/respuesta de correo | ❌ (lo haces en Gmail) | ✅ SMTP/IMAP real (Gmail/Outlook) | `services/email/sender.py`, `agents/email/tools.py` |
| Campañas + publicación en redes | ❌ | ✅ publica vía Zernio + genera imagen IA | `services/marketing/zernio_publisher.py` |
| Redacción de informes → PDF | ❌ (informes fijos) | ✅ informe en lenguaje natural a PDF | `agent_tools/reports.py` (reportlab) |
| Generar / importar Excel por IA | 🟡 export fijo | ✅ `export_erp_data` + `import_excel` (volcado masivo) | `agents/excel/` |
| Importación de facturas por OCR | 🟡 (gema/escaneo) | ✅ OCR + alta idempotente al ERP | `documents.import_invoice_document` |
| Ajustes/actualizaciones masivas de stock conversacionales | ❌ | ✅ `batch_adjust_stock` / `batch_update_products` (preview+confirm) | `agents/inventory/tools.py` |
| Crear un "empleado IA" desde lenguaje natural | ❌ | ✅ `create_ai_employee_from_description` | `agent_tools/ai_team.py` |
| Consultas fiscales RAG + alertas AEAT/BOE | ❌ | ✅ | `agents/compliance/tools.py` |

**Catálogo de skills**: ~50 capacidades operativas (`agent_tools/ai_team.py`, `AVAILABLE_SKILLS`) que se componen en "empleados IA" por tenant: facturar, nóminas, enviar emails, leer bandeja, buscar en documentos, exportar Excel, generar informes PDF, etc.

> ⚠️ **Honestidad (para no sobre-prometer en demo):**
> - **Banca/PSD2 usa datos DEMO** — no hay proveedor PSD2 real cableado todavía (`agents/banking/_psd2_helpers.py`).
> - **Scoring de "fit" de CVs deshabilitado en MVP** por cumplimiento (extrae datos, no puntúa).
> - **Dos catálogos de skills divergen** (operativo vs. etiquetas de UI): conviene unificarlos para que lo que el usuario ve sea exactamente lo ejecutable.

---

## 3. Tus puntos fuertes (dónde ganas)

1. **IA que actúa, no que sugiere.** "Hazme la nómina de Juan" → hecho. Holded sigue siendo data-entry asistido.
2. **Una fuerza de trabajo, no un módulo.** Tus agentes cubren tareas que viven *fuera* del ERP: correo (triaje/envío), marketing y publicación en redes, redacción de informes a PDF, generación/importación de Excel, OCR de facturas, cargas y ajustes masivos. Holded eso lo deja a humanos + Zapier/Make.
3. **Orquestación + workflows persistentes nativos.** Holded externaliza esto a Zapier/Make; tú lo tienes dentro con scheduler, recovery y approvals fiscales.
3. **Soberanía del dato (on-prem/escritorio).** Decisivo para legal, sanitario, ciberseguridad, despachos — clientes que *no pueden* poner datos en cloud.
4. **Profundidad fiscal/laboral real.** Casillas AEAT calculadas + nómina IRPF+SS + finiquito. Más "motor" que "formulario".
5. **Empleados IA configurables por tenant.** Vendes plantilla ("contable IA", "RRHH IA"), no menús.

## 4. Donde Holded te gana (roadmap)

| Gap | Prioridad | Por qué |
|---|---|---|
| Cerrar presentación AEAT real (salir de `dry_run`) | 🔴 Alta | Es tu mayor diferenciador fiscal *y* tu mayor riesgo si lo prometes sin cerrarlo |
| Integración SII | 🟠 Media | Esperado en pymes con volumen |
| Sync e-commerce (Shopify/Woo) | 🟠 Media | Puerta de entrada de muchas pymes de producto |
| App móvil | 🟡 Media-baja | Fichaje/aprobaciones se viven en el móvil |
| Ecosistema de integraciones | 🟡 Baja | No ganarás a +200; elige 5-10 que importen a tu nicho |
| Fabricación / BOM | 🟢 Baja | Solo si atacas pymes industriales |

## 5. Posicionamiento comercial

- **No vendas "como Holded pero…".** Vendes una categoría distinta: **"tu equipo de IA con tus datos en tu casa"**.
- **El encuadre ganador: "sistema de registro" vs "sistema que trabaja".** Holded es donde *guardas* los datos; AutomatizaPyme es quien *hace el trabajo* con ellos (factura, concilia, redacta el informe, manda el correo, lanza la campaña, vuelca el Excel). Esa frase resume tu diferencia mejor que cualquier tabla de features.
- **Precio premium justificado por horas, no por features.** A ~180 €/mes tienes que demostrar que ahorras ≥X horas de gestoría/admin al mes. La demo debe ser "mira cómo hace la nómina/el 303 solo", no una lista de módulos.
- **Nicho de cuña**: asesorías laborales/fiscales pequeñas-medianas + pymes con dato sensible. Ahí Holded es *débil* (cloud, IA que no ejecuta, nómina solo contabilizada).
- **Coexistencia, no sustitución, al principio**: tienes importador de Holded → "tráete tus datos de Holded y deja que la IA trabaje".

## 6. Roadmap priorizado (90 días sugerido)

1. **Cerrar el bucle fiscal** que sí puedas firmar legalmente (o reposicionar claramente "calcado + el gestor presenta"). Mata el miedo al descuadre con validación de 1-2 asesorías reales.
2. **Empaquetar 2 "empleados IA" estrella** con ROI medible (Contable IA = 303/130 + conciliación; RRHH IA = nóminas + fichaje + ausencias).
3. **Conseguir 3-5 pymes pagando** y medir horas ahorradas → es tu único argumento de precio premium.
4. Diferir e-commerce/SII/fabricación hasta que un cliente real lo pida.

---

### Apéndice: fuentes
- Holded: home ES + pricing ES + módulos (indexado 2026-06-21).
- AutomatizaPyme: inventario de código (agents/, services/, routes/, db/models/, frontend) + README/ARCHITECTURE.
