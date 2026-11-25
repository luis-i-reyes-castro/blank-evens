"""
Regression tests for the PDF blank-reverse operation.
"""

import os
from pathlib import Path

import pytest
from pypdf import (
    PdfReader,
    PdfWriter,
)

from blank_evens.pdf import (
    BlankEvensError,
    convert,
)
from tests.pdfutil import (
    write_rich_pdf,
    write_simple_pdf,
)


def test_page_count_order_and_blank_reverses( tmp_path : Path) -> None :
    """
    N source pages become 2N pages, alternating content and a blank reverse
    """
    
    source = tmp_path / "document.pdf"
    write_simple_pdf(
        source,
        [ "Alpha", "Beta" ],
        [ ( 200, 300), ( 400, 100) ],
    )
    original = source.read_bytes()
    
    output = convert(source)
    reader = PdfReader(output)
    
    assert output.name == "document_blank_evens.pdf"
    assert len(reader.pages) == 4
    assert _text(reader.pages[0]) == "Alpha"
    assert _text(reader.pages[2]) == "Beta"
    assert _is_blank(reader.pages[1])
    assert _is_blank(reader.pages[3])
    assert list(reader.pages[1].mediabox) == list(reader.pages[0].mediabox)
    assert list(reader.pages[3].mediabox) == list(reader.pages[2].mediabox)
    assert source.read_bytes() == original
    assert [ path.name for path in tmp_path.iterdir() if path != source ] == [
        output.name,
    ]


def test_one_page_and_many_pages( tmp_path : Path) -> None :
    """
    One page and five pages both keep odd/even order
    """
    
    single = tmp_path / "single.pdf"
    write_simple_pdf( single, [ "Only" ])
    single_out = PdfReader(convert(single))
    assert len(single_out.pages) == 2
    assert _text(single_out.pages[0]) == "Only"
    assert _is_blank(single_out.pages[1])
    
    many = tmp_path / "many.pdf"
    labels = [ "P1", "P2", "P3", "P4", "P5" ]
    write_simple_pdf( many, labels)
    many_out = PdfReader(convert(many))
    assert len(many_out.pages) == 10
    for index, label in enumerate(labels) :
        assert _text(many_out.pages[index * 2]) == label
        assert _is_blank(many_out.pages[index * 2 + 1])


def test_geometry_annotations_forms_outline_and_metadata( tmp_path : Path) -> None :
    """
    Blank reverses inherit geometry, and source-page extras stay on the odd pages
    """
    
    source = tmp_path / "rich.pdf"
    write_rich_pdf(source)
    
    reader = PdfReader(convert(source))
    content = reader.pages[0]
    blank   = reader.pages[1]
    
    assert len(reader.pages) == 4
    assert content.rotation == 90
    assert blank.rotation == 90
    assert list(blank.cropbox) == list(content.cropbox)
    assert list(blank.trimbox) == list(content.trimbox)
    assert list(blank.bleedbox) == list(content.bleedbox)
    assert list(blank.artbox) == list(content.artbox)
    assert int(blank["/UserUnit"]) == 2
    assert content.get("/Annots") is not None
    assert blank.get("/Annots") is None
    assert reader.pages[3].get("/Annots") is None
    assert reader.metadata is not None
    assert reader.metadata["/Title"] == "Probe"
    assert reader.get_fields()["Name"]["/V"] == "Ada"
    outline_page = reader.outline[0]["/Page"].get_object()
    assert outline_page == content.get_object()


def test_names_do_not_overwrite_or_double_the_suffix( tmp_path : Path) -> None :
    """
    Collisions use _2, _3, and never replace an existing file or the source
    """
    
    source = tmp_path / "document.pdf"
    write_simple_pdf( source, [ "Alpha" ])
    taken = tmp_path / "document_blank_evens.pdf"
    taken.write_bytes(b"keep")
    also = tmp_path / "document_blank_evens_2.pdf"
    also.write_bytes(b"keep2")
    
    output = convert(source)
    
    assert output.name == "document_blank_evens_3.pdf"
    assert not output.name.endswith(".pdf.pdf")
    assert taken.read_bytes() == b"keep"
    assert also.read_bytes() == b"keep2"
    assert source.read_bytes() != output.read_bytes()


