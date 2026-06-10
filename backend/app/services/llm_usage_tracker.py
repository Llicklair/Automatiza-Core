"""
Tracker en memoria de uso LLM por tenant/agente/mes.

Captura llamadas, tokens y estima costes sin dependencias externas.
Los datos son efímeros (se pierden al reiniciar); para persistencia
migrar a Redis usando los mismos métodos públicos.
"""

import logging
import threading
from collections import defaultdict
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

_lock = threading.Lock()

# Estructura: {tenant_id: {YYYY-MM: {agent: {provider: {calls, tokens_in, tokens_out}}}}}
_store: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(
    lambda: {"calls": 0, "tokens_in": 0, "tokens_out": 0}
))))

# Precios en USD por 1M tokens (input, output) — actualizar periódicamente
_PRICE_TABLE: dict[str, tuple[float, float]] = {
    "anthropic":   (3.00,  15.00),   # claude-sonnet-4-6
    "openai":      (0.15,   0.60),   # gpt-4o-mini
    "groq":        (0.05,   0.10),   # llama-3.3-70b
    "openrouter":  (0.50,   1.50),   # promedio modelos free/paid
    "claude_code": (0.00,   0.00),   # CLI local — sin coste directo
    "mock":        (0.00,   0.00),
}

_MAX_MONTHS_PER_TENANT = 6  # anti memory-leak


def record(
    tenant_id: str,
    agent: str,
    provider: str,
    tokens_in: int,
    tokens_out: int,
) -> None:
    """Registra una llamada LLM. Thread-safe. Falla silenciosamente."""
    if not tenant_id or tokens_in + tokens_out == 0:
        return
    month = datetime.now(UTC).strftime("%Y-%m")
    prov = (provider or "unknown").lower()
    ag = agent or "unknown"
    try:
        with _lock:
            bucket = _store[tenant_id][month][ag][prov]
            bucket["calls"] += 1
            bucket["tokens_in"] += tokens_in
            bucket["tokens_out"] += tokens_out
            # Limpiar meses viejos si hay demasiados
            months = sorted(_store[tenant_id].keys(), reverse=True)
            for old in months[_MAX_MONTHS_PER_TENANT:]:
                del _store[tenant_id][old]
    except Exception:
        logger.debug("No se pudo registrar el uso LLM; continúo", exc_info=True)


def estimate_cost(provider: str, tokens_in: int, tokens_out: int) -> float:
    """Devuelve el coste estimado en USD."""
    prov = (provider or "").lower()
    price_in, price_out = _PRICE_TABLE.get(prov, (1.00, 3.00))
    return (tokens_in * price_in + tokens_out * price_out) / 1_000_000


def get_monthly_stats(tenant_id: str, months: int = 3) -> list[dict]:
    """
    Devuelve estadísticas de uso para los últimos N meses del tenant.

    Retorna lista ordenada por mes descendente:
    [
      {
        month: "2025-05",
        total_calls: int,
        total_tokens_in: int,
        total_tokens_out: int,
        estimated_cost_usd: float,
        by_agent: [
          { agent, provider, calls, tokens_in, tokens_out, cost_usd }
        ]
      }
    ]
    """
    result = []
    with _lock:
        tenant_data = dict(_store.get(tenant_id, {}))

    sorted_months = sorted(tenant_data.keys(), reverse=True)[:months]

    for month in sorted_months:
        month_data = tenant_data[month]
        total_calls = 0
        total_in = 0
        total_out = 0
        total_cost = 0.0
        by_agent = []

        for agent, providers in month_data.items():
            for provider, counts in providers.items():
                calls = counts["calls"]
                tin = counts["tokens_in"]
                tout = counts["tokens_out"]
                cost = estimate_cost(provider, tin, tout)
                total_calls += calls
                total_in += tin
                total_out += tout
                total_cost += cost
                by_agent.append({
                    "agent": agent,
                    "provider": provider,
                    "calls": calls,
                    "tokens_in": tin,
                    "tokens_out": tout,
                    "cost_usd": round(cost, 4),
                })

        by_agent.sort(key=lambda x: x["tokens_in"] + x["tokens_out"], reverse=True)
        result.append({
            "month": month,
            "total_calls": total_calls,
            "total_tokens_in": total_in,
            "total_tokens_out": total_out,
            "estimated_cost_usd": round(total_cost, 4),
            "by_agent": by_agent,
        })

    return result


