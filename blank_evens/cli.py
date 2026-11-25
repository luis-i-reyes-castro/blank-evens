"""
Command-line interface for blank-evens.
"""

import argparse
import sys
from pathlib import Path

from blank_evens.converters import (
    OFFICE_SUFFIXES,
    convert_document,
)


__version__ = "0.1.0"
""" Program version shown by ``--version``. """

EXIT_OK = 0
""" Every input was converted. """

EXIT_USAGE = 1
""" The command line did not include a file. """

EXIT_FAILURE = 2
""" At least one input failed. """

_OFFICE_NOTE = (
    "Rendered to PDF first. Fonts, pagination, comments, and tracked changes "
    "can differ from Word or PowerPoint, and digital signatures are not kept."
)


def main( argv : list[str] | None = None) -> None :
    """
    Console entry point. The process status is the return code of ``run``.
    """
    
    raise SystemExit(run(argv))


def run( argv : list[str] | None = None) -> int :
    """
    Convert each path and print a short summary \\
    Returns:
        0 when every file succeeds, 1 when no files were given, 2 when any fail.
    """
    
    parser = _parser()
    args   = parser.parse_args(argv)
    
    if not args.paths :
        parser.print_help(sys.stderr)
        return EXIT_USAGE
    
    created = 0
    failed  = 0
    total   = len(args.paths)
    
    for index, path in enumerate( args.paths, start = 1) :
        if total > 1 :
            print(f"[{index}/{total}] {path}")
        
        try :
            output = convert_document( path, output_dir = args.output_dir)
        except Exception as exc :
            failed += 1
            print(f"ERROR: {path}: {exc}", file = sys.stderr)
            continue
        
        created += 1
        print(f"Created: {output}")
        if path.suffix.lower() in OFFICE_SUFFIXES :
            print(f"Note: {path.name}: {_OFFICE_NOTE}", file = sys.stderr)
    
    print(f"{created} created, {failed} failed.")
    
    if failed :
        return EXIT_FAILURE
    
    return EXIT_OK


def _parser() -> argparse.ArgumentParser :
    """
    Build the argument parser
    """
    
    parser = argparse.ArgumentParser(
        prog        = "blank-evens",
        description = (
            "Insert a blank reverse after each page so a duplex printer "
            "can leave the back of every sheet empty."
        ),
    )
    parser.add_argument(
        "paths",
        nargs = "*",
        type  = Path,
        help  = "PDF files, or Word/PowerPoint files when a converter is installed.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type = Path,
        help = "Folder for the new PDFs. Defaults to each input's own folder.",
    )
    parser.add_argument(
        "--version",
        action  = "version",
        version = f"blank-evens {__version__}",
    )
    
    return parser
