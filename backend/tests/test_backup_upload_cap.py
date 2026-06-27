"""Tests del helper de lectura con tope para el restore de backup.

Verifica que `_read_upload_capped` rechaza con 413 ANTES de materializar
todo el upload (lectura por chunks con tope) y que pasa los bytes intactos
para uploads dentro del límite. No aloja 100 MB: usa max_bytes pequeño.
"""

import io

import pytest
from fastapi import HTTPException

from app.api.v1.routes.admin import _read_upload_capped


class FakeUpload:
    """Stub mínimo con `await read(n)` sobre un BytesIO (como UploadFile)."""

    def __init__(self, data: bytes):
        self._b = io.BytesIO(data)

    async def read(self, n: int = -1) -> bytes:
        return self._b.read(n)


@pytest.mark.asyncio
async def test_excede_tope_lanza_413():
    upload = FakeUpload(b"x" * 2000)
    with pytest.raises(HTTPException) as exc:
        await _read_upload_capped(upload, max_bytes=1000)
    assert exc.value.status_code == 413


@pytest.mark.asyncio
async def test_dentro_del_tope_devuelve_bytes_completos():
    data = b"y" * 500
    upload = FakeUpload(data)
    result = await _read_upload_capped(upload, max_bytes=1000)
    assert result == data


@pytest.mark.asyncio
async def test_exactamente_en_el_tope_ok():
    data = b"z" * 1000
    upload = FakeUpload(data)
    result = await _read_upload_capped(upload, max_bytes=1000)
    assert result == data


@pytest.mark.asyncio
async def test_data_vacia_devuelve_bytes_vacios():
    upload = FakeUpload(b"")
    result = await _read_upload_capped(upload, max_bytes=1000)
    assert result == b""


@pytest.mark.asyncio
async def test_para_en_413_sin_leer_todo_el_stream():
    """Confirma que aborta a mitad sin consumir el resto del stream.

    El helper lee en chunks de 1 MB. Con un payload de 3 MB y tope de
    (1 MB + 1 B), tras leer el 2.º chunk (total 2 MB > tope) se aborta:
    queda el 3.er chunk sin leer (prueba de que no se materializa el stream
    completo en RAM).
    """
    chunk = 1024 * 1024
    upload = FakeUpload(b"a" * (3 * chunk))
    with pytest.raises(HTTPException):
        await _read_upload_capped(upload, max_bytes=chunk + 1)
    # Queda al menos el último chunk sin leer.
    assert upload._b.read() != b""
