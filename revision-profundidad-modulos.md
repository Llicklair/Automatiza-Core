# Revisión de profundidad de módulos — ¿listos para piloto/producción?

**Proyecto:** AutomatizaPyme · **Fecha:** 7 jun 2026
**Criterio de medición:** Lanzamiento a producción/piloto con usuarios reales (completitud funcional, manejo de errores, aislamiento multi-tenant, validaciones y tests).
**Alcance:** Agentes de dominio + capa de servicios.

---

## Veredicto general

La arquitectura es **sólida y consistente**: capas estrictas (rutas → servicios → agentes → modelos), aislamiento multi-tenant forzado por wrapper `_isolated` + `ContextVar`, y una suite de **176 archivos de test** que cubre API, servicios, agentes, RLS/multitenant, e2e y todo el bloque fiscal español (AEAT modelos 200/303/IVA, VeriFactu, retenciones).

La mayoría de los módulos **tienen profundidad suficiente** para un piloto. El problema no es la base, sino **dos o tres puntos concretos** donde la profundidad no llega al estándar de producción —principalmente **marketing**.

---

## Cuadro de profundidad — Agentes

| Módulo | Líneas | Tools reales | tenant_id | try/except | Test | Veredicto piloto |
|---|---|---|---|---|---|---|
| orchestrator | 4.698 | (núcleo) | 113 | 132 | extensos | ✅ Listo |
| billing | 1.272 | 14 | 56 | 40 | fuertes | ✅ Listo |
| hr | 1.158 | 8 | 62 | 38 | fuertes | ✅ Listo |
| excel | 1.014 | 6 | 47 | 16 | sí | ✅ Listo |
| banking | 683 | 5 | 29 | 15 | sí | ✅ Listo |
| email | 671 | 6 | 36 | 23 | sí | ✅ Listo |
| documents | 579 | 4 | 29 | 21 | sí | ✅ Listo |
| accounting | 425 | 5 | 21 | 14 | 172 líneas | ✅ Listo |
| crm | 422 | 6 | 27 | 14 | smoke | 🟡 Suficiente, ampliable |
| compliance | 389 | 5 | 19 | 16 | smoke | 🟡 Suficiente, verificar exactitud |
| rag | 373 | 2–3 | 11 | 10 | smoke | 🟡 Suficiente (fino por naturaleza) |
| recruitment | 360 | 7 | 18 | 4 | smoke | 🟡 Suficiente, poco manejo de errores |
| workflow | 287 | (compilador) | 6 | 6 | sí (servicio) | ✅ Listo (apoyado en servicio profundo) |
| **marketing** | **129** | **2** | **7** | **2** | smoke | 🔴 **Insuficiente para producción** |

✅ Listo · 🟡 Suficiente para piloto pero con margen · 🔴 No alcanza profundidad de producción

---

## Hallazgos por prioridad

### 🔴 1. Marketing es un generador de texto, no un módulo

`agents/marketing` (129 líneas) solo tiene **2 herramientas reales**: leer el catálogo de productos y generar un PDF. El agente invoca al LLM para producir un "plan de contenidos" y termina. **No persiste nada**: no guarda campañas, ni calendario editorial, ni piezas de contenido; no hay integración con canales (email/redes), ni métricas. El propio test lo reconoce: *"marketing is intentionally small"*.

Para piloto sirve como **asistente de sugerencias**, pero no como módulo equivalente a billing o hr. Si marketing forma parte de la promesa de producto, necesita: modelo de datos (campaña/contenido), herramientas de crear/listar/actualizar, y al menos un canal de salida.

### 🟡 2. Tests de agentes son *smoke*, no de corrección de negocio

Los tests por agente (`test_marketing_agent.py`, `test_crm_agent.py`, etc., ~70 líneas) verifican que el grafo compila, que las tools están registradas y que el nodo invoca al LLM con mock. La **corrección funcional** se cubre realmente en la capa API/servicio (`test_api_*`, `test_service_*`). Esto está bien, pero los dominios cuyo valor vive **en el agente** (crm, compliance, recruitment) tienen una cobertura de negocio más débil. Antes de producción conviene añadir tests de comportamiento real para esos tres.

### 🟡 3. `recruitment` con poco manejo de errores

7 herramientas pero solo **4 bloques try/except** en 360 líneas (procesa CVs, crea candidatos/posiciones). El procesamiento de CV y la actualización de estado son puntos donde un fallo del LLM o del parseo debería degradar con gracia. Revisar cobertura de errores antes del piloto.

### 🟡 4. `compliance` es asesoría fiscal de solo-lectura

`check_boe_news`, `fiscal_query`, `check_fiscal_deadlines`. Da respuestas fiscales al usuario, así que el riesgo no es técnico sino de **exactitud**: una respuesta fiscal errónea es un problema de producto. Recomendado validar las salidas con casos reales antes de exponerlo.

