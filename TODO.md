# blank-evens — development plan

> **Because sometimes the solution to a printing problem is printing absolutely nothing.**

Repository: https://github.com/luis-i-reyes-castro/blank-evens

## The problem we're solving

An HP LaserJet Pro 400 Color MFP M475dn produced extremely pale text in *simplex* (single-sided) mode, but clearly legible text on **both** sides in duplex mode. The bank requires single-sided documents. The working workaround inserts an empty page after each original PDF page, then prints the resulting PDF **duplex**, yielding a printed front and an empty reverse on every sheet. The printer may sometimes skip truly blank sides; test that behavior with the actual printer. This is a workaround, not a general-purpose printer repair or a promise that every driver will behave the same way.

## Current state (verified from `main` on 2026-11-24)

- `blank_evens.py`: uses `pypdf`; accepts one or more PDF paths; inserts a blank after every page; preserves page boxes and rotation.
- `blank_evens_in_pdf.bat`: Windows drag-and-drop launcher; invokes `py -3`.
- `README.md`: humorous project introduction.
- `LICENSE`: present.
- **Not yet implemented:** Word, PowerPoint, Linux launcher, tests, packaged CLI, or automated conversions.
- **Known bug:** output path is built as `'_BE_<stem>.pdf'` and then adds **another** `.pdf`, producing a name ending in `.pdf.pdf`.
- **Known risk:** `.bat` uses `%*` without argument-by-argument quoting, so drag-and-drop paths containing spaces may be split.
- **Documentation discrepancy:** README currently claims Word/PowerPoint support. Clearly mark them **planned** until they actually work.

## Guiding decisions

- Primary, consistent output format: **PDF**, regardless of whether the input is `.pdf`, `.docx`, or `.pptx`.
- Keep inputs untouched; never silently overwrite an existing output.
- Keep all processing local, especially for bank/legal/confidential documents.
- Work on **Windows 10+ and Linux**. PDF processing should not require Microsoft Office or LibreOffice.
- Word/PowerPoint input may require an external renderer. Be explicit about that dependency and warn that conversion may change fidelity.
- Support legacy `.doc` and `.ppt` only if a robust converter is available; don't claim support prematurely.
- **Do not support Excel** (`.xlsx`/`.xls`) in this project: printed sheets have non-linear pagination and print-area complications.
- Avoid macros and VBA; prefer Python plus thin platform-specific launchers.

## Phase 0 — stabilize the proven PDF workflow (P0)

- [ ] Keep the existing `blank_evens.py` behavior working before refactoring; create a small regression fixture.
- [ ] Fix the doubled `.pdf.pdf` suffix and choose a consistent output convention, e.g. `document_blank_evens.pdf`.
- [ ] Make collision handling deterministic: `..._2.pdf`, `..._3.pdf`, etc.; never overwrite originals or existing outputs.
- [ ] Fix Windows drag-and-drop for paths containing spaces, Unicode, and multiple documents.
- [ ] Handle empty PDFs, malformed files, file permission failures, and encrypted PDFs with actionable errors.
- [ ] Write output to a temporary sibling file and atomically finalize, cleaning up partial artifacts on failure.
- [ ] Preserve original page contents and important page geometry: size, orientation, crop/trim/bleed/art boxes and rotation, including mixed-size PDFs.
- [ ] Check how annotations, form fields, bookmarks and metadata behave under `pypdf` and document any limitations; avoid making false preservation guarantees.
- [ ] Ensure blank even pages contain *no* content; add a test for exactly `2N` pages and correct odd/even ordering.
- [ ] Add `requirements.txt` or a minimal `pyproject.toml`, a `.gitignore` covering generated PDFs, caches and virtual environments.

### Phase 0 acceptance criteria

- `document.pdf` with N pages becomes a fresh PDF of 2N pages: odd pages retain the source content, even pages are blank and match their preceding page's dimensions/orientation.
- Existing outputs and source files remain untouched; error runs leave no misleading partial output.
- A PDF dragged onto the Windows launcher works even when both folder and filename contain spaces.

## Phase 1 — cross-platform CLI and Linux convenience (P1)

- [ ] Refactor to a small package or module structure without breaking `python blank_evens.py document.pdf`.
- [ ] Implement a CLI with `--help`, multiple input paths, output directory option, useful exit codes, and progress/error summaries.
- [ ] Add a POSIX shell launcher (`blank_evens.sh`) with safe quoting and Linux-friendly Python invocation.
- [ ] Keep the Windows BAT launcher; avoid requiring admin rights or an Office installation for PDF input.
- [ ] Document installation with a Python virtual environment (`python -m venv`) on both OSes and drag-and-drop/terminal examples.
- [ ] Optionally support drag-and-drop onto the Linux launcher in desktop environments that allow it; CLI is the guaranteed interface.

