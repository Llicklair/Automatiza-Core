"""Tests del simulador Modelo 303 (UI.SIM) — datos ejemplo, sin BD."""
import pytest

from app.services.onboarding.simulate_303 import (
    SAMPLE_LINES,
    simulate_modelo_303,
)


class TestSimulate303:
    def test_devuelve_estructura_canonica(self):
        result = simulate_modelo_303()

        for key in (
            "is_simulation",
            "year",
            "quarter",
            "tenant_name",
            "tenant_nif",
            "iva_devengado",
            "iva_deducible",
            "totals",
            "explanation",
        ):
            assert key in result, f"Falta campo {key}"

        assert result["is_simulation"] is True

    def test_resultado_positivo_a_ingresar(self):
        """Diseño: el dataset ejemplo siempre da positivo para fijar mensaje."""
        result = simulate_modelo_303()
        assert result["totals"]["resultado"] > 0

    def test_totales_coherentes(self):
        result = simulate_modelo_303()
        totals = result["totals"]

        # Resultado = devengado - deducible
        delta = round(
            totals["devengado_quota"] - totals["deducible_quota"], 2
        )
        assert delta == totals["resultado"]

    def test_iva_devengado_agrupa_por_tipo(self):
        result = simulate_modelo_303()
        devengado = result["iva_devengado"]

        rates = {row["rate"] for row in devengado}
        # El dataset incluye operaciones al 21% y al 10%
        assert 21.0 in rates
        assert 10.0 in rates

    def test_iva_deducible_no_vacio(self):
        result = simulate_modelo_303()
        assert len(result["iva_deducible"]) > 0

    def test_explanation_tiene_3_bullets(self):
        result = simulate_modelo_303()
        expl = result["explanation"]
        assert "headline" in expl
        assert "bullets" in expl
        assert len(expl["bullets"]) == 3
        assert "footer" in expl

    def test_rechaza_trimestre_invalido(self):
        with pytest.raises(ValueError):
            simulate_modelo_303(quarter=5)

    def test_acepta_q1_q2_q3_q4(self):
        for q in (1, 2, 3, 4):
            r = simulate_modelo_303(quarter=q)
            assert r["quarter"] == q

    def test_nif_es_dummy(self):
        result = simulate_modelo_303()
        # X-prefix indica claramente que es ficticio (no NIF español real).
        assert result["tenant_nif"].startswith("X")

    def test_sample_lines_no_vacio(self):
        assert len(SAMPLE_LINES) > 0
        devengadas = [l for l in SAMPLE_LINES if l.direction == "devengado"]
        deducibles = [l for l in SAMPLE_LINES if l.direction == "deducible"]
        assert len(devengadas) > 0
        assert len(deducibles) > 0