### ⚪ 5. Detalles menores
- **`services/assets`**: no es un servicio de código, son imágenes estáticas — pero `escudo_espana.png` y `escudo_espana2.png` son **archivos de 0 bytes** (vacíos). Si se usan en PDFs oficiales, romperán el render. `sepe_logo.png` está bien.
- Servicios deliberadamente pequeños (`client_portal` 73 L, `tenant` 96 L, `i18n` 82 L, `observability` 94 L) son infra/transversales y no necesitan más profundidad.

---

## Capa de servicios — profundidad (referencia)

Servicios con mucho músculo (respaldan a los agentes): **billing 2.989**, **workflow 2.998**, **ai 2.792**, **documents 2.534**, **pdf_reports 3.311**, **pdf 2.457**, **reports 2.042**, **hr 2.031**, **sales 1.775**, **aeat 1.479**, **migration 1.139**, **inventory 1.067**, **integration 1.049**, **ocr 991**. La capa de servicios **no es el cuello de botella**: está más desarrollada que varios agentes.

---

## Recomendación para continuar hacia piloto

**Sí, la base tiene profundidad para continuar.** El proyecto puede ir a piloto con los módulos ✅. Antes de abrirlo a usuarios reales, atender en este orden:

1. **Decidir el rol de marketing**: o se asume como "asistente de contenido" (y se comunica así), o se le da modelo de datos + persistencia. Es el único módulo claramente por debajo del listón.
2. **Reparar los 2 PNG de escudo a 0 bytes** si se usan en documentos oficiales.
3. **Añadir tests de negocio** (no solo smoke) a crm, compliance y recruitment.
4. **Reforzar manejo de errores** en recruitment (procesado de CV).
5. **Validar exactitud fiscal** de compliance con casos reales.

Todo lo demás —billing, hr, banking, accounting, documents, excel, email, orchestrator, workflow— tiene profundidad de producción.

---

## Acciones aplicadas (7 jun 2026) — puntos 2 a 5

Marketing (punto 1) queda como pendiente mayor: su rol previsto era desarrollar
campañas, email marketing y automatización a redes (posts automáticos, WhatsApp),
y nunca se implementó. Requiere proyecto propio (modelo de datos + canales).

**2 · Bug del logo SEPE (más grave que los PNG vacíos).**
Al revisar los assets se descubrió que `escudo_espana*.png` (0 bytes) son archivos
**muertos**: no se referencian en ningún sitio, así que no rompen nada. El problema
real estaba en `services/hr/queries.py`: `_load_sepe_logo_b64()` buscaba el logo en
dos rutas inexistentes (`services/hr/assets/` y `routes/assets/`), cuando el archivo
está en `services/assets/`. Resultado: el logo SEPE **nunca** se incrustaba en las
nóminas. Corregido añadiendo la ruta real como primer candidato.

**3 · Manejo de errores en recruitment.** `agents/recruitment/tools.py`: se añadió
validación de UUID con mensaje claro (`_parse_uuid`) y degradación con gracia en las
6 tools. El punto crítico era `process_cv`: ahora captura por separado fallo de
lectura del PDF (archivo no encontrado / corrupto), fallo del LLM al estructurar y
fallo al guardar — devolviendo un mensaje accionable en vez de tumbar al agente.

**4 · Tests de negocio.** Tres archivos nuevos que ejercitan lógica real (no smoke):
`tests/test_recruitment_business.py`, `tests/test_crm_business.py`,
`tests/test_compliance_business.py`. Cubren validación de entrada, degradación de
errores y el safeguard CONT.0 de compliance (no inventar fechas si el calendario
AEAT no carga). *Nota: no se pudieron ejecutar en este entorno (sandbox sin la BD de
test); conviene correr `pytest` en local para confirmarlos.*
Hallazgo lateral del test de CRM, **ya corregido**: el vocabulario de etapas era
inconsistente — `create_opportunity` aceptaba `negotiation` y
`update_opportunity_stage` no. Unificado en una única constante `VALID_STAGES`
(5 etapas: new, qualified, proposal, won, lost) que coincide con el embudo del
frontend y el tipo de `crm.ts`. Test de regresión añadido para que no vuelva a
divergir.

**5 · Exactitud fiscal de compliance.** Revisado `_CONTEXTO_NORMATIVO` (la única
fuente que el LLM usa para responder consultas fiscales). El diseño es bueno: los
vencimientos salen del calendario AEAT en vivo, no hardcodeados, con safeguard
anti-fechas-caducadas. Pero el bloque estático tenía **dos errores**, ya corregidos:
- *Modelo 111*: decía "mismos plazos" que el 303 → su 4T vence el **20 de enero**, no
  el 30. Aclarado.
- *Factura electrónica B2B*: decía "pendiente de reglamento" → **desactualizado**. Ya
  existe el **RD 238/2026** (BOE 31-mar-2026); calendario desde 1-oct-2026, obligación
  a 1 año para >8M€ y 2 años para el resto. Actualizado.
