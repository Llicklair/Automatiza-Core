"""URL de cotejo de la AEAT del QR tributario (ValidarQR)."""

from app.services.billing.verifactu_qr import build_aeat_cotejo_url


def test_url_incluye_los_4_params_en_orden():
    url = build_aeat_cotejo_url(
        nif="B12345678",
        num_serie="A2026/001",
        fecha="14-05-2026",
        importe="121.00",
        base="https://x/ValidarQR",
    )
    assert url.startswith("https://x/ValidarQR?")
    qs = url.split("?", 1)[1]
    keys = [p.split("=")[0] for p in qs.split("&")]
    assert keys == ["nif", "numserie", "fecha", "importe"]  # orden oficial
    assert "nif=B12345678" in url
    assert "importe=121.00" in url


def test_caracteres_especiales_van_url_encoded():
    url = build_aeat_cotejo_url(
        nif="B1",
        num_serie="A/1 2",
        fecha="14-05-2026",
        importe="10.00",
        base="https://x/ValidarQR",
    )
    numserie_val = url.split("numserie=")[1].split("&")[0]
    assert "/" not in numserie_val  # el '/' va codificado (%2F)
    assert " " not in numserie_val  # el espacio va codificado (+ o %20)
