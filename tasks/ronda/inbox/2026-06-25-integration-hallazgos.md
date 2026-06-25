# Inbox /forja — hallazgos en services/integration (2026-06-25, barrido #1)

Defectos substantivos que el loop NO auto-arregló (fix no trivial, semi-by-design o con
matiz de seguridad). Tu criterio decide. El #5 SÍ se arregló (PR #50).

## Para revisar
1. **`messaging.py:40-52` `find_integration_by_chat` sin filtro de tenant** [alta].
   Escanea TODAS las integraciones telegram de TODOS los tenants y casa por `chat_id` en
   Python. Si dos tenants comparten `chat_id` → el mensaje se procesa en el tenant
   equivocado. Semi by-design (el webhook de Telegram no trae tenant, como el callback de
   firma). Fix recomendado: constraint único `(integration_type, chat_id)` + filtrar/casar
   determinista en SQL. Requiere migración → decisión humana.

2. **`messaging.py:~157-165` polling de `process_and_reply` sin timeout** [media].
   `dispatch_orchestrator` no tiene `asyncio.wait_for`: si el worker se cuelga, la corutina
   queda suspendida y el slot ocupado hasta 120 s. (El finder exageró lo de "60 conexiones":
   el `async with` es secuencial, 1 a la vez — eso NO es el problema; el timeout sí.)

3. **`service.py:255-268` `handle_oauth_callback`: state OAuth no recuperable** [media].
   En fallo transitorio de `exchange_code`, el state ya fue consumido (pop) → el reintento
   falla con "estado inválido" y el usuario reinicia desde cero. Fix posible: restaurar el
   state en excepción — PERO valorar replay/seguridad antes. Decisión humana.

4. **`heartbeat.py:148-154` conteo de tareas en el feed** [baja, cosmético].
   El conteo de "pendientes" no filtra por empleado asignado → mensaje del activity feed
   impreciso con varios empleados del mismo dominio. No rompe nada.

## Descartado (falso positivo del finder)
- "httpx sin timeout → cuelga infinito" en `service.py:305`: FALSO. httpx por defecto usa
  timeout de 5s. La mejora real (manejar 5xx/429 del test de token) es opinable → no urgente.
