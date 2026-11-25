"""Insert a blank reverse side after each PDF page."""
import sys
from pathlib import Path
from copy import deepcopy
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject


def convert(source):
    source = Path(source)
    if source.suffix.lower() != '.pdf' or not source.is_file():
        raise ValueError('Please supply an existing PDF file.')
    clean_prefix = f'_BE_{source.stem.replace( " ", "_")}.pdf'
    output = source.with_name(f'{clean_prefix}.pdf')
    i = 2
    while output.exists():
        output = source.with_name(f'{clean_prefix}_{i}.pdf')
        i += 1
    reader = PdfReader(source)
    if reader.is_encrypted and not reader.decrypt(''):
        raise ValueError('Password-protected PDF is not supported.')
    writer = PdfWriter()
    writer.append(reader)
    for i in range(len(reader.pages)-1, -1, -1):
        page = writer.pages[i]
        blank = writer.insert_blank_page(width=float(page.mediabox.width), height=float(page.mediabox.height), index=i+1)
        for key in ('/MediaBox', '/CropBox', '/TrimBox', '/BleedBox', '/ArtBox', '/Rotate', '/UserUnit'):
            if key in page:
                blank[NameObject(key)] = deepcopy(page[key])
    try:
        with output.open('xb') as f:
            writer.write(f)
    except Exception:
        # Leave any partial output visible for troubleshooting.
        raise
    return output

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Drag PDF files onto the BAT launcher.')
    for filename in sys.argv[1:]:
        try:
            print('Created:', convert(filename))
        except Exception as exc:
            print(f'ERROR: {filename}: {exc}')
