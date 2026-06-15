# Reestructuración de módulos a medias

> Backlog **vivo** de módulos que están incompletos o cuyo **concepto** hay que
> rehacer. Cada entrada está aterrizada en código real (file:line) para que sea
> accionable. Se trabaja *poco a poco*, validando cada cambio con el ciclo de
> [`iteraciones-cliente-real.md`](iteraciones-cliente-real.md) (un flujo no está
> hecho hasta que hay un test que lo replica).
>
> Fuente: investigación de código (workflow `investiga-modulos-a-medias`, 2026-06-15).

Prioridad sugerida: **1) Modelos AEAT** (riesgo fiscal/legal) · **2) Marketing**
(bugs que engañan al usuario) · **3) Gestoría documental** (mejora de UX, ya hay base).

---

## 1. Gestoría / generación documental → hacerla CONVERSACIONAL

**Objetivo:** que en RRHH el usuario **no rellene un prompt**. El LLM **entrevista
paso a paso** (p.ej. contrato de trabajo → tipo de jornada, horas semanales, salario,
duración, convenio…) y construye el documento.

### Estado actual
Coexisten dos flujos:
- **(A) One-shot (RRHH)** — el usuario elige `doc_type` y escribe instrucciones libres
  en un textarea, o teclea una frase NL. `frontend/.../rrhh/documentos/page.tsx:76-81`
  + `_hooks/useHRDocumentos.ts:9` (`parseNLIntent` por regex, frágil) →
  `POST /hr/documents/generate` → `services/hr/commands.py:133` (`generate_document`)
  hace **una sola** `llm.ainvoke` sin diálogo (`commands.py:161-181`).
- **(B) Conversacional (ya existe)** — `services/documents/contracts_interview.py:45`
  (`run_interview`): el LLM pregunta **una cosa por turno** y al emitir
  `=== CONTRATO FINALIZADO ===` devuelve el documento. Expuesto en
  `routes/documents.py:120` (`POST /documents/contracts/interview`) y consumido por
  `components/documentos/ContractWizard.tsx` — **pero solo en `/documentos`, no en RRHH**,
  y solo cubre 4 tipos genéricos (`contracts_interview.py:18-23`: servicios/trabajo/nda/alquiler).

> **La pieza ya está construida** (B). El trabajo es **portarla a RRHH** y enriquecerla.

### Plan
1. **Backend**: añadir `POST /hr/documents/interview` análogo a `run_interview`, que
   entreviste por `doc_type` laboral (contrato, despido, finiquito, certificado, adenda
   — `services/hr/queries.py:385` `DOC_TYPE_LABELS`).
2. **Slot-filling por tipo**: definir, por documento, la **lista de campos requeridos**
   que la entrevista debe cubrir antes de finalizar (contrato de trabajo: NIF, puesto,
   jornada completa/parcial, horas, salario bruto, duración, fecha inicio, convenio).
   Hoy el prompt de contratos es genérico (`contracts_interview.py:26-42`) y no pregunta
   estos campos.
3. **Señal de fin estructurada**: no depender solo del marcador de texto
   (`FINAL_MARKER`, `contracts_interview.py:80`, frágil — el modelo puede emitirlo antes
   de tiempo). Devolver `done` + slots completados de forma estructurada.
4. **Frontend**: sustituir el textarea/barra-NL de `rrhh/documentos` por un chat tipo
   `ContractWizard.tsx`; eliminar `parseNLIntent` (regex) una vez exista el wizard.
5. **Pipeline común**: el documento conversacional debe entrar por el **mismo** flujo de
   aprobación + folio (`commands.py:222` `_next_doc_number`) + PDF
   (`GET /hr/documents/{id}/pdf`, `hr_documents.py:81`).

### Flujos a probar (→ tabla de iteraciones)
- Contrato de trabajo conversacional completo (preguntas → documento sin placeholders → draft → aprobar → PDF).
- Despido / finiquito / certificado conversacionales.
- Reiniciar entrevista a medias (estado limpio) y reanudar.

