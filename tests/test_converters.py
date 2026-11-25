"""
Office dispatch, missing converters, and LibreOffice rendering when installed.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from pypdf import PdfReader

from blank_evens.converters import (
    BlankEvensError,
    convert_document,
    render_office,
)
from blank_evens.converters import _render_with_office
from tests.office_files import (
    write_docx,
    write_pptx,
)
from tests.pdfutil import write_simple_pdf


def test_excel_and_unknown_types_are_rejected( tmp_path : Path) -> None :
    """
    Excel is out of scope, and other suffixes are unsupported
    """
    
    workbook = tmp_path / "sheet.xlsx"
    workbook.write_bytes(b"not a workbook")
    notes = tmp_path / "notes.txt"
    notes.write_bytes(b"hello")
    
    with pytest.raises( BlankEvensError, match = "out of scope") :
        convert_document(workbook)
    with pytest.raises( BlankEvensError, match = "Unsupported type") :
        convert_document(notes)


def test_pdf_dispatch_matches_the_pdf_tool( tmp_path : Path) -> None :
    """
    A PDF sent through the dispatcher uses the same blank-page result
    """
    
    source = tmp_path / "document.pdf"
    write_simple_pdf( source, [ "Alpha", "Beta" ])
    
    output = convert_document(source)
    reader = PdfReader(output)
    
    assert len(reader.pages) == 4
    assert output.name == "document_blank_evens.pdf"


def test_missing_converter_explains_how_to_install(
    tmp_path    : Path,
    monkeypatch : pytest.MonkeyPatch,
) -> None :
    """
    Without LibreOffice or Office, the error tells the user what to install
    """
    
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(shutil, "which", lambda _name : None)
    source = tmp_path / "note.docx"
    source.write_bytes(b"not a document")
    
    with pytest.raises( BlankEvensError, match = "LibreOffice") :
        convert_document(source)


def test_office_com_is_windows_only( tmp_path : Path) -> None :
    """
    The COM adapter refuses to start on other operating systems
    """
    
    if sys.platform == "win32" :
        pytest.skip("Windows can attempt the Office COM adapter")
    
    with pytest.raises( BlankEvensError, match = "only available on Windows") :
        _render_with_office( tmp_path / "note.docx", tmp_path)


def test_libreoffice_failure_is_actionable(
    tmp_path    : Path,
    monkeypatch : pytest.MonkeyPatch,
) -> None :
    """
    A failed renderer mentions passwords, signatures, and the converter text
    """
    
    monkeypatch.setattr(shutil, "which", lambda _name : "soffice")
    
    def failed_run( *args, **kwargs) :
        return subprocess.CompletedProcess( args, 1, "", "load failed")
    
    monkeypatch.setattr(subprocess, "run", failed_run)
    source = tmp_path / "note.docx"
    source.write_bytes(b"not a document")
    work = tmp_path / "work"
    work.mkdir()
    
    with pytest.raises( BlankEvensError, match = "password-protected") as raised :
        render_office( source, work)
    
    assert "load failed" in str(raised.value)
    assert "digital signatures" in str(raised.value)


def test_libreoffice_timeout(
    tmp_path    : Path,
    monkeypatch : pytest.MonkeyPatch,
) -> None :
    """
    A hung renderer is stopped and reported
    """
    
    monkeypatch.setattr(shutil, "which", lambda _name : "soffice")
    
    def hung_run( *args, **kwargs) :
        raise subprocess.TimeoutExpired( cmd = "soffice", timeout = 180)
    
    monkeypatch.setattr(subprocess, "run", hung_run)
    source = tmp_path / "note.docx"
    source.write_bytes(b"not a document")
    work = tmp_path / "work"
    work.mkdir()
    
    with pytest.raises( BlankEvensError, match = "stopped") :
        render_office( source, work)


@pytest.mark.skipif(
    shutil.which("soffice") is None and shutil.which("libreoffice") is None,
    reason = "LibreOffice is not installed",
)
def test_docx_and_pptx_gain_blank_reverses( tmp_path : Path) -> None :
    """
    Rendered Word pages and PowerPoint slides each get a blank reverse
    """
    
    document = tmp_path / "letter.docx"
    deck     = tmp_path / "deck.pptx"
    write_docx( document, "Hello bank")
    write_pptx( deck, [ "Slide one", "Slide two" ])
    document_bytes = document.read_bytes()
    deck_bytes     = deck.read_bytes()
    
    document_out = convert_document(document)
    deck_out     = convert_document(deck)
    document_pdf = PdfReader(document_out)
    deck_pdf     = PdfReader(deck_out)
    
    assert document_out.name == "letter_blank_evens.pdf"
    assert len(document_pdf.pages) % 2 == 0
    assert "hellobank" in _compact(document_pdf.pages[0])
    assert document_pdf.pages[1].get_contents() is None
    assert len(deck_pdf.pages) == 4
    assert "slideone" in _compact(deck_pdf.pages[0])
    assert "slidetwo" in _compact(deck_pdf.pages[2])
    assert deck_pdf.pages[1].get_contents() is None
    assert deck_pdf.pages[3].get_contents() is None
    assert document.read_bytes() == document_bytes
    assert deck.read_bytes() == deck_bytes
    names = { path.name for path in tmp_path.iterdir() }
    assert names == {
        "letter.docx",
        "letter_blank_evens.pdf",
        "deck.pptx",
        "deck_blank_evens.pdf",
    }


def _compact( page) -> str :
    """
    Page text with whitespace removed, so LibreOffice line breaks do not matter
    """
    
    return "".join((page.extract_text() or "").split()).lower()
