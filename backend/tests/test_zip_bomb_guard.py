"""Guard anti zip-bomb de extract_zip_entries (file-ops puro, sin DB)."""

import io
import zipfile

import pytest

from app.services.documents._file_ops import MAX_ZIP_ENTRIES, extract_zip_entries


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries.items():
            z.writestr(name, data)
    return buf.getvalue()


def test_normal_zip_extracts_ok():
    payload = _zip_bytes({"a.txt": b"hello", "b.txt": b"world"})
    names = sorted(n for n, _, _ in extract_zip_entries(payload))
    assert names == ["a.txt", "b.txt"]


def test_zip_bomb_oversized_entry_rejected():
    # 60MB de ceros: comprime a unos pocos KB pero descomprime más allá del cap de 50MB.
    bomb = _zip_bytes({"bomb.txt": b"\0" * (60 * 1024 * 1024)})
    with pytest.raises(ValueError):
        extract_zip_entries(bomb)


def test_zip_too_many_entries_rejected():
    many = {f"f{i}.txt": b"x" for i in range(MAX_ZIP_ENTRIES + 1)}
    with pytest.raises(ValueError):
        extract_zip_entries(_zip_bytes(many))
