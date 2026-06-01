# Activar Langfuse (trazabilidad LLM)

Langfuse captura automáticamente cada llamada al modelo (input messages,
output, tokens, latencia, coste estimado) y la agrupa por tenant + tarea.
Útil para debugging de agentes, análisis de coste y detección de prompt
injection en producción.

## Setup (~5 min)

### 1. Cuenta gratis en Langfuse Cloud

Registrarse en <https://cloud.langfuse.com>. Plan gratuito: 50k observaciones/mes,
suficiente para uso interno de una PYME.

Tras crear el proyecto, copiar **Public Key** (`pk-lf-...`) y **Secret Key**
(`sk-lf-...`) desde *Settings → API Keys*.

### 2. Instalar el paquete en el venv

```bash
cd backend
pip install "langfuse>=2.50,<3"
# o, con poetry:
poetry install -E observability
```

El paquete está declarado como **opcional** en `pyproject.toml` (extra
`observability`) para no añadir 5 MB al venv del usuario que no lo necesita.

### 3. Añadir las keys al `.env` del backend

```env
LANGFUSE_PUBLIC_KEY=pk-lf-XXXXXXXXXXXXXXXXXXXX
LANGFUSE_SECRET_KEY=sk-lf-XXXXXXXXXXXXXXXXXXXX
# Opcional, default es cloud.langfuse.com:
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 4. Reiniciar backend

`uvicorn app.main:app --reload` — al primer request a un endpoint que
invoque agentes (`POST /tasks`, etc.), aparecerán las trazas en el
dashboard de Langfuse en segundos.

## Cómo se integra (sin tocar agentes)

`get_langfuse_callback()` en `app/core/llm_callbacks.py` devuelve un
`langfuse.callback.CallbackHandler` listo si las keys + el paquete están
disponibles, sino `None`.

`app/workers/_orchestrator_context.py` lo añade a la lista de callbacks
de LangGraph junto al `UsageTrackingCallback` ya existente. LangGraph
propaga callbacks a todos los nodos, por lo que **cada llamada LLM de
cualquier agente queda trazada sin instrumentar el agente individualmente**.

## Verificar que funciona

1. Login y crea una tarea simple desde la UI (o `POST /api/v1/tasks` con
   un `user_intent` cualquiera).
2. Espera 5-10s.
3. En Langfuse: *Sessions* → la sesión aparecerá con `session_id =
   task_id` y `user_id = tenant_id`.
4. Cada turno del orchestrator es un trace; cada llamada LLM es un span
   con tokens y latencia.

## Desactivar

Quitar las keys del `.env` y reiniciar. El callback degrada a `None`,
sin overhead. Si además quieres librarte del paquete: `pip uninstall langfuse`.

## Coste

Plan gratis cubre proyectos individuales. Para gestoría con muchos clientes
en backend SaaS, monitorizar el contador de observaciones — un agente
LangGraph típico genera 5-15 observaciones por tarea.

## Ver también

- `app/core/observability.py:trace_llm_call` — context manager manual
  para tracear llamadas LLM aisladas (no usado en el flujo principal,
  reservado para casos especiales).
- `app/services/llm_usage_tracker.py` — registro local de tokens/coste
  en BD del propio tenant (independiente de Langfuse).
