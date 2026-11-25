"""
Render Word and PowerPoint files to PDF, then insert blank reverses.

PDF files stay inside pypdf and do not need Office or LibreOffice.
``.docx`` and ``.pptx`` (and legacy ``.doc`` / ``.ppt``) are rendered to PDF
in a temporary directory, then passed through the same blank-page operation.
On Windows the renderer is Microsoft Word or PowerPoint via COM when pywin32
and Office are installed, and LibreOffice otherwise.
On Linux and macOS the renderer is a headless LibreOffice (``soffice``).
Excel workbooks are rejected. Their printed pagination is not a page list.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from blank_evens.pdf import (
    BlankEvensError,
    convert as convert_pdf,
)


WORD_SUFFIXES = { ".doc", ".docx" }
""" Word formats sent to Word or LibreOffice. """

SLIDE_SUFFIXES = { ".ppt", ".pptx" }
""" Slide formats sent to PowerPoint or LibreOffice. """

EXCEL_SUFFIXES = { ".xls", ".xlsx", ".xlsm" }
""" Rejected on purpose. Spreadsheet pagination is not a page sequence. """

OFFICE_SUFFIXES = WORD_SUFFIXES | SLIDE_SUFFIXES
""" Office formats rendered to PDF before the blank-page step. """

_CONVERT_TIMEOUT_SECONDS = 180
""" How long an external renderer may run before it is stopped. """


def convert_document(
    source     : Path | str,
    output_dir : Path | str | None = None,
) -> Path :
    """
    Insert blank reverses into a PDF, or into a PDF rendered from Office \\
    Args:
        source     : ``.pdf``, ``.doc``, ``.docx``, ``.ppt``, or ``.pptx``.
        output_dir : Destination folder. Defaults to the source file's folder.
    Returns:
        Path of the new PDF. The source file is not modified.
    Raises:
        BlankEvensError: The type is unsupported, or rendering or writing failed.
    """
    
    source = Path(source)
    suffix = source.suffix.lower()
    
    if suffix in EXCEL_SUFFIXES :
        raise BlankEvensError(
            "Excel workbooks are out of scope. "
            "Export a PDF from Excel, then run blank-evens on that PDF."
        )
    if suffix == ".pdf" :
        return convert_pdf( source, output_dir = output_dir)
    if suffix not in OFFICE_SUFFIXES :
        shown = source.suffix or source.name
        raise BlankEvensError(
            f"Unsupported type '{shown}'. "
            "Use a PDF, or a Word/PowerPoint file when a converter is installed."
        )
    
    beside = source.parent if output_dir is None else output_dir
    
    with tempfile.TemporaryDirectory(prefix = "blank-evens-") as tmp :
        rendered = render_office( source, Path(tmp))
        
        return convert_pdf(
            rendered,
            output_dir  = beside,
            output_stem = source.stem,
        )


def render_office( source : Path, work : Path) -> Path :
    """
    Render one Office document to a PDF inside ``work`` \\
    Returns:
        The rendered PDF. It is a temporary file, not the blank-evens result.
    Raises:
        BlankEvensError: No converter is installed, or the converter failed.
    """
    
    if not source.exists() :
        raise BlankEvensError(f"File not found: {source}")
    if not source.is_file() :
        raise BlankEvensError(f"Not a file: {source}")
    
    failures : list[str] = []
    
    if sys.platform == "win32" :
        try :
            return _render_with_office( source, work)
        except BlankEvensError as exc :
            failures.append(str(exc))
        except OSError as exc :
            failures.append(
                f"Microsoft Office export failed. {exc.strerror or exc}"
            )
        except Exception as exc :
            # pywin32 raises COM errors that are not OSError subclasses.
            failures.append(f"Microsoft Office export failed. {exc}")
    
    try :
        return _render_with_libreoffice( source, work)
    except BlankEvensError as exc :
        failures.append(str(exc))
    
    if not failures :
        failures.append(missing_converter_message(source))
    
    raise BlankEvensError(" ".join(failures))


def missing_converter_message( source : Path) -> str :
    """
    Explain which optional program can render this file
    """
    
    if sys.platform == "win32" :
        return (
            f"No converter found for {source.name}. "
            "Install Word or PowerPoint plus pywin32 (`pip install pywin32`), "
            "or install LibreOffice. PDF files do not need either program."
        )
    
    return (
        f"No converter found for {source.name}. "
        "Install LibreOffice so `soffice` is on PATH. "
        "PDF files do not need LibreOffice."
    )


def _render_with_libreoffice( source : Path, work : Path) -> Path :
    """
    Convert with a headless LibreOffice process \\
    Raises:
        BlankEvensError: LibreOffice is missing, hangs, or rejects the document.
    """
    
    binary = shutil.which("libreoffice") or shutil.which("soffice")
    if binary is None :
        raise BlankEvensError(missing_converter_message(source))
    
    staged  = work / f"input{source.suffix.lower()}"
    profile = work / "profile"
    dest    = work / "input.pdf"
    shutil.copyfile( source, staged)
    command = [
        binary,
        f"-env:UserInstallation={profile.as_uri()}",
        "--headless",
        "--norestore",
        "--nolockcheck",
        "--convert-to", "pdf",
        "--outdir", str(work),
        str(staged),
    ]
    
    try :
        completed = subprocess.run(
            command,
            capture_output = True,
            text           = True,
            timeout        = _CONVERT_TIMEOUT_SECONDS,
            check          = False,
        )
    except subprocess.TimeoutExpired :
        raise BlankEvensError(
            f"LibreOffice did not finish {source.name} "
            f"within {_CONVERT_TIMEOUT_SECONDS} seconds. The conversion was stopped."
        ) from None
    
    if completed.returncode != 0 or not dest.is_file() :
        detail = (completed.stderr or completed.stdout or "").strip()
        extra  = f" {detail}" if detail else ""
        raise BlankEvensError(
            f"LibreOffice could not convert {source.name}.{extra} "
            "If the document is password-protected, remove the password first. "
            "Conversion rewrites the file and drops digital signatures."
        )
    
    return dest


def _render_with_office( source : Path, work : Path) -> Path :
    """
    Export PDF through Word or PowerPoint COM on Windows \\
    Raises:
        BlankEvensError: Office or pywin32 is missing, or the export failed.
    """
    
    if sys.platform != "win32" :
        raise BlankEvensError("Microsoft Office export is only available on Windows.")
    
    try :
        import win32com.client
    except ImportError :
        raise BlankEvensError(
            "pywin32 is not installed. "
            "Install it with `pip install pywin32`, or install LibreOffice instead."
        ) from None
    
    dest   = work / "input.pdf"
    suffix = source.suffix.lower()
    
    try :
        if suffix in WORD_SUFFIXES :
            _export_word( win32com.client, source, dest)
        else :
            _export_powerpoint( win32com.client, source, dest)
    except BlankEvensError :
        raise
    except Exception as exc :
        raise BlankEvensError(
            f"Microsoft Office could not export {source.name}. {exc} "
            "If the document is password-protected, remove the password first. "
            "Exporting invalidates digital signatures."
        ) from None
    
    if not dest.is_file() :
        raise BlankEvensError(
            f"Microsoft Office did not produce a PDF for {source.name}."
        )
    
    return dest


def _export_word( win32com, source : Path, dest : Path) -> None :
    """
    Export one Word document to PDF without saving the document
    """
    
    word = win32com.DispatchEx("Word.Application")
    word.Visible       = False
    word.DisplayAlerts = 0
    
    try :
        # ConfirmConversions, ReadOnly, AddToRecentFiles. Read-only avoids a save.
        document = word.Documents.Open( str(source.resolve()), False, True, False)
        
        try :
            # 17 is wdExportFormatPDF.
            document.ExportAsFixedFormat( str(dest.resolve()), 17)
        finally :
            document.Close(0)
    finally :
        word.Quit()


def _export_powerpoint( win32com, source : Path, dest : Path) -> None :
    """
    Export one slide deck to PDF, one slide per page, without saving it
    """
    
    app = win32com.DispatchEx("PowerPoint.Application")
    
    try :
        # ReadOnly, Untitled, WithWindow.
        presentation = app.Presentations.Open(
            str(source.resolve()),
            True,
            False,
            False,
        )
        
        try :
            # 32 is ppSaveAsPDF. Slides stay in order, one page each.
            presentation.SaveAs( str(dest.resolve()), 32)
        finally :
            presentation.Close()
    finally :
        app.Quit()