def test_unicode_and_spaces_in_the_path( tmp_path : Path) -> None :
    """
    Spaces and non-ASCII characters stay in the folder and the file stem
    """
    
    folder = tmp_path / "carpeta con espacio"
    folder.mkdir()
    source = folder / "página.pdf"
    write_simple_pdf( source, [ "Hola" ])
    
    output = convert(source)
    
    assert output.parent == folder
    assert output.name == "página_blank_evens.pdf"
    assert _text(PdfReader(output).pages[0]) == "Hola"


def test_output_directory( tmp_path : Path) -> None :
    """
    --output-dir receives the PDF and the source folder gains nothing new
    """
    
    source = tmp_path / "document.pdf"
    write_simple_pdf( source, [ "Alpha" ])
    destination = tmp_path / "out"
    
    output = convert( source, output_dir = destination)
    
    assert output == destination / "document_blank_evens.pdf"
    assert list(tmp_path.glob("*.pdf")) == [ source ]


def test_empty_zero_page_malformed_and_encrypted( tmp_path : Path) -> None :
    """
    Unreadable PDFs raise an actionable error and do not leave an output
    """
    
    empty = tmp_path / "empty.pdf"
    empty.write_bytes(b"")
    with pytest.raises( BlankEvensError, match = "empty") :
        convert(empty)
    
    zero = tmp_path / "zero.pdf"
    with zero.open("wb") as handle :
        PdfWriter().write(handle)
    with pytest.raises( BlankEvensError, match = "no pages") :
        convert(zero)
    
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"this is not a pdf")
    with pytest.raises( BlankEvensError, match = "not a readable PDF") :
        convert(broken)
    
    secret = tmp_path / "secret.pdf"
    _write_encrypted( secret, "hunter2")
    with pytest.raises( BlankEvensError, match = "password-protected") :
        convert(secret)
    
    openable = tmp_path / "openable.pdf"
    _write_encrypted( openable, "")
    assert len(PdfReader(convert(openable)).pages) == 2
    produced = sorted(path.name for path in tmp_path.glob("*_blank_evens.pdf"))
    assert produced == [ "openable_blank_evens.pdf" ]


def test_failed_write_leaves_no_partial( tmp_path : Path, monkeypatch) -> None :
    """
    A crash while writing removes the temp file and does not publish an output
    """
    
    source = tmp_path / "document.pdf"
    write_simple_pdf( source, [ "Alpha" ])
    
    def boom( self, stream) -> None :
        raise OSError("disk full")
    
    monkeypatch.setattr( "blank_evens.pdf.PdfWriter.write", boom)
    
    with pytest.raises( OSError, match = "disk full") :
        convert(source)
    
    assert [ path.name for path in tmp_path.iterdir() ] == [ "document.pdf" ]


@pytest.mark.skipif(
    os.name == "nt" or getattr( os, "geteuid", lambda : 0)() == 0,
    reason = "This process can still read or write mode 000.",
)
def test_permission_errors( tmp_path : Path) -> None :
    """
    Unreadable files and unwritable folders name the permission problem
    """
    
    source = tmp_path / "document.pdf"
    write_simple_pdf( source, [ "Alpha" ])
    source.chmod(0)
    
    try :
        with pytest.raises( BlankEvensError, match = "Cannot read") :
            convert(source)
    finally :
        source.chmod(0o644)
    
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o555)
    
    try :
        with pytest.raises( BlankEvensError, match = "Cannot write") :
            convert( source, output_dir = locked)
    finally :
        locked.chmod(0o755)


def _text( page) -> str :
    """
    Extracted page text without surrounding whitespace
    """
    
    return (page.extract_text() or "").strip()


def _is_blank( page) -> bool :
    """
    A reverse is blank when it has no content stream, text, or annotations
    """
    
    return (
        page.get_contents() is None
        and page.get("/Annots") is None
        and _text(page) == ""
    )


def _write_encrypted( path : Path, user_password : str) -> None :
    """
    Write a one-page PDF encrypted with the given user password
    """
    
    writer = PdfWriter()
    writer.add_blank_page( width = 200, height = 300)
    writer.encrypt( user_password = user_password, owner_password = "owner-secret")
    
    with path.open("wb") as handle :
        writer.write(handle)
