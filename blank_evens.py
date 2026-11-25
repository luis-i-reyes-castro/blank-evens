"""
Insert a blank reverse side after each PDF page.
"""

import sys


try :
    from blank_evens.cli import main

except ModuleNotFoundError as exc :
    
    if exc.name == "pypdf" :
        sys.stderr.write(
            "pypdf is not installed for this Python.\n"
            "Windows: double-click install_windows.bat\n"
            "macOS:   double-click install_macos.command\n"
            "Linux:   python3 -m venv .venv && "
            ".venv/bin/python -m pip install .\n"
        )
        raise SystemExit(1)
    
    raise


if __name__ == "__main__"  :
    raise SystemExit(main())