---

## 2. Marketing → corregir bugs que **engañan al usuario**

**Contexto:** los 52 tests de marketing pasan, pero **solo cubren la capa de servicio**
(`publish_post`, tokens, métricas). Los bugs reales están en los **handlers HTTP y el
frontend**, sin test → por eso "no saltan". (Por eso este módulo es candidato nº1 a
escribir tests de flujo real.)

### Bugs confirmados (prioridad)
| # | Sev | Bug | Evidencia | Arreglo |
|---|-----|-----|-----------|---------|
| 1 | 🔴 crit | **"Publicar ahora" NO publica**: crea un draft y dice "publicado" | `TabCrear.tsx:40-50` llama solo a `posts.create({scheduled_at: undefined})`, nunca a `posts.publish()` | Tras `create()`, llamar `posts.publish(id)` y reflejar el `status` real (o endpoint atómico create+publish) |
| 2 | ✅ **hecho** | ~~publish devuelve 200 aunque falle~~ → ahora 502 con `error_message` | `routes/marketing.py` inspecciona el `PublishResult` y propaga 502 si `!ok` | blindado: `backend/tests/test_e2e_marketing_publish.py` (2026-06-15) |
| 3 | ✅ **hecho** | ~~Email-marketing reporta 0 fallos siempre~~ → cuenta `failed` bien | helper `send_failed()` en `email/sender.py`; `send_campaign` inspecciona el resultado de `send_email` | blindado: `test_email_campaign_worker.py::test_send_campaign_sin_credenciales_cuenta_fallos` (2026-06-15) |
| 4 | ✅ **hecho** | ~~OAuth fallo de perfil → cuentas `'unknown'`/duplicadas~~ → aborta con error | el callback hace `return _popup_html(False, …)` si `_fetch_profile` falla o no da id; no persiste nada | blindado: `test_marketing_oauth_callback.py` (2026-06-15) |
| 5 | 🟡 med | IG `impressions` deprecado → insights 400 → métricas a 0 | `metrics.py:89-92` pide `impressions` en Graph v18 (Meta lo retiró) | Usar `reach`/`views`, alinear versión de API |
| 6 | 🟡 med | `image_generation`/`image_search` **hardcodean** el host de Render | `image_generation.py:44`, `image_search.py:41` | No hardcodear; sin proxy/key → `None`/503 controlado |
| 7 | 🟡 med | `generate_plan`: lógica de negocio gruesa en la ruta (fallback + "red de seguridad") | `routes/marketing.py:524-687` (parte de las 16 mutaciones, D5-N3) | Mover a `services/marketing/plan_builder.py` |
| 8 | 🟡 med | PKCE de Twitter en memoria de proceso → rompe en multi-worker/reinicio | `oauth.py:27-50` (`_pkce_store` dict) | Persistir verifier por `state` en DB/redis |
| 9 | ⚪ low | `publish_batch` marca `failed` sin reintento transitorio; `_decode_state` no valida plataforma | `routes/marketing.py:752`, `oauth.py:58-64` | Backoff como el scheduler; validar plataforma soportada |

### Flujos a probar
- Conectar red (OAuth) → cuenta "Conectado" sin duplicados/`unknown`.
- "Publicar ahora" → se publica de verdad o muestra error real (no draft fantasma).
- Programar → scheduler publica → `scheduled→published`; ante 5xx, backoff.
- Email-marketing con fallo de envío → resumen cuenta `failed>0`.

---

## 3. Modelos fiscales AEAT → entregar el modelo **OFICIAL**

**Aclaración:** el PDF actual **no lo genera un LLM** — es **reportlab** dibujando un
**borrador** que imita la estética AEAT. Pero el problema es el que señalas: **no es el
modelo oficial** y va sellado "BORRADOR — NO VÁLIDO PARA PRESENTACIÓN".

