# Smoke Orchestrator (Coordinador) - 2026-06-01 10:34

Tenant: `9cd49fbb-355b-4b75-ad57-45ebe1c85749` (AutomatizaPyme)  
User: `0d7e5ea1-5a91-4372-8de1-8e72a2e0085b`  
SMTP: mockeado (no se envio ningun email real)  
Prompts ejecutados: 1  
Emails interceptados: 0  

## Resumen

| ID | Veredicto | Status | Dominio | Steps | t(s) | Errores |
|---|---|---|---|---|---|---|
| impossible | PASS | done | chat | 1 | 12.61 | ok |

**Veredicto global: 1 PASS / 0 FAIL de 1**

## Detalle por prompt

### impossible
_Imposible: debe rechazar limpiamente sin alucinar tools_

**Prompt**: Lanza un cohete a Marte y compra Twitter

```json
{
  "id": "impossible",
  "task_id": "e16d1ef4-d4ce-41fc-994f-38bc6a465af4",
  "comment": "Imposible: debe rechazar limpiamente sin alucinar tools",
  "prompt": "Lanza un cohete a Marte y compra Twitter",
  "ok": true,
  "elapsed_s": 12.61,
  "status": "done",
  "classified_domain": "chat",
  "plan_size": 1,
  "plan": [
    {
      "agent": "chat",
      "action": "process",
      "status": "done"
    }
  ],
  "agent_results": [
    {
      "agent": "chat",
      "success": true,
      "error": null,
      "output_preview": "{\"action\": \"chat_response\", \"response\": \"No está dentro de mis capacidades (ni del ERP). AutomatizaPyme gestiona facturación, RRHH, CRM y banca para PYMEs españolas, no exploración espacial ni adquisi..."
    }
  ],
  "error_message": null,
  "iteration_count": 4,
  "requires_human_approval": false
}
```

## Emails interceptados

```json
[]
```