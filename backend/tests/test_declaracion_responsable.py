"""Documento de la declaración responsable del productor (art. 15 Orden HAC/1177/2024)."""

from datetime import date

from app.services.billing.declaracion_responsable import TITULO, generate_declaracion_responsable
from app.services.billing.registro_facturacion import default_sistema_informatico


def test_empieza_con_el_titulo_normalizado():
    doc = generate_declaracion_responsable(lugar="Madrid, España", fecha=date(2026, 7, 21))
    assert doc.startswith(TITULO)


def test_incluye_los_campos_a_l_en_orden():
    doc = generate_declaracion_responsable(lugar="Madrid, España")
    for letra in "abcdefghijkl":
        assert f"\n{letra}) " in doc
    posiciones = [doc.index(f"\n{letra}) ") for letra in "abcdefghijkl"]
    assert posiciones == sorted(posiciones)  # en el orden a)…l)


def test_refleja_datos_del_sistema_y_del_productor():
    s = default_sistema_informatico()
    doc = generate_declaracion_responsable(lugar="Alicante, España")
    assert s.nombre_sistema in doc
    assert s.id_sistema in doc
    assert s.version in doc
    assert s.nombre_razon in doc  # productor
    assert s.nif in doc  # NIF del productor


def test_manifestacion_ancla_las_normas():
    doc = generate_declaracion_responsable(lugar="Madrid, España")
    assert "29.2.j)" in doc
    assert "1007/2023" in doc
    assert "HAC/1177/2024" in doc


def test_fecha_y_lugar_de_suscripcion():
    doc = generate_declaracion_responsable(lugar="Elche, España", fecha=date(2026, 7, 21))
    assert "21/07/2026" in doc
    assert "Elche, España" in doc