### Estado actual
- `services/pdf_reports/_fiscal_modelo303.py:198` (y `_fiscal_modelos.py:138-453` para
  130/111/190/347/390/115/349/200/100) dibujan el PDF con reportlab; sello BORRADOR
  (`_fiscal_modelo303.py:55`) y pie "No sustituye la presentación oficial".
- **No hay XSD oficiales**: `services/aeat/xsd/` solo tiene esquemas Verifactu/SII →
  `xsd_validation.py:29-32` hace `return []` (validación **omitida en silencio**) si no
  hay XSD del modelo.
- Los XML se **autodeclaran no oficiales** con valores inventados/hardcodeados
  (`modelo_303_xml.py:42` `tipo='auxiliar'`; `presentacion/asistida.py` usa un namespace
  inventado). La presentación "asistida" abre un deep-link a Sede para importar a mano.
- `services/aeat/xades_signer.py` **existe pero no se invoca** → no hay presentación
  telemática real.
- UI: `ModelosPanel.tsx:184` etiqueta "Descargar el Modelo X en PDF" → puede confundirse
  con el oficial.

### Plan (elegir vía)
- **Vía A — PDF oficial rellenable (AcroForm)**: depositar en el repo el formulario
  **oficial** de la AEAT (PDF con campos), y rellenarlo **por nombre de campo** con los
  importes calculados (`build_modelo_303_data`). Entregable: PDF oficial para imprimir/
  presentar en Sede.
- **Vía B — Presentación telemática**: generar el **fichero que la Sede acepta** para
  predeclaración/import de cada modelo (namespace + estructura **oficiales**, con XSD
  real depositado en `services/aeat/xsd/`), firmar con `xades_signer.py` (XAdES) y
  presentar. Es el camino completo pero mayor.

### Pasos transversales (ambas vías)
1. Conseguir y versionar los **artefactos oficiales** (PDF AcroForm y/o XSD) por modelo.
2. Hacer que la **ausencia de XSD sea un fallo explícito**, no un pase silencioso
   (`xsd_validation.py`).
3. Mientras no esté el oficial: etiquetar la UI claramente como **"Borrador (no oficial)"**
   (`ModelosPanel.tsx`) para no inducir a error.

### Flujos a probar
- Modelos → 303 trimestre con datos → descargar → **¿es el modelo oficial?**
- Presentación asistida 131/200 → XML → Sede AEAT → Importar → **¿lo acepta?**

---

## 4. Otros módulos sin cobertura de flujo real (riesgo)

La investigación de cobertura detectó dominios completos **sin ningún test de usuario**
(además de los de arriba). Alimentan la tabla de [`iteraciones-cliente-real.md`](iteraciones-cliente-real.md):

| Dominio | Estado | Gap |
|---|---|---|
| **Veri\*factu / `/verify`** | 🔴 | E2E **legalmente obligatorio** en `test.skip` (`frontend/e2e/happy-path.spec.ts:18-34`); el funcional no toca `/verify` |
| **Modelos AEAT** (18 endpoints) | 🔴 | 0 tests (`modelos_aeat.py`) |
| **Presentación AEAT** (10 endpoints) | 🔴 | 0 tests (`aeat_presentation.py`) |
| Tesorería + SEPA (pain.001/008) | 🟠 | 0 tests (`treasury.py`) |
| Cobros/recobro | 🟠 | 0 tests (`collections.py`) |
| Inventario multi-almacén | 🟠 | solo stock de producto, no almacenes (`warehouses.py`) |
| Importación masiva (onboarding datos) | 🟠 | 0 tests (`import_bulk.py`) |
| Scanner QR / portal cliente / onboarding wizard | 🟡 | 0 tests |

> El único E2E de usuario real hoy es `tasks/test_funcional_completo.py` (20 fases) —
> y **no** cubre marketing, Veri\*factu ni AEAT. Empezar por Veri\*factu (legal) y AEAT.

---

## Registro de avances

<!-- A medida que se reestructure cada módulo, anotar aquí el commit/PR + el test que lo blinda -->
