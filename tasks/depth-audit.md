# Audit de profundidad de módulos — POV usuario (2026-06-09)

Complementa `pilot-readiness.md` (que mira infra/onboarding). Esto mira, dominio
a dominio, **cuánta profundidad real** tiene cada uno y **qué falta para que una
PYME/asesoría saque valor**.

## Método y caveat
13 dominios auditados (6 subagentes + marketing que ya conocíamos). **Los
reportes de subagentes sobre-estiman stubs**: a veces solo miran la capa `tools.py`
del agente y se pierden el `service`. Ejemplo verificado: el agente dijo "banking
no persiste conciliación / sin PSD2 real" — **falso**: `services/banking/service.py:141`
persiste (`status=reconciled`, `invoice=paid`) e `integrations/psd2.py` tiene
`NordigenClient` (GoCardless) real. Conclusión: trata los ratings como guía, no
dogma; lo "DEMO" suele ser *fallback sin credenciales*, no código falso.

## Madurez por dominio

| Dominio | Rating | Lo real | Gap nº1 para producción |
|---|---|---|---|
| **billing** | Beta→Prod | Verifactu (hash-chain), ACID, PDF, OCR facturas recibidas | Facturas recurrentes (modelo existe, sin tool/job) |
| **hr / nóminas** | **Prod (core)** | Tasas SS 2025-26 reales, IRPF, cuota solidaridad, nómina PDF legal | Aprobación masiva (UI) + simulación previa |
| **inventory** | Beta+ | Persistencia real, multi-almacén, lotes FEFO, movimientos | Venta/POS→decremento stock (no enlazado) |
| **crm** | Beta→Prod | CRUD completo, audit de actividades, multi-tenant | Enlazar email↔actividad; recordatorios/tareas |
| **banking** | Beta | PSD2 real (Nordigen) + conciliación persiste; demo si sin creds | Onboarding de credenciales + señalizar demo-vs-live; exponer SEPA |
| **fiscal / AEAT** | Beta | 303/390/111/190/347 reales (Decimal); UI /impuestos | Envío real a SEDE (hoy dry-run; XAdES con stub fallback) |
| **documents** | Beta | OCR facturas real, clasificación por reglas, embeddings | Búsqueda semántica generada pero **no expuesta** |
| **excel** | Beta | Export/import real (openpyxl, 6+ entidades) | Export de pedidos/POS + import de transacciones |
| **rag** | Beta | Embeddings reales (bge-m3) + fallback keyword | Escala (sin pgvector → coseno en Python ~5k chunks) |
| **email** | Beta | Gmail + IMAP/SMTP reales; demo si sin creds | UX demo-vs-live + drafts persistentes + search |
| **recruitment** | Beta | Parseo CV real (LLM); scoring **deshabilitado a propósito** (AI Act) | Entrevistas/notas + audit de decisión + consentimiento GDPR |
| **accounting** | Alpha→Beta | CRUD asientos real, P&L, activos | **Factura→asiento automático** (billing↔accounting roto) |
| **marketing** | Beta | (esta sesión) refresh+cifrado tokens, FB Pages, IG Graph API, reintentos | Verificación end-to-end contra app Meta real |

## Los 4 temas transversales (los bloqueantes de VERDAD)

1. **Degradación por falta de config, no por falta de código.** banking, email
   (y la IA, ver pilot-readiness #1) tienen implementación real que cae a DEMO sin
   credenciales. El trabajo real no es "construir", es: (a) **onboarding de
   credenciales** y (b) **señalizar demo-vs-live** en UI (hoy se confunden). No son stubs.

2. **Integración cross-dominio = el mayor valor sin construir.** Cada dominio
   funciona **aislado**; falta el pegamento end-to-end que una PYME espera:
   - **factura → asiento contable** (billing→accounting): hoy manual. *El gap más caro.*
   - **venta/POS → movimiento de stock** (sales→inventory): inventario en paralelo, no en vivo.
   - **conciliación → estado factura**: ✅ ya existe (corrección al agente).
   - **email enviado → actividad CRM**: no se registra.

3. **Profundidad fiscal real.** Cálculo de modelos sólido, pero el *último tramo*
   falta: envío real a SEDE (dry-run por defecto + XAdES con stub si falta `xmlsec`),
   casillas avanzadas del 303, ajustes fiscales del 200, 130/115/349 parciales.

4. **Búsqueda semántica de documentos**: embeddings generados pero sin endpoint/UI
   para buscar. Valor RAG a medio cablear.

## Decisión #3 — ¿fiscal como dominio propio?

**Matiz clave que cambia la respuesta:** hoy los modelos AEAT **NO se generan vía
tools del agente** — se construyen por rutas API + la UI `/impuestos`. El agente
`compliance` solo tiene 3 tools LLM (deadlines, query, BOE). Así que:

- El **peso técnico** justifica un dominio (9 builders + pipeline firma/SEDE), PERO
- promover "fiscal" a dominio del Coordinador **solo aporta** si quieres generación
  **conversacional** ("genérame el 303 del Q2 y preséntalo"). Si el flujo fiscal va
  a seguir siendo UI-driven (wizard en /impuestos), crear el dominio es overhead.

**Recomendación:** decisión de producto, no técnica. Si el roadmap es "el usuario
pide impuestos al asistente" → promover (separar de compliance + envolver los
builders como tools). Si es "wizard guiado en /impuestos" → dejarlo en services+UI
y solo asegurar que compliance puede *responder* sobre fiscal (ya lo hace vía RAG).
Mi voto pragmático: **no promover aún**; primero cerrar el envío real a SEDE (que es
el bloqueante de valor), y promover a dominio cuando exista la intención conversacional.

## Qué construir para producción (priorizado por valor/esfuerzo)

1. **factura→asiento automático** (billing→accounting). Alto valor, esfuerzo medio.
2. **Onboarding + señalización de credenciales** (IA, banking, email). Alinea con pilot-readiness #1.
3. **Envío real AEAT a SEDE** (quitar dry-run por defecto tras validar cert + XAdES sin stub).
4. **venta/POS → stock** (sales→inventory).
5. **Exponer búsqueda semántica de documentos** (endpoint + caja de búsqueda).
6. **Facturas recurrentes** (job programado) + **conciliación de pago** (marcar pagada).

> Nota: casi nada de esto es "features nuevas" — es **cablear lo que ya existe** entre
> dominios y cerrar el último tramo (config, envío, exposición). El producto tiene
> profundidad; le falta *continuidad*.
