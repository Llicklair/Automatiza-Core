# Auditoría E2E de agentes con LLM real — 2026-06-23

**Método.** Se iteró el sistema **una orden NL a la vez** contra el orquestador real
(provider `claude_code` = `claude` CLI local, sin API key) sobre el tenant seguro
**Demo Masivo** (`c505879e-…`). Runner: [c:/tmp/run_order.py] (traza las tools que
el LLM invoca de verdad, parcheando `BaseTool.invoke/ainvoke`). Cada orden ≈ 30–120 s.
Varios subagentes por ronda (uno por dominio). Verificación E2E real (escritura →
relectura). NO se usó `ENVIRONMENT=testing` (eso fuerza un MockChatModel que no razona).

> **Corte de sesión:** a mitad de la Ronda D se agotó la cuota de la suscripción
> Claude Code (`session limit · resets 2:30am Europe/Madrid`). El runner y el escritorio
> comparten ese mismo pozo de tokens. **marketing / email / excel y el test de
> orquestación multi-paso quedan pendientes** hasta el reset.

## Veredictos por dominio

| Dominio | Veredicto | Routing | Lecturas | Escrituras E2E |
|---|---|---|---|---|
| **banking** | ✅ PASS | 3/3 ✓ | check_balances, list_transactions, financial_summary, reconcile_transactions | (read-only) — multi-intención abre 2 tools |
| **hr** | ✅ PASS | 3/3 ✓ | list_employees (25), list_payrolls (30) | ✓ propose_schedule generó borrador con fechas reales |
| **documents** | 🟡 PASS c/peros | 2/3 ("buscar"→billing) | list_tenant_documents (482), classify_document | n/a · sin búsqueda semántica real · tope 200 docs como conteo |
| **crm** | 🟡 PARTIAL | 3/3 ✓ | list_opportunities (401), search_client | ✗ `create_opportunity` nunca disparó (exige cliente preexistente) |
| **billing** | 🟡 PARTIAL | 1/3 | list_invoices, list_albaranes | ✗ "crea albarán"→inventory (no-op); "busca cliente"→excel |
| **recruitment** | 🔴 PARTIAL/FAIL | reads ✓, write→crm | list_positions | ✗ misrouteado + **falso éxito** |
| **inventory** | 🔴 FAIL | 3/3 ✓ | find_products, get_product_stock | ✗ `create_product` = **0 tool-calls** (determinista 2/2) |
| **accounting** | 🔴 FAIL | 1/3 | — (sus tools nunca disparan) | ✗ "libro diario"→0 tools + **excusa MCP alucinada** |
| **compliance** | 🔴 FAIL | 0/3 | — | ✗ inalcanzable; `report` **fabrica** informe + **falso éxito** |
| **excel** | 🟡 PARTIAL | "facturas a Excel"→billing | export_erp_data (.xlsx real) | ⚠ billing exporta **.CSV diciendo "Excel"** y capa a 50 filas en silencio |
| **email** | 🟡 PARTIAL | read ✓; "busca…factura"→billing | check_inbox (demo) | ✗ `search_email` inalcanzable; disclaimer DEMO en campo `error` con success=true |
| **marketing** | 🔴 FAIL | 3/3 ✓ | sin tool `list_campaigns` (responde en prosa) | ✗ `create_campaign` NUNCA dispara; lee catálogo+redes y **fabrica** "campaña preparada" |
| **orquestador** | 🟢🟡 mixto | multi-paso ✓ (coordinator, 2 pasos, **`create_opportunity` SÍ dispara**); chitchat ✓ (chat, no-dispatch) | — | ⚠ ambigua "X y Y" (sin "luego") **colapsa a 1 dominio** y descarta la otra mitad |

## Causas raíz (con referencia a código)

### A. Clasificador insensible a tildes — `classifier.py:333`
`intent_lower = intent.lower()` **no normaliza diacríticos**. Keywords acentuadas
(`"pérdidas y ganancias"`, `"nómina"`, `"declaración"`, `"añade"`, `"amortización"`)
fallan en silencio cuando el usuario omite tildes (lo normal). Caso real: "Dame el
resumen de **perdidas** y ganancias" → la strong de accounting no casó y ganó el
genérico `"dame el resumen"`→**report**. Fragilidad de alto impacto.

### B. Keywords genéricos sobre-capturan — `classifier_data.py`
`"datos"`→excel (l.134), `"venta"` como substring de "ventas"→crm (l.77), `"dame el
resumen"`→report (l.251), `"saldo de la cuenta"`→banking strong (l.301). Vencen al
dominio correcto: "busca un **cliente**, dame sus **datos**"→excel; "puesto de trabajo
para **ventas**"→crm; "saldo de la **cuenta** de tesorería"→banking (en vez de
accounting `get_account_balance`).

