"""Ingestion: plain-text extraction from PDF/DOCX and JSON input listing.

This module knows nothing about TECH-6. It exists so the CLI's
``extract`` command and the batch pipeline share one extraction path
instead of each re-implementing pdfplumber/python-docx calls.

One deliberate limitation: ``scan_inputs`` records a per-file extraction
failure as an ``[error extracting text: ...]`` string in the result
mapping, for backwards compatibility. Callers that print extracted text
must treat such strings as errors (the CLI does); a future version
should return ``(results, errors)`` instead.
"""
from pathlib import Path
from typing import Dict, Union


def extract_text_from_pdf(path: Union[str, Path]) -> str:
    """Extract text from a PDF using pdfplumber.

    Raises RuntimeError if pdfplumber is not installed.
    """
    try:
        import pdfplumber
    except Exception as e:
        raise RuntimeError("pdfplumber is required for PDF extraction: pip install pdfplumber") from e

    text_parts = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_text_from_docx(path: Union[str, Path]) -> str:
    """Extract text from a .docx using python-docx, in document order.

    The old implementation appended *all* paragraphs first and *then*
    all table rows, so a CV whose employment table sits between two
    paragraphs came out scrambled. Iterating the document body keeps
    paragraphs and tables in the order a reader sees them.
    """
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    doc = Document(str(path))
    parts = []
    for child in doc.element.body.iterchildren():
        if child.tag.endswith("}p"):
            text = Paragraph(child, doc).text
            if text.strip():
                parts.append(text)
        elif child.tag.endswith("}tbl"):
            table = Table(child, doc)
            for row in table.rows:
                row_text = " | ".join(cell.text for cell in row.cells)
                if row_text.strip():
                    parts.append(row_text)
    return "\n".join(parts)


def scan_inputs(folder: Union[str, Path] = "inputs/resumes") -> Dict[str, str]:
    """Scan `folder` (defaults to `inputs/resumes`) and return a mapping of filename -> extracted text.

    Supported extensions: .pdf, .docx
    """
    folder = Path(folder)
    results: Dict[str, str] = {}

    if not folder.exists():
        return results

    for p in sorted(folder.iterdir()):
        if p.is_dir():
            continue
        suffix = p.suffix.lower()
        try:
            if suffix == ".pdf":
                results[p.name] = extract_text_from_pdf(p)
            elif suffix == ".docx":
                results[p.name] = extract_text_from_docx(p)
            else:
                # skip unknown file types
                continue
        except Exception as exc:
            results[p.name] = f"[error extracting text: {exc}]"

    return results


def list_json_inputs(folder: Union[str, Path] = "inputs/json") -> list[Path]:
    """List `.json` files directly under `folder`, sorted by name.

    Only the top level is scanned (no recursion): a batch run over a
    directory should not silently pick up nested exports. The
    ``inputs/json`` default is a legacy of the pre-package layout;
    callers in the package pass an explicit directory.
    """
    folder = Path(folder)
    if not folder.exists():
        return []
    return sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".json"], key=lambda p: p.name)


if __name__ == "__main__":
    import json

    extracted = scan_inputs()  # defaults to inputs/resumes
    for name, text in extracted.items():
        print(f"--- {name} ---")
        print(text[:1000])
        print()
    print(json.dumps({k: len(v) for k, v in extracted.items()}, indent=2))
