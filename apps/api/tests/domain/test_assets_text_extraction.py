"""Unit tests for the PDF / utf-8 sniffing in AssetsService._download_as_text.

Avoids the full HTTP / DB stack — injects a minimal storage stub that returns
canned bytes for a known file_ref.
"""

from __future__ import annotations

from io import BytesIO

import pytest
from pypdf import PdfWriter

from app.domain.assets.service import AssetsService


class _StubStorage:
    def __init__(self, data: bytes) -> None:
        self._data = data

    async def download(self, _file_ref: str) -> bytes:
        return self._data


def _build_minimal_pdf_bytes(body_text: str) -> bytes:
    # pypdf can only *read* text it extracted; reliably encoding new text is
    # brittle without a layout engine. A blank page PDF is enough: the
    # test asserts we don't raw-decode the binary into replacement chars.
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


async def test_txt_file_returns_plain_utf8() -> None:
    storage = _StubStorage("你好 world\n第二行".encode("utf-8"))

    text = await AssetsService._download_as_text(storage, "resume.txt")

    assert text == "你好 world\n第二行"


async def test_utf8_decode_replaces_bad_bytes() -> None:
    storage = _StubStorage(b"hello\xffworld")

    text = await AssetsService._download_as_text(storage, "jd.txt")

    assert text.startswith("hello")
    assert "world" in text
    # Replacement char preserves length instead of raising.
    assert "�" in text


async def test_pdf_bytes_do_not_leak_raw_binary() -> None:
    """A blank-page PDF has no extractable text — but the important invariant
    is that we do NOT fall back to raw utf-8 decoding of the binary, because
    that is exactly what blew up the prod walkthrough (216k junk tokens)."""
    pdf_bytes = _build_minimal_pdf_bytes("")
    assert pdf_bytes.startswith(b"%PDF-")
    storage = _StubStorage(pdf_bytes)

    text = await AssetsService._download_as_text(storage, "resume.pdf")

    # Must not contain PDF structural tokens that would appear under a
    # raw-bytes decode (xref, obj, endstream, %%EOF, etc.).
    for sigil in ("%%EOF", "xref", "endobj", "/Type"):
        assert sigil not in text, f"raw PDF structure leaked: {sigil!r}"


async def test_corrupt_pdf_falls_back_to_decode() -> None:
    """If pypdf chokes on a malformed PDF, we still return *something* rather
    than bubble the PdfReadError — callers handle LLM context-length limits."""
    # Valid magic but junk body — pypdf will raise PdfReadError.
    storage = _StubStorage(b"%PDF-1.4\n<invalid stream>\n")

    text = await AssetsService._download_as_text(storage, "corrupt.pdf")

    # Fallback is the utf-8-replace decode of the original bytes. The
    # magic prefix is preserved verbatim because the `%`, `P`, `D`, `F`
    # characters are ASCII.
    assert text.startswith("%PDF-")