### C. Huecos de cobertura — `classifier_data.py`
- `"cliente"` a secas NO es keyword de crm/billing (solo "X cliente" compuestos).
- recruitment exige `"puesto abierto"/"puesto vacante"`; "puesto de trabajo" no casa.
- compliance solo cubre **modelos AEAT** ("modelo 303", "hacienda"…); "auditoría",
  "cumplimiento", "registro de auditoría" no tienen hogar → caen a `report`/`chat`.
  (El agente compliance **existe** y está cableado — `dispatchers/compliance.py`,
  VALID_DOMAINS l.73 — pero es **inalcanzable** para intents de auditoría.)

### D. El match keyword "confiado-pero-erróneo" cortocircuita al LLM — `classifier.py:399`
El clasificador LLM (más listo) **solo** corre si las keywords devuelven `"unknown"`.
Un acierto keyword equivocado nunca se revisa, y **se cachea 24 h** por tenant
(`classify:`). Un error se vuelve pegajoso.

### E. `report` fabrica y miente éxito — `dispatchers/reports.py:30`
`_dispatch_report` **ignora el intent** (solo extrae mes/año), SIEMPRE arma un informe
financiero desde BD y devuelve `success: True` (l.225). Sin guard de relevancia. Por eso
una orden de "auditoría" misrouteada produce un informe financiero falso, y el agente
`summary` lo **re-etiqueta** como "Registro de Auditoría". Alucinación + falso éxito.

### F. El guard de fallo es bueno pero incompleto — `dispatchers/_outcome.py`
`detect_failure` (acción pedida + 0 tools → fallo) **sí** atrapa los no-op de "crea"
(billing/accounting correctamente `success=false`). Pero le faltan:
- `"abre"/"abrir"` en `_ACTION_INTENT_KW` (l.26) → "**Abre** un puesto" no se trata como
  acción → el no-op de recruitment pasa como éxito.
- `"no dispongo de"` en `_TOOL_REFUSAL_PHRASES` (l.49) → el rechazo "No dispongo de
  herramientas de RRHH" no se detecta.
- **`tool_was_invoked` es demasiado grosero (l.60)**: devuelve True si dispara
  *cualquier* tool, incluida una de LECTURA. Caso marketing-create: el LLM disparó
  `get_product_catalog` (lectura) y luego **fabricó** "campaña preparada" → 0 writes pero
  el guard no salta (any-tool=True). Para un intent de ACCIÓN debe exigir que dispare una
  tool de **escritura** (create/update/…), no cualquiera. Es el agujero del "phantom-write".

### G. Las tools SÍ están enlazadas; falla la **elicitación** del provider — `accounting/agent.py:23-59`
accounting enlaza sus 7 tools y hace `bind_tools` correctamente. El fallo es que el
provider `claude_code` hace **tool-calling basado en prompt** (`<<<TOOL_CALL>>>`), no
function-calling nativo, y para varios agentes/intents (accounting-list, inventory-create,
crm/billing-create) el modelo **no emite el sentinel** y devuelve prosa (a veces una
excusa MCP inventada). banking/hr/documents elicitan bien → no es un fallo universal del
provider, es **no determinista por agente/prompt**. Es el riesgo #1 porque el **escritorio
empaqueta exactamente este provider**.

### H. (META) CI no ejerce el camino que falla
Los tests corren con `ENVIRONMENT=testing` → **MockChatModel**, que devuelve tool-calls
de forma determinista. CI **nunca** ejercita la elicitación prompt-based de `claude_code`
que el escritorio envía y que falla en producción. Toda esta clase de bugs es **invisible
a la suite**. Falsa confianza verde.

## Patrón transversal (resumen ejecutivo)
- **Lecturas:** sólidas en casi todos los dominios (datos reales, tools correctas).
- **Escrituras/creación:** frágiles — por **misrouting** (a un agente sin la tool) o por
  **no-emisión de tool-call** del provider. Solo se probó una escritura E2E limpia (hr
  propose_schedule).
- **Routing** es el cuello de botella nº1 (causas A–D). `report` como cajón-de-sastre
  (E) y los huecos del guard (F) convierten misroutes en **falsos éxitos peligrosos**.

## Arreglos propuestos (priorizados)
1. **[Alto/barato] Normalizar tildes** en `classifier.py` antes de matchear (NFKD + quitar
   combiners; o `unidecode`). Mata la causa A de un plumazo.
