"""
Launcher quoting, shell syntax, and a POSIX smoke run.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.pdfutil import write_simple_pdf


ROOT = Path(__file__).resolve().parents[1]


def test_windows_launcher_quotes_each_path() -> None :
    """
    Drag-and-drop paths are passed as ``%~1``, not as an unquoted ``%*``
    """
    
    text = (ROOT / "blank_evens_in_pdf.bat").read_text(encoding = "utf-8")
    
    assert '"%~1"' in text
    assert "%*" not in text
    assert ".venv\\Scripts\\python.exe" in text
    assert "BLANK_EVENS_NO_PAUSE" in text


def test_shell_scripts_parse() -> None :
    """
    The POSIX launchers and the macOS installer are valid bash
    """
    
    bash = shutil.which("bash")
    if bash is None :
        pytest.skip("bash is not installed")
    
    scripts = [
        ROOT / "blank_evens.sh",
        ROOT / "blank_evens.command",
        ROOT / "install_macos.command",
    ]
    for script in scripts :
        subprocess.run( [ bash, "-n", str(script) ], check = True)


def test_installers_cover_python_and_the_dependency() -> None :
    """
    Windows and macOS installers both install Python when needed, then pip install
    """
    
    windows = (ROOT / "install_windows.ps1").read_text(encoding = "utf-8")
    macos   = (ROOT / "install_macos.command").read_text(encoding = "utf-8")
    
    assert "Python.Python.3.13" in windows
    assert "winget" in windows
    assert "-m pip install" in windows
    assert "pywin32" in windows
    assert "python@3.13" in macos
    assert "macos11.pkg" in macos
    assert "-m pip install" in macos
    assert "python3 -m venv" in (ROOT / "blank_evens.sh").read_text(encoding = "utf-8")


@pytest.mark.skipif( os.name == "nt", reason = "The shell launcher is POSIX.")
def test_shell_launcher_converts_a_pdf( tmp_path : Path) -> None :
    """
    blank_evens.sh converts a PDF whose folder and name contain spaces
    """
    
    folder = tmp_path / "my folder"
    folder.mkdir()
    source = folder / "my file.pdf"
    write_simple_pdf( source, [ "Alpha" ])
    
    completed = subprocess.run(
        [ "bash", str(ROOT / "blank_evens.sh"), str(source) ],
        check          = False,
        capture_output = True,
        text           = True,
    )
    
    assert completed.returncode == 0, completed.stderr
    assert (folder / "my file_blank_evens.pdf").is_file()


def test_script_entrypoint( tmp_path : Path) -> None :
    """
    ``python blank_evens.py document.pdf`` still works
    """
    
    source = tmp_path / "document.pdf"
    write_simple_pdf( source, [ "Alpha" ])
    
    completed = subprocess.run(
        [ sys.executable, str(ROOT / "blank_evens.py"), str(source) ],
        check          = False,
        capture_output = True,
        text           = True,
    )
    
    assert completed.returncode == 0, completed.stderr
    assert "document_blank_evens.pdf" in completed.stdout
    assert (tmp_path / "document_blank_evens.pdf").is_file()


def test_shell_launcher_requires_a_file() -> None :
    """
    The shell launcher exits 1 when it is started with no paths
    """
    
    if shutil.which("bash") is None :
        pytest.skip("bash is not installed")
    
    completed = subprocess.run(
        [ "bash", str(ROOT / "blank_evens.sh") ],
        check          = False,
        capture_output = True,
        text           = True,
    )
    
    assert completed.returncode == 1
    assert "Usage:" in completed.stderr
