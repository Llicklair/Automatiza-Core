# PLAN — Los 4 rojos (ALTA · fiscal/auth · decisión humana)

Fecha: 2026-06-27. Verificado contra código real (no especulación del inbox).
Zona NO-EDIT: el loop NO los parchea. Este plan es para que TÚ apruebes/rechaces
cada uno. Esfuerzo = tamaño del cambio; Riesgo = de romper algo si se hace mal.

---

## ROJO #1 — Doble-ejecución de aprobación en retry del orquestador
**Severidad:** ALTA-fiscal · **Esfuerzo:** medio-alto (refactor) · **Riesgo del fix:** alto

**Causa raíz (confirmada):** `tasks_orchestrator.py:108-126`. `resume_orchestrator`
usa `IdempotencyGuard`: marca en éxito (`mark_executed`, línea 121) pero en excepción
**libera el guard** (`guard.release`, línea 125) y reintenta 3× (`_retry`). El guard es
a nivel del NODO `resume_orchestrator` entero, no de la acción financiera irreversible
dentro de él. Si la factura/asiento/email YA se ejecutó y un paso POSTERIOR del resume
lanza → el retry re-ejecuta la MISMA aprobación. Además `PendingApproval` nunca se marca
"consumido" (el `WHERE status='approved'` que pretende dar idempotencia no funciona
porque el status nunca cambia).
**Efecto:** doble asiento contable / doble factura / doble email al cliente.

**Opciones de fix:**
- (a) Marcar `PendingApproval` como `consumed` al ejecutar. *Problema:* un retry tras
  éxito no halla "approved" y marca la tarea FAILED siendo exitosa (falso negativo).
- (b) **[recomendada]** Idempotencia a nivel de la PARTE IRREVERSIBLE, no del nodo:
  guard propio sobre `_execute_from_approval`/`_create_invoice_from_approval` con clave
  estable (approval_id) que NO se libera en excepción posterior. Separa
  "execute-once-guarded" de "graph-resume-reintentable".
**Decisión que necesito de ti:** ¿semántica (a) o (b)? Es el camino de coordinación más
crítico + fiscal; quiero tu OK al diseño antes de tocar.

---

## ROJO #2 — SEPA: remesa duplicada en reintento
**Severidad:** ALTA-fiscal · **Esfuerzo:** bajo-medio · **Riesgo del fix:** medio

**Causa raíz (confirmada):** `treasury.py:97 generate_pain001`. `SepaRemittance.msg_id`
(`models/treasury.py:27`) es `String(35)` con **índice NO único** (la migración
`0052` crea `ix_sepa_remittances_msg_id`, no UNIQUE). Cada llamada genera `msg_id` uuid4
nuevo → dos POST concurrentes o un reintento de frontend tras timeout crean DOS remesas
→ **dos XML SEPA distintos al banco para el mismo pago = doble cobro/transferencia**.
Agrava: `download_pain001` (`treasury.py:195`) **llama a `generate_pain001`** → descargar
el XML persiste una 2ª remesa (inbox MEDIA aparte).

**Fix propuesto:**
1. Aceptar `Idempotency-Key` del cliente (header) → si ya existe remesa con esa clave
   para el tenant, devolver la existente en vez de crear otra.
2. `download_pain001` debe LEER una remesa existente (por id), no regenerarla.
3. (defensa BD) índice único sobre `(tenant_id, idempotency_key)`.
**Riesgo:** medio — cambia el contrato del endpoint (nuevo header). Compatible si la
clave es opcional con fallback al comportamiento actual + warning.
**Decisión:** ¿acepto `Idempotency-Key` (requiere coordinación con frontend) o prefieres
deduplicar por hash de contenido (`sha256`, ya existe en el modelo) sin tocar el contrato?

---

## ROJO #3 — Portal: issue_token concurrente → dos tokens activos
**Severidad:** ALTA-auth · **Esfuerzo:** bajo (migración) · **Riesgo del fix:** bajo-medio

