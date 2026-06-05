"""Tests del ordenamiento por enlace de la cadena Verifactu (FAC.HASH).

Lógica pura (sin BD): el orden de la cadena lo define el enlace hash
``huella_anterior → huella``, NO el ``created_at``. Esto evita el bug por el que
dos registros con la misma marca de tiempo podían encadenar mal al emitir o dar
falsos negativos al verificar la integridad.

Complementa a ``test_verifactu_chain.py`` (que cubre el camino con BD).
"""

import random

from app.services.billing.verifactu_chain import (
    find_tail_huella,
    order_verifactu_chain,
)


class _Rec:
    """Registro mínimo con los campos que usa el ordenamiento."""

    def __init__(self, huella, huella_anterior, payload=""):
        self.huella = huella
        self.huella_anterior = huella_anterior
        self.payload_canonico = payload


def _chain(n):
    """Cadena bien formada de n registros: h0 (génesis) → h1 → … → h{n-1}."""
    recs = []
    prev = None
    for i in range(n):
        h = f"h{i}"
        recs.append(_Rec(h, prev))
        prev = h
    return recs


# ─── order_verifactu_chain ────────────────────────────────────────────────────


def test_ordena_por_enlace_no_por_orden_de_entrada():
    recs = _chain(5)
    barajados = recs[:]
    random.shuffle(barajados)
    ordered, ok = order_verifactu_chain(barajados)
    assert ok
    assert [r.huella for r in ordered] == ["h0", "h1", "h2", "h3", "h4"]


def test_cadena_vacia_es_valida():
    assert order_verifactu_chain([]) == ([], True)


def test_un_solo_registro():
    ordered, ok = order_verifactu_chain(_chain(1))
    assert ok and len(ordered) == 1


def test_genesis_con_string_vacio_equivale_a_none():
    recs = [_Rec("h0", ""), _Rec("h1", "h0")]
    ordered, ok = order_verifactu_chain(recs)
    assert ok and len(ordered) == 2


def test_eslabon_perdido_no_bien_formada():
    recs = _chain(4)
    del recs[2]  # h3 apunta a h2, que ya no está
    _, ok = order_verifactu_chain(recs)
    assert not ok


def test_bifurcacion_no_bien_formada():
    recs = [_Rec("h0", None), _Rec("h1a", "h0"), _Rec("h1b", "h0")]
    _, ok = order_verifactu_chain(recs)
    assert not ok


def test_multiple_genesis_no_bien_formada():
    recs = [_Rec("h0", None), _Rec("h1", None)]
    _, ok = order_verifactu_chain(recs)
    assert not ok


def test_ciclo_no_bien_formada():
    recs = [_Rec("h0", "h1"), _Rec("h1", "h0")]  # ningún génesis
    _, ok = order_verifactu_chain(recs)
    assert not ok


# ─── find_tail_huella ─────────────────────────────────────────────────────────


def test_tail_de_cadena_lineal():
    assert find_tail_huella(_chain(5)) == "h4"


def test_tail_un_registro():
    assert find_tail_huella(_chain(1)) == "h0"


def test_tail_vacia_es_none():
    assert find_tail_huella([]) is None


def test_tail_independiente_del_orden_de_entrada():
    recs = _chain(4)
    random.shuffle(recs)
    assert find_tail_huella(recs) == "h3"