2. **[Alto] Guard de relevancia en `report`** (causa E): si el intent no es financiero
   (auditoría/cumplimiento/etc.) → no fabricar; devolver `success=False` o re-rutar.
3. **[Alto] Completar `detect_failure`** (causa F): añadir `"abre/abrir"` a acciones y
   `"no dispongo de"`/`"no cuento con"` a rechazos.
4. **[Medio] Subir el listón del keyword-classifier** (causas B–D): que un match de
   score 1 con runner-up genérico delegue al LLM en vez de resolver; quitar `"datos"`
   de excel; añadir cobertura crm("cliente"), recruitment("puesto de trabajo"),
   compliance("auditoría/cumplimiento").
5. **[Estratégico] Cerrar el gap de CI** (causa H): un smoke E2E con el provider real
   (claude_code) sobre un puñado de órdenes write, separado de la suite mock.
6. **[Investigar] Elicitación de writes bajo claude_code** (causa G): ¿se puede forzar
   `tool_choice`/few-shot del sentinel para creates? Reproducir accounting-list aislado.

### I. Conjunción "X y Y" (sin secuencia) colapsa a un dominio — `classifier.py:177-208`
La descomposición multi-paso solo se dispara con `_MULTI_STEP_CONNECTORS` (" y luego ",
" y después "…). Una pregunta conjuntiva normal — "¿Cuánto he facturado **y** cuántos
empleados tengo?" — no tiene connector de secuencia → no va a `coordinator`; "facturado"
gana billing y la mitad de "empleados" se **descarta sin avisar**. Falta tratar la "y"
conjuntiva (no solo la secuencial) como señal de posible multi-dominio.

### J. Falso éxito de formato/fuente (variante de E/F)
- excel: "facturas a Excel"→billing emite un **.CSV** y el resumen dice "exportadas a
  Excel" (mentira de formato), capando a 50 filas en silencio.
- email: "busca correos…factura"→billing busca en el **gestor documental** y lo presenta
  como resultado de bandeja de entrada (mentira de fuente).
El sistema afirma haber hecho lo pedido con un artefacto del tipo/fuente equivocados.

### ✅ Positivo a preservar — el camino `coordinator` es el más fiable para escrituras
El único create que disparó limpio (`create_opportunity`) fue **vía coordinator con la
acción nombrada en el plan** ("crea … y luego …", 2 pasos). El single-shot del mismo
dominio NO disparó. Pista: **nombrar la acción en un paso del plan** elicita la tool mucho
mejor que dejar al agente decidir en una sola pasada. Coste: lento (~257 s multi-paso).

---

## Estado: survey COMPLETO (14 comportamientos, 9 dominios + orquestador)
Scoreboard: **PASS** banking, hr · **PASS c/peros** documents, orquestador(multi-paso/chitchat)
· **PARTIAL** crm, billing, email, excel · **FAIL** inventory, accounting, compliance, marketing.
Para reproducir una orden: `"$DESKPY" c:/tmp/run_order.py "<orden>"` (DESKPY = python
embebido del escritorio). OJO: agota la cuota de la suscripción Claude Code (la comparte
el escritorio); ~15-20 órdenes la tumban hasta el reset.

---

## Fixes aplicados + verificados (2026-06-23)
Tres arreglos (working tree, sin commit) — verificados offline (27 casos de regresión de
los tests existentes + 7 nuevos, todos verdes) y **confirmados E2E con LLM real**:

| # | Fix | Fichero | Confirmación E2E |
|---|---|---|---|
| 1 | `detect_failure`: +verbos (`abre/abrir`, `publica/publicar`), +frase (`no dispongo de`), y exige tool de **escritura** (no cualquiera) para intents de acción → mata el phantom-write | `dispatchers/_outcome.py` | "crea campaña" → `success=False`/failed (antes true) |
| 2 | Clasificador **tildes-tolerante** (NFKD): `_keyword_classify` auto-normaliza; keywords se normalizan en cada comparación. Tablas intactas (las parsea el audit script) | `classifier.py` | "balance de situacion" (sin tilde) → `accounting` + tools disparadas (antes misrouteo) |
| 3 | Guard de relevancia en `report`: rechaza intents de auditoría/cumplimiento/GDPR en vez de fabricar un informe financiero re-etiquetado | `dispatchers/reports.py` | "registro de auditoría" → `success=False` con mensaje claro (antes informe falso true) |

Pendiente (no incluido, requiere decisión de producto): mejorar la precisión del keyword-classifier
(causas B–D), elicitación de writes bajo `claude_code` (causa G), conjunción "X y Y" (causa I),
y el gap del mock en CI (causa H — añadir un smoke E2E con provider real).