**Causa raíz (confirmada):** `client_portal/tokens.py:27 issue_token`. Hace
SELECT-todos-los-activos → `is_active=False` en bucle → INSERT nuevo → commit, **sin lock
ni UNIQUE**. Dos `issue_token` concurrentes del mismo cliente (admin doble-click "generar
enlace") leen ambos, desactivan ambos, insertan ambos → **DOS tokens activos**.
**Efecto:** (a) revocar uno deja el otro vivo = revocación incompleta (seguridad);
(b) el endpoint admin de status (`scalar_one_or_none`) casca 500 (`MultipleResultsFound`).

**Fix propuesto (el más limpio de los 4):**
- **UNIQUE parcial en BD:** `CREATE UNIQUE INDEX ... ON client_portal_tokens
  (client_id, tenant_id) WHERE is_active = true` (migración). DB-enforced: el 2º insert
  concurrente falla → garantiza UN token activo, Y arregla el `scalar_one_or_none`.
- Manejar `IntegrityError` en `issue_token` (reintentar/devolver el existente).
- **NO** arreglar solo el `scalar_one_or_none`→`.limit(1)`: enmascararía el doble-token.
**Riesgo:** bajo-medio — es tabla de AUTH; requiere migración + probar que un cliente con
0 tokens activos no choca con el índice (el `WHERE is_active=true` lo cubre).
**Decisión:** ¿OK a la migración UNIQUE parcial? Es la opción correcta y de bajo riesgo.

---

## ROJO #4 — Autonomy gate se bypasea para importes ≤ 5000 €
**Severidad:** ALTA-fiscal/payroll · **Esfuerzo:** depende del diseño · **Riesgo:** medio
**⚠️ ESTE NECESITA VERIFICACIÓN — el inbox lo afirma pero el código sugiere matiz.**

**Lo que veo en el código:** hay DOS mecanismos distintos y NO equivalentes:
- `evaluate_autonomy`/`gated_tool` (`services/autonomy.py`): política por dominio
  AUTO/CONFIRM/MANUAL. `fiscal`=MANUAL, `banking_write`=MANUAL por defecto. NO mira importe.
- `APPROVAL_THRESHOLD_EUR = 5000` (`validators/billing.py:171`): umbral de importe
  independiente; en `_invoice_create_async.py:68` solo crea `PendingApproval`
  `if amount > 5000`. Comentario explícito: "NO es el gate de autonomía".

**El hueco real:** una acción con dominio en AUTO **y** importe ≤ 5000 € no pasa por
NINGÚN control → ejecuta directa. Si la política del dominio es AUTO (el tenant la relajó),
un importe de 4999 € se ejecuta sin aprobación. ¿Es bug o diseño? Depende de si "≤5000 €
en AUTO sin aprobación" es aceptable para tu negocio.
**Decisión que necesito:** ¿el umbral 5000 € debe aplicar SIEMPRE (incluso para acciones
no-fiscales en AUTO), o solo es un segundo cinturón sobre billing? Esto es **política de
producto**, no un bug técnico claro — por eso lo dejo para tu criterio antes de nada.

---

## Resumen para decidir
| # | Qué | Esfuerzo | Riesgo fix | Lo que necesito de ti |
|---|-----|----------|-----------|----------------------|
| 3 | Portal doble-token | **bajo** | bajo-medio | OK a migración UNIQUE parcial |
| 2 | SEPA doble-remesa | bajo-medio | medio | ¿Idempotency-Key vs dedup por sha256? |
| 1 | Orquestador doble-ejec | medio-alto | alto | ¿semántica (a) o (b)? |
| 4 | Autonomy gate 5000€ | ? | medio | decisión de política (¿bug o diseño?) |

**Recomendación de orden:** #3 primero (limpio, alto valor seguridad) → #2 → #1 → #4.
Ninguno lo toco sin tu OK explícito (zona NO-EDIT).
