"""Constantes canónicas del dominio de facturación."""

# Facturas EMITIDAS por nosotros = issued + rectificativas/abono. Las
# rectificativas llevan amount_total negativo, así que sumarlas netea
# correctamente ingresos/IVA/top-clientes; excluirlas SOBREESTIMA las cifras
# (bug B8). Fuente única del conjunto: analytics, reports y billing deben
# importar esta tupla, no redefinirla.
EMITTED_INVOICE_TYPES = ("issued", "rectificativa")
