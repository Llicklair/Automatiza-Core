# Smoke Orchestrator (Coordinador) - 2026-06-03 19:29

Tenant: `9cd49fbb-355b-4b75-ad57-45ebe1c85749` (AutomatizaPyme)  
User: `0d7e5ea1-5a91-4372-8de1-8e72a2e0085b`  
SMTP: mockeado (no se envio ningun email real)  
Prompts ejecutados: 3  
Emails interceptados: 0  

## Resumen

| ID | Veredicto | Status | Dominio | Steps | t(s) | Errores |
|---|---|---|---|---|---|---|
| hr_simple | PASS | done | recruitment | 1 | 146.9 | ok |
| iter5_recruitment | PASS | done | recruitment | 1 | 29.58 | ok |
| iter13_uploads | PASS | done | billing | 1 | 34.0 | ok |

**Veredicto global: 3 PASS / 0 FAIL de 3**

## Detalle por prompt

### hr_simple
_Mono-dominio recruitment: crear candidato_

**Prompt**: Da de alta un candidato llamado Juan Smoke Perez con email juan.smoke@test.com para puesto de desarrollador backend

```json
{
  "id": "hr_simple",
  "task_id": "855d9771-4044-4164-baed-e00d081cdc1f",
  "comment": "Mono-dominio recruitment: crear candidato",
  "prompt": "Da de alta un candidato llamado Juan Smoke Perez con email juan.smoke@test.com para puesto de desarrollador backend",
  "ok": true,
  "elapsed_s": 146.9,
  "status": "done",
  "classified_domain": "recruitment",
  "plan_size": 1,
  "plan": [
    {
      "agent": "recruitment",
      "action": "process",
      "status": "done"
    }
  ],
  "agent_results": [
    {
      "agent": "recruitment",
      "success": true,
      "error": null,
      "output_preview": "{\"action\": \"completed\", \"response\": \"Candidato dado de alta correctamente:\\n\\n- **Nombre:** Juan Smoke Perez\\n- **Email:** juan.smoke@test.com\\n- **ID:** `3551c5f1-ba13-4ef2-88e8-39bdd46689d8`\\n- **Es..."
    },
    {
      "agent": "summary",
      "success": true,
      "error": null,
      "output_preview": "{\"action\": \"chat_response\", \"response\": \"Candidato **Juan Smoke Perez** dado de alta correctamente con email juan.smoke@test.com.\\n\\n**Acción pendiente:** El candidato quedó sin puesto asignado. Para ..."
    }
  ],
  "error_message": null,
  "iteration_count": 4,
  "requires_human_approval": false
}
```

### iter5_recruitment
_Iter5/A: clasificar recruitment -> create_candidate + schedule_interview_

**Prompt**: Da de alta a la candidata Lucia Martinez con email lucia.martinez@test.com para la vacante Backend Senior y agenda una entrevista

```json
{
  "id": "iter5_recruitment",
  "task_id": "72a192e7-2994-4442-bf70-1b082af63930",
  "comment": "Iter5/A: clasificar recruitment -> create_candidate + schedule_interview",
  "prompt": "Da de alta a la candidata Lucia Martinez con email lucia.martinez@test.com para la vacante Backend Senior y agenda una entrevista",
  "ok": true,
  "elapsed_s": 29.58,
  "status": "done",
  "classified_domain": "recruitment",
  "plan_size": 1,
  "plan": [
    {
      "agent": "recruitment",
      "action": "process",
      "status": "done"
    }
  ],
  "agent_results": [
    {
      "agent": "recruitment",
      "success": true,
      "error": null,
      "output_preview": "{\"action\": \"completed\", \"response\": \"Candidata registrada correctamente:\\n\\n- **Nombre:** Lucia Martinez\\n- **Email:** lucia.martinez@test.com\\n- **ID:** `87a6c77e-a679-4064-b0d1-1b8a5bc78931`\\n- **Es..."
    },
    {
      "agent": "summary",
      "success": true,
      "error": null,
      "output_preview": "{\"action\": \"chat_response\", \"response\": \"**Lucia Martinez ha sido registrada correctamente** en el sistema de reclutamiento.\\n\\n- Email: lucia.martinez@test.com\\n- Estado: Nueva candidata (pendiente d..."
    }
  ],
  "error_message": null,
  "iteration_count": 4,
  "requires_human_approval": false
}
```

### iter13_uploads
_Iter13/A: clasificar uploads/documents -> ingest + dispatch a documents_

**Prompt**: Procesa el lote de facturas que subi hoy y dame un resumen

```json
{
  "id": "iter13_uploads",
  "task_id": "daa8ab6b-19aa-4adb-abc0-031c87032ca7",
  "comment": "Iter13/A: clasificar uploads/documents -> ingest + dispatch a documents",
  "prompt": "Procesa el lote de facturas que subi hoy y dame un resumen",
  "ok": true,
  "elapsed_s": 34.0,
  "status": "done",
  "classified_domain": "billing",
  "plan_size": 1,
  "plan": [
    {
      "agent": "custom",
      "action": "process",
      "status": "done"
    }
  ],
  "agent_results": [
    {
      "agent": "custom",
      "success": true,
      "error": null,
      "output_preview": "{\"action\": \"completed\", \"response\": \"Aquí tienes el resumen de tus **28 facturas** (total: **81.140,68€**):\\n\\n### Por estado\\n| Estado | Cantidad | Importe |\\n|--------|----------|---------|\\n| **Dra..."
    },
    {
      "agent": "summary",
      "success": true,
      "error": null,
      "output_preview": "{\"action\": \"chat_response\", \"response\": \"He procesado las **28 facturas** que subiste hoy. Aquí tienes el resumen:\\n\\n**Total facturado: 81.140,68€**\\n\\n- **18 facturas en borrador** (~38.676€) — aún ..."
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