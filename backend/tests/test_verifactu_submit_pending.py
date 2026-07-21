"""Job de remisión continua VeriFactu (submit_pending_verifactu)."""

import pytest

from app.workers.tasks_scheduler import submit_pending_verifactu


@pytest.mark.asyncio
async def test_remision_automatica_inactiva_sin_nif_configurado():
    # Con VERIFACTU_SIF_NIF en placeholder (B00000000, default de tests), la remisión
    # automática es un no-op seguro: corta antes de tocar la BD, no lanza y no intenta
    # enviar nada a la AEAT.
    await submit_pending_verifactu()
