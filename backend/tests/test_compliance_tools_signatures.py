"""Las tools de compliance deben aceptar tenant_id como kwarg en su
args_schema (lo que el LLM ve), aunque no usen el valor — el LLM se lo
pasa por convención al alinearse con el resto de tools del sistema.

Antes de este fix, llamar `check_fiscal_deadlines(tenant_id=...)` reventaba
con TypeError (visto en BD: task 'afa29664...' del 4 mayo y la del prompt
CTO de hoy).
"""
from __future__ import annotations

# Importamos las @tool desde su módulo concreto. El package re-exporta
# `tools` como lista, así que `from app.agents.compliance import tools`
# devolvería la lista en vez del módulo — usamos el path completo.
from app.agents.compliance.tools import check_boe_news, check_fiscal_deadlines


class TestComplianceToolsAcceptTenantId:
    def test_check_fiscal_deadlines_args_schema_has_tenant_id(self):
        fields = check_fiscal_deadlines.args_schema.model_fields
        assert "tenant_id" in fields, (
            f"check_fiscal_deadlines schema must accept tenant_id; got: {list(fields)}"
        )

    def test_check_boe_news_args_schema_has_tenant_id(self):
        fields = check_boe_news.args_schema.model_fields
        assert "tenant_id" in fields, (
            f"check_boe_news schema must accept tenant_id; got: {list(fields)}"
        )

    def test_tenant_id_is_optional_in_both(self):
        """tenant_id no debe ser obligatorio: el LLM puede omitirlo."""
        for tool in (check_fiscal_deadlines, check_boe_news):
            field = tool.args_schema.model_fields["tenant_id"]
            # En pydantic v2 los campos opcionales tienen default explícito
            assert not field.is_required(), (
                f"{tool.name}.tenant_id should be optional"
            )
