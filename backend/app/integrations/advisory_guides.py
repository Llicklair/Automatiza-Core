"""
Guías normativas estáticas para PYMEs españolas.
Contenido de referencia por sección: fiscal, laboral, mercantil.
"""

GUIAS: dict[str, list[dict]] = {
    "fiscal": [
        {
            "titulo": "Modelo 303 — Autoliquidación trimestral del IVA",
            "resumen": "Todas las empresas y autónomos que realicen actividades sujetas a IVA deben presentar el Modelo 303 cada trimestre (abril, julio, octubre y enero). Incluye IVA repercutido menos IVA soportado deducible.",
            "referencia_legal": "Art. 164 Ley 37/1992, de 28 de diciembre, del IVA",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740",
            "consejo_pyme": "Revisa que todas las facturas de gasto estén contabilizadas antes del cierre trimestral. El IVA soportado no declarado en plazo se puede recuperar en los 4 años siguientes.",
        },
        {
            "titulo": "Modelo 130 — Pago fraccionado IRPF",
            "resumen": "Los autónomos en estimación directa deben ingresar trimestralmente el 20% del rendimiento neto acumulado, descontando los pagos ya realizados y las retenciones soportadas.",
            "referencia_legal": "Art. 110 Ley 35/2006, de 28 de noviembre, del IRPF",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764",
            "consejo_pyme": "Si más del 70% de tus ingresos tienen retención, puedes estar exento de presentar el 130. Consúltalo con tu asesor.",
        },
        {
            "titulo": "Modelo 111 — Retenciones e ingresos a cuenta",
            "resumen": "Declaración trimestral de las retenciones practicadas a trabajadores, profesionales y empresarios. Obligatorio si pagas nóminas o facturas con retención de IRPF.",
            "referencia_legal": "Art. 108 RD 439/2007 Reglamento del IRPF",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-2007-6820",
            "consejo_pyme": "Verifica que los tipos de retención aplicados coinciden con la situación personal de cada trabajador. Un error puede generar sanciones.",
        },
        {
            "titulo": "SII — Suministro Inmediato de Información del IVA",
            "resumen": "Las empresas con facturación superior a 6 millones de euros (y quienes opten voluntariamente) deben remitir sus registros de facturación a la AEAT en un plazo de 4 días.",
            "referencia_legal": "RD 596/2016, de 2 de diciembre",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-2016-11575",
            "consejo_pyme": "Aunque no sea obligatorio para tu PYME, el SII te da acceso a los datos de tus clientes/proveedores en la AEAT y facilita la detección de discrepancias.",
        },
        {
            "titulo": "Factura electrónica obligatoria (Ley Crea y Crece)",
            "resumen": "A partir de 2026, todas las empresas y autónomos deberán emitir y recibir facturas en formato electrónico estructurado (Facturae) en sus relaciones B2B.",
            "referencia_legal": "Ley 18/2022, de 28 de septiembre (Crea y Crece), Art. 12",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-2022-15818",
            "consejo_pyme": "Adapta tu software de facturación antes de la fecha límite. AutomatizaPyme ya genera facturas compatibles con Facturae.",
        },
        {
            "titulo": "Modelo 347 — Operaciones con terceros",
            "resumen": "Declaración anual informativa de operaciones con terceros que superen los 3.005,06 € anuales (IVA incluido). Se presenta en febrero.",
            "referencia_legal": "Art. 93 Ley 58/2003 General Tributaria + RD 1065/2007",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-2007-15984",
            "consejo_pyme": "Cruza tus datos con los de tus principales clientes y proveedores antes de presentar. Las discrepancias generan requerimientos automáticos de la AEAT.",
        },
        {
            "titulo": "Modelo 390 — Resumen anual del IVA",
            "resumen": "Declaración-resumen anual del IVA que recopila toda la información de los cuatro modelos 303 trimestrales. Se presenta en enero del año siguiente.",
            "referencia_legal": "Art. 164.Uno.6 Ley 37/1992 del IVA",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740",
            "consejo_pyme": "Los importes del 390 deben cuadrar exactamente con la suma de los 303 trimestrales. Cualquier diferencia será detectada automáticamente.",
        },
        {
            "titulo": "Deducciones fiscales para PYMEs",
            "resumen": "Las PYMEs (cifra de negocios < 10M€) pueden aplicar tipo reducido del 25% en IS, libertad de amortización con creación de empleo, y deducción por I+D+i entre el 25% y el 42%.",
            "referencia_legal": "Arts. 101-105 Ley 27/2014 del Impuesto sobre Sociedades",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-2014-12328",
            "consejo_pyme": "Revisa si puedes aplicar la reserva de nivelación (hasta 1M€ de BI) o la reserva de capitalización (10% del incremento de fondos propios).",
        },
    ],
    "mercantil": [
        {
            "titulo": "Depósito de cuentas anuales",
            "resumen": "Toda sociedad mercantil debe depositar sus cuentas anuales en el Registro Mercantil dentro del mes siguiente a su aprobación por la Junta General (plazo habitual: hasta el 30 de julio).",
            "referencia_legal": "Art. 279 RDLeg 1/2010 Ley de Sociedades de Capital",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-2010-10544",
            "consejo_pyme": "El incumplimiento acarrea el cierre registral (no puedes inscribir ningún acto) y multas de 1.200 a 60.000 €. Si facturas más de 6M€, la multa puede llegar a 300.000 €.",
        },
        {
            "titulo": "Junta General Ordinaria — Convocatoria anual",
            "resumen": "La Junta General Ordinaria debe reunirse dentro de los 6 primeros meses de cada ejercicio para aprobar cuentas, aplicación de resultado y gestión de los administradores.",
            "referencia_legal": "Art. 164 RDLeg 1/2010 Ley de Sociedades de Capital",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-2010-10544",
            "consejo_pyme": "En SL con socio único basta con que el socio adopte las decisiones y las haga constar en acta. No hace falta convocatoria formal.",
        },
        {
            "titulo": "Libros mercantiles obligatorios",
            "resumen": "Toda empresa debe llevar: Libro Diario, Libro de Inventarios y Cuentas Anuales, y Libro de Actas. Las SL deben llevar además el Libro Registro de Socios.",
            "referencia_legal": "Arts. 25-30 Código de Comercio (RD 22/1885)",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-1885-6627",
            "consejo_pyme": "Los libros se legalizan telemáticamente en el Registro Mercantil. AutomatizaPyme genera el Libro Diario automáticamente desde tu contabilidad.",
        },
        {
            "titulo": "Legalización telemática de libros",
            "resumen": "Los libros obligatorios deben legalizarse en el Registro Mercantil dentro de los 4 meses siguientes al cierre del ejercicio (hasta el 30 de abril para ejercicios naturales).",
            "referencia_legal": "Art. 18 Ley 14/2013, de apoyo a los emprendedores",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-2013-10074",
            "consejo_pyme": "La legalización se hace online a través de registradores.org. Necesitas certificado digital de la sociedad o del administrador.",
        },
        {
            "titulo": "Modificaciones estatutarias y capital social",
            "resumen": "Cualquier cambio en los estatutos (objeto social, domicilio, capital) requiere acuerdo de Junta y escritura pública inscrita en el Registro Mercantil. El capital mínimo de una SL es 1 € (desde Ley Crea y Crece).",
            "referencia_legal": "Arts. 285-295 RDLeg 1/2010 + Art. 5 Ley 18/2022",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-2010-10544",
            "consejo_pyme": "Si reduces capital a 1 €, debes destinar el 20% de beneficios a reserva legal hasta alcanzar el 60% del capital + reserva legal = 3.000 €.",
        },
        {
            "titulo": "Declaración de titulares reales (TITBE)",
            "resumen": "Desde 2023, todas las personas jurídicas deben comunicar su titularidad real al Registro Mercantil. La declaración se presenta anualmente junto al depósito de cuentas.",
            "referencia_legal": "Orden JUS/794/2021 + Ley 10/2010 de PBC",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-2010-6737",
            "consejo_pyme": "Si no la presentas, el Registro no admitirá el depósito de cuentas. Asegúrate de incluirla cuando prepares la documentación anual.",
        },
        {
            "titulo": "Responsabilidad del administrador",
            "resumen": "Los administradores responden personalmente de las deudas sociales si no promueven la disolución cuando existen causas legales (pérdidas que dejen el patrimonio neto por debajo de la mitad del capital social).",
            "referencia_legal": "Art. 367 RDLeg 1/2010 Ley de Sociedades de Capital",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-2010-10544",
            "consejo_pyme": "Revisa el patrimonio neto en cada cierre trimestral. Si cae por debajo del 50% del capital, tienes 2 meses para convocar Junta.",
        },
        {
            "titulo": "Registro Mercantil — Inscripción de poderes y cargos",
            "resumen": "Todo nombramiento, cese o revocación de administradores y apoderados debe inscribirse en el Registro Mercantil para que sea oponible a terceros.",
            "referencia_legal": "Art. 22 Código de Comercio + Art. 94 RRM",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-1885-6627",
            "consejo_pyme": "Inscribe los cambios cuanto antes. Un administrador cesado no inscrito puede seguir vinculando a la sociedad frente a terceros de buena fe.",
        },
    ],
    "laboral": [
        {
            "titulo": "Registro de jornada obligatorio",
            "resumen": "Todas las empresas deben registrar la jornada diaria de cada trabajador, incluyendo hora de inicio y fin. El registro debe conservarse 4 años.",
            "referencia_legal": "Art. 34.9 Estatuto de los Trabajadores (RDLeg 2/2015)",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-2015-11430",
            "consejo_pyme": "Usa un sistema digital de fichaje. Las inspecciones de trabajo solicitan el registro de jornada como primer documento. Las multas van de 751 a 7.500 €.",
        },
        {
            "titulo": "Contratos de trabajo — Modalidades vigentes",
            "resumen": "Tras la reforma laboral de 2022, las modalidades principales son: indefinido ordinario, indefinido fijo-discontinuo, temporal por circunstancias de la producción (máx. 6 meses) y temporal por sustitución.",
            "referencia_legal": "RDL 32/2021, de 28 de diciembre (Reforma Laboral)",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-2021-21788",
            "consejo_pyme": "Los contratos temporales tienen un límite de 18 meses en 24 para el mismo puesto. Superado el límite, el trabajador pasa a indefinido automáticamente.",
        },
        {
            "titulo": "Prevención de Riesgos Laborales",
            "resumen": "Toda empresa con trabajadores debe tener un Plan de PRL, realizar evaluación de riesgos, vigilancia de la salud y formación en prevención. Las empresas de hasta 25 trabajadores pueden asumir la prevención el propio empresario.",
            "referencia_legal": "Ley 31/1995, de 8 de noviembre, de PRL",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-1995-24292",
            "consejo_pyme": "Contrata un Servicio de Prevención Ajeno (SPA). Es la opción más práctica para PYMEs. El coste ronda los 50-100 €/trabajador/año.",
        },
        {
            "titulo": "Nóminas y Seguridad Social — Plazos",
            "resumen": "Las cotizaciones a la SS se pagan mensualmente antes del último día del mes siguiente al devengo. Las nóminas deben entregarse al trabajador junto con el pago.",
            "referencia_legal": "Art. 29 ET + Art. 56 RD 2064/1995 Reglamento General de Recaudación SS",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-1995-26447",
            "consejo_pyme": "Domicilia los pagos de la SS. Un retraso genera automáticamente recargo del 10% (si pagas en el mes siguiente) o del 20% + intereses después.",
        },
        {
            "titulo": "Plan de Igualdad",
            "resumen": "Las empresas con 50 o más trabajadores deben elaborar y registrar un Plan de Igualdad. Las de menos de 50 pueden hacerlo voluntariamente y acceder a bonificaciones.",
            "referencia_legal": "Art. 45 LO 3/2007 + RD 901/2020",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-2020-12214",
            "consejo_pyme": "Aunque no sea obligatorio, tener un Plan de Igualdad puntúa positivamente en licitaciones públicas y acceso a subvenciones.",
        },
        {
            "titulo": "Convenio colectivo aplicable",
            "resumen": "Todo contrato de trabajo está regulado por un convenio colectivo sectorial o de empresa. El convenio fija salarios mínimos, jornada máxima, vacaciones y permisos por encima del Estatuto de los Trabajadores.",
            "referencia_legal": "Arts. 82-92 Estatuto de los Trabajadores",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-2015-11430",
            "consejo_pyme": "Identifica tu convenio por CNAE en la web del Ministerio de Trabajo. Pagar por debajo del convenio genera reclamaciones automáticas.",
        },
        {
            "titulo": "Protocolo de desconexión digital",
            "resumen": "La empresa debe elaborar una política interna de desconexión digital que garantice el derecho del trabajador a no atender comunicaciones fuera de su horario.",
            "referencia_legal": "Art. 88 LO 3/2018 (LOPDGDD)",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-2018-16673",
            "consejo_pyme": "Basta con un documento interno negociado con los representantes de los trabajadores. Inclúyelo en el manual de acogida.",
        },
        {
            "titulo": "Canal de denuncias interno",
            "resumen": "Desde junio de 2023, las empresas con 50 o más trabajadores deben disponer de un canal interno de denuncias para infracciones normativas.",
            "referencia_legal": "Ley 2/2023, de 20 de febrero (Protección del informante)",
            "url_boe": "https://www.boe.es/buscar/act.php?id=BOE-A-2023-4513",
            "consejo_pyme": "Existen plataformas SaaS desde 30 €/mes que cumplen todos los requisitos legales. No hace falta desarrollo propio.",
        },
    ],
}


def get_guides(section: str = "fiscal") -> list[dict]:
    """Devuelve las guías normativas para la sección indicada."""
    return GUIAS.get(section, GUIAS["fiscal"])
