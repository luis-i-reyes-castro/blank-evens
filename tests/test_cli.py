"""
Command-line exit codes, help, and multi-file summaries.
"""

from pathlib import Path

import pytest

from blank_evens.cli import (
    EXIT_FAILURE,
    EXIT_OK,
    EXIT_USAGE,
    run,
)
from tests.pdfutil import write_simple_pdf


def test_help_and_version() -> None :
    """
    Help and version exit successfully
    """
    
    with pytest.raises(SystemExit) as help_exit :
        run([ "--help" ])
    with pytest.raises(SystemExit) as version_exit :
        run([ "--version" ])
    
    assert help_exit.value.code == 0
    assert version_exit.value.code == 0


def test_usage_without_files( capsys : pytest.CaptureFixture[str]) -> None :
    """
    No paths prints help and returns the usage status
    """
    
    assert run([]) == EXIT_USAGE
    captured = capsys.readouterr()
    assert "blank-evens" in captured.err
    assert captured.out == ""


def test_several_files_and_a_failure(
    tmp_path : Path,
    capsys   : pytest.CaptureFixture[str],
) -> None :
    """
    Good files are written, a bad file is reported, and the status is failure
    """
    
    first  = tmp_path / "one.pdf"
    second = tmp_path / "two.pdf"
    broken = tmp_path / "broken.pdf"
    write_simple_pdf( first, [ "One" ])
    write_simple_pdf( second, [ "Two" ])
    broken.write_bytes(b"nope")
    destination = tmp_path / "printed"
    
    status = run([
        str(first),
        str(broken),
        str(second),
        "--output-dir",
        str(destination),
    ])
    captured = capsys.readouterr()
    
    assert status == EXIT_FAILURE
    assert (destination / "one_blank_evens.pdf").is_file()
    assert (destination / "two_blank_evens.pdf").is_file()
    assert "ERROR:" in captured.err
    assert "2 created, 1 failed." in captured.out
    assert "[1/3]" in captured.out


def test_success_status( tmp_path : Path, capsys : pytest.CaptureFixture[str]) -> None :
    """
    A single good PDF exits 0 and prints the created path
    """
    
    source = tmp_path / "document.pdf"
    write_simple_pdf( source, [ "Alpha" ])
    
    assert run([ str(source) ]) == EXIT_OK
    captured = capsys.readouterr()
    assert "document_blank_evens.pdf" in captured.out
    assert "1 created, 0 failed." in captured.out