def flush_tenant(tenant_id: str) -> None:
    """Elimina todos los datos del tenant (útil en tests)."""
    with _lock:
        _store.pop(tenant_id, None)


def _snapshot() -> list[dict]:
    """Copia plana del store: filas (tenant, month, agent, provider, counts)."""
    rows: list[dict] = []
    with _lock:
        for tenant_id, months in _store.items():
            for month, agents in months.items():
                for agent, providers in agents.items():
                    for provider, counts in providers.items():
                        rows.append({
                            "tenant_id": tenant_id,
                            "month": month,
                            "agent": agent,
                            "provider": provider,
                            "calls": counts["calls"],
                            "tokens_in": counts["tokens_in"],
                            "tokens_out": counts["tokens_out"],
                        })
    return rows


async def persist_to_db() -> int:
    """Vuelca el store en memoria a `llm_usage_monthly` (valores ABSOLUTOS).

    Idempotente: hace upsert SET (no incrementa), así que recargar y volver a
    volcar no duplica. Falla silenciosamente (best-effort).
    """
    import uuid as _uuid
    from datetime import datetime as _dt

    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models.llm_usage import LlmUsageMonthly

    rows = _snapshot()
    if not rows:
        return 0
    written = 0
    try:
        async with AsyncSessionLocal() as db:
            for r in rows:
                res = await db.execute(
                    select(LlmUsageMonthly).where(
                        LlmUsageMonthly.tenant_id == _uuid.UUID(r["tenant_id"]),
                        LlmUsageMonthly.month == r["month"],
                        LlmUsageMonthly.agent == r["agent"],
                        LlmUsageMonthly.provider == r["provider"],
                    )
                )
                existing = res.scalar_one_or_none()
                if existing:
                    existing.calls = r["calls"]
                    existing.tokens_in = r["tokens_in"]
                    existing.tokens_out = r["tokens_out"]
                    existing.updated_at = _dt.now(UTC)
                else:
                    db.add(LlmUsageMonthly(
                        tenant_id=_uuid.UUID(r["tenant_id"]),
                        month=r["month"],
                        agent=r["agent"],
                        provider=r["provider"],
                        calls=r["calls"],
                        tokens_in=r["tokens_in"],
                        tokens_out=r["tokens_out"],
                        updated_at=_dt.now(UTC),
                    ))
                written += 1
            await db.commit()
    except Exception:  # noqa: BLE001 — persistencia best-effort, no debe tumbar el shutdown
        return 0
    return written


async def load_from_db(months: int = _MAX_MONTHS_PER_TENANT) -> int:
    """Carga los últimos `months` meses desde `llm_usage_monthly` al store.

    Se llama una vez al arrancar para restaurar el dashboard tras un reinicio.
    """
    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models.llm_usage import LlmUsageMonthly

    # Meses recientes a restaurar (YYYY-MM de hoy hacia atrás).
    now = datetime.now(UTC)
    keep = set()
    y, m = now.year, now.month
    for _ in range(months):
        keep.add(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1

    loaded = 0
    try:
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(LlmUsageMonthly))
            with _lock:
                for row in res.scalars().all():
                    if row.month not in keep:
                        continue
                    bucket = _store[str(row.tenant_id)][row.month][row.agent][row.provider]
                    bucket["calls"] = int(row.calls or 0)
                    bucket["tokens_in"] = int(row.tokens_in or 0)
                    bucket["tokens_out"] = int(row.tokens_out or 0)
                    loaded += 1
    except Exception:  # noqa: BLE001 — si falla, el tracker sigue vacío (no fatal)
        return 0
    return loaded
