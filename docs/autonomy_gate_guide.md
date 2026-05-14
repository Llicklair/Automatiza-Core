# Autonomy gate — guía de integración (AI.AGT wiring)

> **Versión 1.0 — 2026-05-14**.

SEC.AUT define la política de autonomía por dominio. Este documento explica
cómo los agentes deben **respetarla** desde sus tools.

## El gate en una frase

> Antes de ejecutar una tool con efecto secundario, llama a
> `evaluate_autonomy(...)`. Si la decisión es **AUTO**, ejecuta. Si es
> **CONFIRM**, crea una `PendingApproval` y devuelve. Si es **MANUAL**,
> devuelve sugerencia sin ejecutar.

## Dominios que deben gatearse

Todos los dominios que escriben en BD o disparan acciones con coste
(dinero, email, llamada a API externa, presentación a AEAT) deben
consultar el gate. Lista mínima a 2026-05-14:

| Dominio | Defaults SEC.AUT | Ejemplo de tool a gatear |
|---|---|---|
| `banking_write` | MANUAL | `transfer_funds`, `create_payment_order` |
| `accounting` | CONFIRM | `create_journal_entry`, `auto_reconcile` |
| `marketing` | CONFIRM | `send_campaign_email`, `bulk_email` |
| `recruitment` | CONFIRM | `email_candidate`, `schedule_interview` |
| `email` | AUTO | (gateado de todas formas si va a destinatario externo) |

Dominios con default AUTO (CRM, RAG, validators, uploads...) pueden saltarse
el gate para tools de solo-lectura. Pero si introducen una tool de
escritura nueva, deben aplicarlo.

## Patrón canónico (Python)

```python
from app.services.autonomy_gate import evaluate_autonomy

async def transfer_funds(
    db, tenant_id, user_id, task_id, amount, beneficiary,
):
    decision = await evaluate_autonomy(
        db,
        tenant_id=tenant_id,
        domain="banking_write",
        action_summary=f"Transferir {amount}€ a {beneficiary}",
        action_payload={"amount": float(amount), "beneficiary": beneficiary},
        user_id=user_id,
        task_id=task_id,
    )

    if decision.manual_only:
        # No ejecuta. Devuelve sugerencia al LLM para que la diga al usuario.
        return decision.to_suggestion_response()

    if decision.needs_approval:
        approval = await decision.persist_pending_approval(db)
        await db.commit()
        return decision.to_pending_response(approval_id=approval.id)

    # AUTO: ejecutar la acción real.
    result = await _actually_transfer(db, ...)
    return {"executed": True, "result": result}
```

## Tres respuestas estándar

El gate devuelve **siempre** un dict con `executed: bool` y `mode`:

| Mode | `executed` | Acción del agente | Acción del orquestador |
|---|---|---|---|
| AUTO | `True` | Ejecuta tool real | Sigue el flujo normalmente |
| CONFIRM | `False` | Crea `PendingApproval` y devuelve `approval_id` | Marca task como `waiting_for_approval` y termina |
| MANUAL | `False` | Devuelve sugerencia textual | El LLM responde al usuario con la sugerencia, sin ejecución |

## Errores comunes

### 1. Llamar al gate **después** de la acción

❌ Ejecutar la transferencia y luego pedir aprobación. Si pasa, ya no
hay vuelta atrás. El gate va **antes** de la acción.

### 2. Ignorar la decisión MANUAL

❌ Tratar MANUAL como warning. Si el gate dice MANUAL el agente debe
parar y devolver sugerencia textual al LLM.

### 3. Persistir aprobación sin `task_id`

`PendingApproval.task_id` es NOT NULL. Si el gate se invoca desde un
endpoint REST sin tarea (poco común), usa solo `to_pending_response()`
y deja que el caller decida cómo persistirlo.

### 4. No gatear tools "obviamente seguras"

Cualquier tool que produzca side-effect (incluso "solo" un email) debe
ser gateada. Marketing == CONFIRM porque un mail mal redactado a 500
contactos no se desenvía.

## Decisión MANUAL: ¿qué muestra el usuario?

El LLM recibe el `to_suggestion_response()` y debe convertirlo en una
respuesta natural al usuario que **describa qué haría** sin haberlo
hecho. Ejemplo de prompt para el LLM:

> "El gate ha devuelto MANUAL. Explica al usuario en lenguaje natural
> qué acción se proponía y dile que la puede ejecutar él
> directamente. NO inventes que ya se ha hecho."

## Logs y observabilidad

`evaluate_autonomy()` emite log `DEBUG` con la decisión.
`persist_pending_approval()` emite `INFO` con `approval.id` para
trazabilidad cruzada con la bandeja.

## Roadmap de wiring (follow-up por agente)

Las tools concretas a refactorizar de forma incremental:

| Sprint | Agente | Tools a gatear |
|---|---|---|
| 7 | `banking` | `transfer_funds`, `pay_invoice`, `create_remesa` |
| 7 | `accounting` | `create_journal_entry`, `auto_reconcile_bank_movement` |
| 8 | `marketing` | `send_campaign_email`, `schedule_post` |
| 8 | `recruitment` | `email_candidate`, `schedule_interview` |
| 8 | `email` | `send_email` (destinatarios externos) |

Cada PR debe incluir:
1. Aplicar el patrón canónico arriba.
2. Test que verifica las 3 ramas (AUTO/CONFIRM/MANUAL).
3. Actualización de la fila correspondiente aquí.

## Tests

Suite del gate: `backend/tests/test_autonomy_gate.py` (10 tests).
Cubre defaults, override de policy, persistencia de approval, validación
de task_id y serialización segura del payload (UUIDs).
