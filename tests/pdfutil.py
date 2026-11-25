"""
Synthetic PDFs for tests. Nothing here is a real bank or identity document.
"""

from pathlib import Path

from pypdf import PdfWriter
from pypdf.annotations import Text
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
    RectangleObject,
    TextStringObject,
)


def write_simple_pdf(
    path   : Path,
    texts  : list[str],
    sizes  : list[tuple[ float, float]] | None = None,
) -> None :
    """
    Write one page per text string, using Helvetica and the given page sizes
    """
    
    writer = PdfWriter()
    sizes  = sizes or [ ( 200.0, 300.0) for _text in texts ]
    
    for text, (width, height) in zip( texts, sizes, strict = True) :
        page = writer.add_blank_page( width = width, height = height)
        _draw_text( page, text)
    
    with path.open("wb") as handle :
        writer.write(handle)


def write_rich_pdf( path : Path) -> None :
    """
    Write a two-page PDF with geometry, a note, a field, a bookmark, and a title
    """
    
    writer = PdfWriter()
    first  = writer.add_blank_page( width = 200, height = 300)
    second = writer.add_blank_page( width = 400, height = 100)
    _draw_text( first, "Alpha")
    _draw_text( second, "Beta")
    first.rotate(90)
    first.cropbox  = RectangleObject([ 10, 20, 180, 280])
    first.trimbox  = RectangleObject([ 12, 22, 170, 270])
    first.bleedbox = RectangleObject([ 8, 18, 190, 290])
    first.artbox   = RectangleObject([ 15, 25, 160, 260])
    first[NameObject("/UserUnit")] = NumberObject(2)
    writer.add_annotation(
        page_number = 0,
        annotation  = Text( rect = ( 40, 40, 80, 80), text = "note"),
    )
    _add_text_field( writer, first, "Name", "Ada")
    writer.add_outline_item( title = "Chap", page_number = 0)
    writer.add_metadata({ "/Title" : "Probe", "/Author" : "Blank" })
    
    with path.open("wb") as handle :
        writer.write(handle)


def _draw_text( page, text : str) -> None :
    """
    Draw one Helvetica string. The text must not contain parentheses or backslashes.
    """
    
    font = DictionaryObject({
        NameObject("/Type")     : NameObject("/Font"),
        NameObject("/Subtype")  : NameObject("/Type1"),
        NameObject("/BaseFont") : NameObject("/Helvetica"),
    })
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font") : DictionaryObject({
            NameObject("/F1") : font,
        }),
    })
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 24 Tf 72 72 Td ({text}) Tj ET".encode())
    page[NameObject("/Contents")] = stream


def _add_text_field( writer : PdfWriter, page, name : str, value : str) -> None :
    """
    Add one text widget and register it on the page and in AcroForm
    """
    
    field = DictionaryObject({
        NameObject("/FT")      : NameObject("/Tx"),
        NameObject("/T")       : TextStringObject(name),
        NameObject("/V")       : TextStringObject(value),
        NameObject("/Subtype") : NameObject("/Widget"),
        NameObject("/Type")    : NameObject("/Annot"),
        NameObject("/Rect")    : RectangleObject([ 50, 50, 160, 80]),
        NameObject("/F")       : NumberObject(4),
    })
    reference = writer._add_object(field)
    annots    = page.get("/Annots")
    if annots is None :
        page[NameObject("/Annots")] = ArrayObject([ reference ])
    else :
        annots.append(reference)
    
    form = DictionaryObject({
        NameObject("/Fields") : ArrayObject([ reference ]),
    })
    writer._root_object[NameObject("/AcroForm")] = writer._add_object(form)
