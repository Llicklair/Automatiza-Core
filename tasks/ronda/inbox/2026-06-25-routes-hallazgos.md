# Inbox /forja — hallazgos en api/v1/routes (2026-06-25, barrido #12)

El loop arregló #1 (microsoft_callback sin rls_bypass → PR #51). Quedan:

## Candidatos limpios (auto-fixeables en turnos futuros)
3. ✅ RESUELTO (PR #51, 8e316cf): **`marketing.py:304` zernio platform sin whitelist**. Ahora
   `platform = connected if connected in _ZERNIO_PLATFORMS else "social"`. 51 tests verdes.
4. ✅ RESUELTO (PR #51, cf4e0f0): **`email_marketing.py` `html_body` sin `max_length`** [media].
   Añadidos `Field(max_length=...)` en name(200)/subject(300)/html_body(500_000) de TemplateCreate y
   CampaignCreate. (Pendiente menor: `CampaignUpdate` también podría capear sus campos opcionales.)

## Consistencia (ver contexto RLS-sound)
2. **`sender.py:35` send_campaign (background) no llama `set_current_tenant`** [media]. Overlap con
   agents#1. La campaña YA se filtra por tenant (fix previo, en master) y los destinatarios van por
   campaign_id (tenant-validado). El listener RLS global + fail-closed cubre el resto. Consistencia:
   `set_current_tenant(tenant_id)` al inicio del sender, como los `_isolated` de background. No P0.

## Refactor (diferible)
5. **`marketing.py:581-745` `generate_plan` con ~165 líneas de lógica de negocio en la ruta**
   [baja arch]. Viola "routes = validar + HTTP, cero lógica". Extraer a
   `services/marketing/plan_generator.py`. Refactor amplio → planificar.
