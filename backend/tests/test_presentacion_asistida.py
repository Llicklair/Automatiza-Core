"""Tests de presentación asistida (PRES.ASS)."""
import pytest
from app.services.presentacion.asistida import (
    SEDE_AEAT_LINKS,
    TenantSummary,
    build_modelo_131_xml,
    build_modelo_200_xml,
    build_xml,
    get_sede_link,
)


def _tenant(year=2026, quarter=1) -> TenantSummary:
    return TenantSummary(
        nif="B12345678",
        name="Acme S.L.",
        address="Calle Mayor 1, 28001 Madrid",
        fiscal_year=year,
        quarter=quarter,
    )


class TestBuildXml:
    def test_modelo_131_contiene_datos_tenant(self):
        xml = build_modelo_131_xml(_tenant())
        assert "<?xml" in xml
        assert "Modelo131" in xml
        assert "B12345678" in xml
        assert "Acme S.L." in xml
        assert "Calle Mayor 1" in xml

    def test_modelo_131_devengo_correcto(self):
        xml = build_modelo_131_xml(_tenant(year=2026, quarter=3))
        assert "<Ejercicio>2026</Ejercicio>" in xml
        assert "<Periodo>3T</Periodo>" in xml

    def test_modelo_200_periodo_es_anual(self):
        xml = build_modelo_200_xml(_tenant(year=2025))
        assert "Modelo200" in xml
        assert "<Ejercicio>2025</Ejercicio>" in xml
        assert "<Periodo>0A</Periodo>" in xml

    def test_modelo_200_tipo_gravamen_25(self):
        xml = build_modelo_200_xml(_tenant())
        assert "<TipoGravamen>25</TipoGravamen>" in xml

    def test_meta_prerelleno_presente(self):
        xml = build_modelo_131_xml(_tenant())
        assert "MetaPrerelleno" in xml
        assert 'sistema="AutomatizaPyme"' in xml

    def test_caracteres_especiales_escapados(self):
        tenant = TenantSummary(
            nif="B12345678",
            name='Tony & "Bros" <SL>',
            address="Calle <test> & Co.",
        )
        xml = build_modelo_131_xml(tenant)
        # Caracteres XML-reservados deben venir escapados
        assert "&amp;" in xml
        assert "&lt;" in xml or "&gt;" in xml
        assert "<SL>" not in xml  # no aparece literal sin escape


class TestBuildXmlDispatcher:
    def test_modelo_131(self):
        xml = build_xml("131", _tenant())
        assert "Modelo131" in xml

    def test_modelo_200(self):
        xml = build_xml("200", _tenant())
        assert "Modelo200" in xml

    def test_modelo_invalido_lanza(self):
        with pytest.raises(ValueError, match="no soportado"):
            build_xml("303", _tenant())  # type: ignore


class TestSedeLinks:
    def test_linkmaps_apunta_a_sede_oficial(self):
        for modelo in ("131", "200"):
            url = get_sede_link(modelo)
            assert url.startswith("https://sede.agenciatributaria.gob.es/")

    def test_modelo_invalido_lanza(self):
        with pytest.raises(ValueError):
            get_sede_link("999")  # type: ignore

    def test_links_son_estables(self):
        # Snapshot: si AEAT cambia las URLs, falla el test y obligamos a
        # actualizar de forma visible en code review.
        assert SEDE_AEAT_LINKS["131"].endswith("G609.shtml")
        assert SEDE_AEAT_LINKS["200"].endswith("G208.shtml")
