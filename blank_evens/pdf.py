"""
Insert a blank reverse side after each page of a PDF.
"""

import os
import tempfile
from copy import deepcopy
from pathlib import Path

from pypdf import (
    PdfReader,
    PdfWriter,
)
from pypdf.errors import (
    EmptyFileError,
    PdfReadError,
    PyPdfError,
)
from pypdf.generic import NameObject


PAGE_BOX_KEYS = (
    "/MediaBox",
    "/CropBox",
    "/TrimBox",
    "/BleedBox",
    "/ArtBox",
    "/Rotate",
    "/UserUnit",
)
""" Page geometry copied from each source page onto its blank reverse. """

_NAME_TRIES = 10_000
""" How many collision suffixes to try before giving up. """


class BlankEvensError(Exception) :
    """ A conversion failure with a message meant for the user. """


def convert(
    source      : Path | str,
    output_dir  : Path | str | None = None,
    output_stem : str | None        = None,
) -> Path :
    """
    Write a new PDF with a blank page after each source page \\
    Args:
        source      : Existing PDF. The file is only read.
        output_dir  : Destination folder. Defaults to the source file's folder.
        output_stem : Output filename stem. Defaults to the source stem.
    Returns:
        Path of the new PDF. Existing files are never overwritten.
    Raises:
        BlankEvensError: The PDF cannot be read, or the output cannot be published.
    """
    
    source    = Path(source)
    reader    = _open_reader(source)
    directory = _output_directory( source, output_dir)
    stem      = output_stem if output_stem is not None else source.stem
    writer    = _with_blank_reverses(reader)
    
    return _write_atomically( writer, directory, stem)


def _output_directory( source : Path, output_dir : Path | str | None) -> Path :
    """
    Resolve the folder that will receive the finished PDF
    """
    
    if output_dir is None :
        if not source.exists() :
            raise BlankEvensError(f"File not found: {source}")
        if not source.is_file() :
            raise BlankEvensError(f"Not a file: {source}")
        
        return source.parent
    
    directory = Path(output_dir)
    if directory.exists() and not directory.is_dir() :
        raise BlankEvensError(f"Output path is not a directory: {directory}")
    
    try :
        directory.mkdir( parents = True, exist_ok = True)
    except PermissionError :
        raise BlankEvensError(
            f"Cannot create the output directory {directory}. "
            "Check the folder permissions."
        ) from None
    except OSError as exc :
        raise BlankEvensError(
            f"Cannot create the output directory {directory}. {exc.strerror or exc}"
        ) from None
    
    return directory


def _open_reader( source : Path) -> PdfReader :
    """
    Open a PDF, including files whose user password is empty \\
    Raises:
        BlankEvensError: The file is unreadable, empty, encrypted, or has no pages.
    """
    
    if not source.exists() :
        raise BlankEvensError(f"File not found: {source}")
    if not source.is_file() :
        raise BlankEvensError(f"Not a file: {source}")
    if source.suffix.lower() != ".pdf" :
        raise BlankEvensError(
            f"{source.name} is not a PDF. "
            "Word and PowerPoint files need the blank-evens command."
        )
    
    try :
        reader = PdfReader(source)
    except PermissionError :
        raise BlankEvensError(
            f"Cannot read {source}. Check the file permissions."
        ) from None
    except EmptyFileError :
        raise BlankEvensError(f"{source.name} is empty.") from None
    except PdfReadError as exc :
        raise BlankEvensError(f"{source.name} is not a readable PDF. {exc}") from None
    except OSError as exc :
        raise BlankEvensError(
            f"Cannot read {source}. {exc.strerror or exc}"
        ) from None
    
    if reader.is_encrypted and reader.decrypt("") == 0 :
        raise BlankEvensError(
            f"{source.name} is password-protected. Remove the password and try again."
        )
    if len(reader.pages) == 0 :
        raise BlankEvensError(f"{source.name} has no pages.")
    
    return reader


def _with_blank_reverses( reader : PdfReader) -> PdfWriter :
    """
    Copy the document and insert an empty page after each source page
    """
    
    writer = PdfWriter()
    
    try :
        writer.append(reader)
    except PyPdfError as exc :
        raise BlankEvensError(f"Could not copy the PDF. {exc}") from None
    
    _copy_metadata( reader, writer)
    
    for index in range( len(writer.pages) - 1, -1, -1) :
        source_page = writer.pages[index]
        
        try :
            writer.insert_blank_page(
                width  = float(source_page.mediabox.width),
                height = float(source_page.mediabox.height),
                index  = index + 1,
            )
        except PyPdfError as exc :
            raise BlankEvensError(
                f"Could not insert a blank page after page {index + 1}. {exc}"
            ) from None
        
        # The object returned by insert_blank_page is not the page kept in the writer.
        _copy_geometry( source_page, writer.pages[index + 1])
    
    return writer


def _copy_metadata( reader : PdfReader, writer : PdfWriter) -> None :
    """
    Copy the document info dictionary onto the new PDF
    """
    
    if reader.metadata is None :
        return
    
    infos = {
        str(key) : str(value)
        for key, value in reader.metadata.items()
        if value is not None
    }
    if not infos :
        return
    
    writer.add_metadata(infos)


def _copy_geometry( source_page, blank_page) -> None :
    """
    Give the blank page the source page's boxes, rotation, and user unit
    """
    
    for key in PAGE_BOX_KEYS :
        if key in source_page :
            blank_page[NameObject(key)] = deepcopy(source_page[key])


def _write_atomically( writer : PdfWriter, directory : Path, stem : str) -> Path :
    """
    Write to a sibling temp file and publish it only after the write succeeds \\
    Returns:
        The final PDF path. Partial files are removed when writing fails.
    """
    
    try :
        handle, name = tempfile.mkstemp(
            prefix = f".{stem}_blank_evens.",
            suffix = ".partial",
            dir    = directory,
        )
    except PermissionError :
        raise BlankEvensError(
            f"Cannot write in {directory}. Check the folder permissions."
        ) from None
    except OSError as exc :
        raise BlankEvensError(
            f"Cannot write in {directory}. {exc.strerror or exc}"
        ) from None
    
    os.close(handle)
    tmp = Path(name)
    
    try :
        with tmp.open("wb") as out :
            writer.write(out)
        
        return _publish( tmp, directory, stem)
    except Exception :
        tmp.unlink(missing_ok = True)
        raise


def _publish( tmp : Path, directory : Path, stem : str) -> Path :
    """
    Place the temp PDF under the first free ``stem_blank_evens`` name \\
    Returns:
        The published path. The temp name is removed.
    Raises:
        BlankEvensError: No free name remains, or the folder rejects the file.
    """
    
    for number in range( 1, _NAME_TRIES + 1) :
        dest = _candidate( directory, stem, number)
        
        try :
            if os.name == "nt" :
                os.rename( tmp, dest)
            else :
                os.link( tmp, dest)
                tmp.unlink()
        except FileExistsError :
            continue
        except OSError as exc :
            raise BlankEvensError(
                f"Cannot create {dest}. {exc.strerror or exc}"
            ) from None
        
        return dest
    
    tmp.unlink(missing_ok = True)
    raise BlankEvensError(
        f"Could not find a free name for {stem}_blank_evens.pdf in {directory}."
    )


def _candidate( directory : Path, stem : str, number : int) -> Path :
    """
    Build ``stem_blank_evens.pdf``, or ``stem_blank_evens_N.pdf`` after a collision
    """
    
    if number == 1 :
        name = f"{stem}_blank_evens.pdf"
    else :
        name = f"{stem}_blank_evens_{number}.pdf"
    
    return directory / name