## Phase 2 — PowerPoint and Word input (P2)

- [ ] Make the supported-input dispatcher explicit: `.pdf` uses `pypdf`; `.docx` and `.pptx` are rendered to PDF first, then use the **same** blank-page operation.
- [ ] On Windows, prefer native PowerPoint/Word PDF export through Office COM **when Office is installed** (optional `pywin32`); do not require it for PDF-only users.
- [ ] On Linux, support a detected `libreoffice --headless` for `.docx` and `.pptx`; optionally provide a Windows LibreOffice fallback.
- [ ] Run converters in a separate temporary directory; prevent filename collisions and clean intermediates.
- [ ] Handle unavailable converters, hung/failed conversions, and documents with unsupported features with clear messages.
- [ ] Verify order/appearance of slides when exporting `.pptx`; for v1, export **one slide per PDF page**. Do not promise editable `.pptx` output.
- [ ] Explain Word's dynamic pagination and possible changes in fonts, pagination, tracked changes, comments or page layout between Word and LibreOffice.
- [ ] Document that conversions of password-protected or digitally signed documents may require separate handling and may invalidate signatures.
- [ ] Change the README's support table only when each implementation is tested and shipped.

### Phase 2 acceptance criteria

- `.docx` and `.pptx` on supported configured systems become PDF outputs with a blank after every rendered page/slide.
- No Office installation is needed on Linux when LibreOffice is installed; missing prerequisites produce helpful instructions.
- Source documents remain unchanged, and temporary converted PDFs are not left behind.

## Phase 3 — tests, quality and CI (P2)

- [ ] Add `pytest` tests for 1/2/N-page inputs, zero-page handling, mixed sizes, rotation, naming collisions, Unicode paths, spaces in paths and corrupted PDFs.
- [ ] Inspect generated PDFs programmatically (`pypdf`) to assert page count, parity, blank page contents and page geometry.
- [ ] Add integration tests for Office/LibreOffice conversion behind capability checks; skip gracefully when the converter isn't available.
- [ ] Add a Windows BAT smoke test and a Linux shell smoke test, where feasible.
- [ ] Add GitHub Actions running PDF-core tests on Windows and Ubuntu, across supported Python versions.
- [ ] Add formatting/linting (e.g. Ruff) and a simple, repeatable test command.
- [ ] Never commit actual banking/utility documents, personal information, or proprietary test PDFs. Generate synthetic fixtures.

## Phase 4 — README, image, release (P3)

- [ ] Keep the funny origin story, but add concise **What it does**, **Supported formats**, **Installation**, **Usage**, **Printing settings**, **Limitations**, and **Contributing** sections.
- [ ] Make the support matrix accurate: PDF = working; Word/PowerPoint = planned until implemented; Excel = out of scope.
- [ ] Add the lightweight SVG illustration at `assets/printer-meltdown.svg` and reference it near the top of `README.md` using `![Printer tantrum](assets/printer-meltdown.svg)`.
- [ ] Add examples for duplex + blank reverse printing. Warn that duplex orientation settings (long/short edge) depend on page layout.
- [ ] Explain that some drivers may suppress blank pages; test with two source pages before relying on it. A tiny optional mark/dot on even pages is a **future opt-in** workaround, not a default (banks may reject the mark).
- [ ] Clarify that blank-even PDFs can change pagination and invalidate digital signatures; use original files for official electronic submissions.
- [ ] Publish a small tagged release only after Windows and Linux PDF tests pass.

## Suggested structure (flexible)

```text
blank-evens/
├── README.md
├── TODO.md
├── LICENSE
├── pyproject.toml          # or requirements.txt
├── .gitignore
├── blank_evens.py          # backward-compatible entry point
├── blank_evens_in_pdf.bat  # keep existing drag-and-drop path working
├── blank_evens.sh
├── blank_evens/
│   ├── __init__.py
│   ├── cli.py
│   ├── pdf.py
│   └── converters.py
├── assets/
│   └── printer-meltdown.svg
└── tests/
    ├── test_pdf.py
    ├── test_cli.py
    └── test_converters.py
```

## Guidance for Codex

1. **Inspect the current repository before editing.** Preserve existing working PDF behavior and check the exact file names.
2. Implement phases **in order**. Do not combine all phases into one unreviewable commit.
3. Write tests for each phase, run them and report results. Prefer focused PRs/commits with descriptive messages.
4. For external converters, use optional adapters and informative missing-dependency failures; never make them mandatory for PDF-only usage.
5. Do not modify the source documents, delete existing output PDFs, or upload test documents to external services.
6. Do not automatically commit or push confidential source documents, PDFs or credentials.
7. Start with Phase 0 and Phase 1; propose the Phase 2 converter design before adding Office automation.

**Project motto:** *Making printers print properly by giving them twice as much nothing to print.*
