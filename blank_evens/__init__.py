"""
Insert a blank reverse side after each page of a document.
"""

from blank_evens.cli import (
    __version__,
    main,
)
from blank_evens.pdf import (
    BlankEvensError,
    convert,
)


__all__ = [
    "BlankEvensError",
    "__version__",
    "convert",
    "main",
]
