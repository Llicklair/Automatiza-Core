"""Banking agent — datos demo y umbrales de alerta.

Las credenciales PSD2 viven en app.services.banking.psd2 (service reutilizable).
"""

ALERT_THRESHOLDS = {
    "cargo_inusual_eur": 5_000,
    "saldo_minimo_eur": 1_000,
}

_DEMO_SALDOS = [
    {
        "account_id": "demo_001",
        "iban": "ES91 2100 0418 4502 0005 1332",
        "nombre": "Cuenta Corriente (Demo)",
        "saldo": 18450.72,
        "moneda": "EUR",
    },
    {
        "account_id": "demo_002",
        "iban": "ES80 2310 0001 1800 0001 2345",
        "nombre": "Cuenta Ahorro (Demo)",
        "saldo": 5200.00,
        "moneda": "EUR",
    },
]

_DEMO_TXS = [
    {
        "id": "1",
        "fecha": "2026-03-15",
        "concepto": "TRANSFERENCIA RECIBIDA ACME SL",
        "importe": 4500,
        "tipo": "abono",
        "categoria": "cliente_cobro",
    },
    {
        "id": "2",
        "fecha": "2026-03-14",
        "concepto": "AMAZON WEB SERVICES",
        "importe": -350,
        "tipo": "cargo",
        "categoria": "proveedor_servicio",
    },
    {
        "id": "3",
        "fecha": "2026-03-13",
        "concepto": "NOMINAS MARZO 2026",
        "importe": -12000,
        "tipo": "cargo",
        "categoria": "nominas",
    },
    {
        "id": "4",
        "fecha": "2026-03-12",
        "concepto": "ENGIE ENERGIA FACTURA",
        "importe": -280.50,
        "tipo": "cargo",
        "categoria": "suministros",
    },
    {
        "id": "5",
        "fecha": "2026-03-11",
        "concepto": "COBRO FACTURA #2026-041",
        "importe": 7200,
        "tipo": "abono",
        "categoria": "cliente_cobro",
    },
    {
        "id": "6",
        "fecha": "2026-03-10",
        "concepto": "CUOTA PRESTAMO BANCO",
        "importe": -1100,
        "tipo": "cargo",
        "categoria": "financiero",
    },
]
