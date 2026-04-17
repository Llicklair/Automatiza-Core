"""
Generacion de PDFs de RRHH con formato oficial espanol.

Barrel re-export: cada tipo de documento vive en su propio modulo.
- _payroll.py          → Nominas (recibo de salario)
- _finiquito.py        → Finiquito
- _liquidacion.py      → Liquidacion y finiquito
- _registro_jornada.py → Registro de jornada
- _hr_common.py        → Helpers compartidos
"""

from app.services.pdf._finiquito import generate_finiquito_pdf  # noqa: F401
from app.services.pdf._liquidacion import generate_liquidacion_finiquito_pdf  # noqa: F401
from app.services.pdf._payroll import generate_payroll_pdf  # noqa: F401
from app.services.pdf._registro_jornada import generate_registro_jornada_pdf  # noqa: F401
