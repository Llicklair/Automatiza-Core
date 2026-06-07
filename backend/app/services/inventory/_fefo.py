"""Lógica pura de asignación FEFO (First Expired, First Out).

Sin dependencias de base de datos: recibe objetos "lote" con los atributos
`id`, `quantity`, `expiry_date` y `received_at`, y decide cuánto descontar de
cada uno. Aislar este cálculo lo hace testeable sin levantar Postgres.

Regla de orden FEFO:
  1. Antes los lotes que caducan antes (`expiry_date` ascendente).
  2. Los lotes SIN caducidad van al final.
  3. A igual caducidad, antes el recibido primero (`received_at` ascendente).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


class LotLike(Protocol):
    id: object
    quantity: int
    expiry_date: date | None
    received_at: object


@dataclass(frozen=True)
class LotAllocation:
    """Cuántas unidades descontar de un lote concreto."""

    lot_id: object
    quantity: int


def _fefo_sort_key(lot: LotLike):
    expiry = lot.expiry_date
    # received_at puede ser datetime con o sin tz; .timestamp() normaliza a float
    # y evita comparar naive con aware. None → 0.0 (se recibió "lo más antiguo").
    received = lot.received_at
    received_key = received.timestamp() if received is not None else 0.0
    return (
        expiry is None,  # los lotes sin caducidad, al final
        expiry or date.max,  # luego por caducidad ascendente
        received_key,  # a igualdad, el más antiguo primero
    )


def plan_fefo_deduction(lots: list[LotLike], quantity: int) -> tuple[list[LotAllocation], int]:
    """Planifica el descuento FEFO de `quantity` unidades sobre `lots`.

    Devuelve `(asignaciones, faltante)` donde `faltante` es lo que no pudo
    cubrirse con los lotes disponibles (0 si se cubrió todo). No modifica nada:
    es el llamador quien aplica las asignaciones.
    """
    qty = int(quantity)
    if qty <= 0:
        return [], 0

    plan: list[LotAllocation] = []
    remaining = qty
    for lot in sorted(lots, key=_fefo_sort_key):
        if remaining <= 0:
            break
        available = int(lot.quantity or 0)
        if available <= 0:
            continue
        take = min(available, remaining)
        plan.append(LotAllocation(lot_id=lot.id, quantity=take))
        remaining -= take

    return plan, remaining
