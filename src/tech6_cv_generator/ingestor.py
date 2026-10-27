"""Ingestor module

Provides functions to extract plain text from PDF and DOCX files and to scan
an inputs directory for supported files.
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
    """Extract text from a .docx using python-docx."""
    from docx import Document

    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text and p.text.strip()]

    # Try extracting table text as well
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text for cell in row.cells)
            paragraphs.append(row_text)

    return "\n".join(paragraphs)


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


def list_json_inputs(folder: Union[str, Path] = "inputs/json"):
    """List `.json` files under `folder` (default `inputs/json`) and return a list of Path objects sorted by name."""
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
