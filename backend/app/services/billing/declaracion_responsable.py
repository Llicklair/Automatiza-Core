"""Documento de la DECLARACIÓN RESPONSABLE del productor del SIF.

Genera el documento normalizado que exige el art. 15 de la Orden HAC/1177/2024:
título fijo + campos a)–l) en orden, cada dato precedido del texto que lo describe.
El productor (la SL) lo suscribe (fecha + lugar) y debe estar disponible dentro del
propio sistema y a disposición del comercializador y del cliente (art. 15.3).

Los datos de identificación del sistema y del productor salen del
`SistemaInformatico` (settings VERIFACTU_SIF_*). Antes de suscribirlo en real, el
NIF del productor debe ser el de la SL productora (hoy es placeholder).
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from app.services.billing.registro_facturacion import (
    SistemaInformatico,
    default_sistema_informatico,
)

TITULO = "DECLARACIÓN RESPONSABLE DEL SISTEMA INFORMÁTICO DE FACTURACIÓN"

_DESCRIPCION_COMPONENTES = (
    "Aplicación de software de facturación (ERP web) que genera los registros de "
    "facturación de alta y anulación, los encadena mediante huella SHA-256, los "
    "remite a la AEAT en modalidad VERI*FACTU y mantiene el registro de eventos del "
    "sistema."
)

_MANIFESTACION = (
    "El productor declara que este sistema informático, en la versión indicada en "
    "esta declaración, cumple con lo dispuesto en el artículo 29.2.j) de la Ley "
    "58/2003, de 17 de diciembre, General Tributaria, en el Reglamento aprobado por "
    "el Real Decreto 1007/2023, de 5 de diciembre, en la Orden HAC/1177/2024 y en la "
    "sede electrónica de la Agencia Estatal de Administración Tributaria para todo "
    "aquello que complete las especificaciones de dicha orden."
)


def generate_declaracion_responsable(
    *,
    lugar: str,
    fecha: date | None = None,
    sistema: SistemaInformatico | None = None,
    descripcion_componentes: str | None = None,
    direccion_productor: str = "",
) -> str:
    """Devuelve el texto del documento de la declaración responsable (art. 15.1)."""
    s = sistema or default_sistema_informatico()
    f = fecha or datetime.now(UTC).date()
    solo_vf = "Sí" if (s.solo_verifactu or "").upper() == "S" else "No"
    multi = "Sí" if (s.multi_ot or "").upper() == "S" else "No"
    firma = (
        "No aplica (el sistema solo funciona como VERI*FACTU)."
        if solo_vf == "Sí"
        else "Firma electrónica de los registros de facturación y de evento."
    )

    lineas = [
        TITULO,
        "",
        f"a) Nombre del sistema informático: {s.nombre_sistema}",
        f"b) Código identificador del sistema informático (IdSistemaInformatico): {s.id_sistema}",
        f"c) Identificador completo de la versión: {s.version}",
        f"d) Componentes, hardware y software, y descripción de sus funcionalidades: "
        f"{descripcion_componentes or _DESCRIPCION_COMPONENTES}",
        f"e) ¿Se ha producido para funcionar exclusivamente como VERI*FACTU?: {solo_vf}",
        f"f) ¿Permite dar soporte a la facturación de varios obligados tributarios?: {multi}",
        f"g) Tipos de firma de los registros (solo aplicable si no se usa como VERI*FACTU): {firma}",
        f"h) Productor del sistema informático (nombre o razón social): {s.nombre_razon}",
        f"i) NIF del productor: {s.nif}",
        f"j) Dirección postal completa del productor: {direccion_productor or '(pendiente de configurar)'}",
        f"k) Manifestación de cumplimiento: {_MANIFESTACION}",
        f"l) Fecha y lugar de suscripción: {f.strftime('%d/%m/%Y')}, {lugar}.",
    ]
    return "\n".join(lineas)
