"""Command-line interface for tech6-cv-generator.

Usage:
    tech6-cv-generator generate INPUT... [--output-dir DIR] [--schema-dir DIR]
    tech6-cv-generator map SCHEMA.json [--output OUT.json]
    tech6-cv-generator extract FILE...
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import __version__
from .ingestor import extract_text_from_docx, extract_text_from_pdf, scan_inputs
from .orchestrator import map_schema_file


def _add_output_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory for generated DOCX files (default: ./outputs)",
    )


def _cmd_generate(args: argparse.Namespace) -> int:
    inputs: list[Path] = []
    for raw in args.inputs:
        path = Path(raw)
        if path.is_dir():
            inputs.extend(sorted(p for p in path.glob("*.json")))
        elif path.is_file():
            inputs.append(path)
        else:
            print(f"tech6-cv-generator: no such file or directory: {raw}", file=sys.stderr)
            return 2
    if not inputs:
        print("tech6-cv-generator: no JSON inputs found", file=sys.stderr)
        return 2
    # Deduplicate preserving order: passing both a file and its directory
    # (or the same file twice) used to generate the same CV twice.
    inputs = list(dict.fromkeys(inputs))

    # Group by parent directory so mapped copies land next to their source.
    from .orchestrator import generate_one, map_schemas

    report = []
    for parent in sorted({p.parent for p in inputs}):
        siblings = [p for p in inputs if p.parent == parent]
        if args.schema_dir is not None:
            # Mapped copies are written next to the inputs, as before.
            map_schemas(args.schema_dir, parent)
        for json_path in siblings:
            report.append(generate_one(json_path, args.output_dir))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.output_dir / "generation_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    failed = [e for e in report if e["status"] != "ok"]
    for entry in report:
        status = "ok" if entry["status"] == "ok" else f"ERROR: {entry['error']}"
        print(f"{entry['input']} -> {entry['output'] or status}")
    print(f"Wrote generation report: {report_path}")
    return 1 if failed else 0


def _cmd_map(args: argparse.Namespace) -> int:
    schema_path = Path(args.schema)
    out_path = Path(args.output) if args.output else Path(f"{schema_path.stem}_mapped.json")
    result = map_schema_file(schema_path, out_path.parent, force=True)
    if result is None:
        print(f"tech6-cv-generator: no mapping rule for {schema_path.name}", file=sys.stderr)
        return 2
    # map_schema_file names the output after the schema stem; honour an
    # explicit --output name by renaming when it differs.
    if result != out_path:
        result.rename(out_path)
    print(f"Mapped {schema_path.name} -> {out_path}")
    return 0


def _cmd_extract(args: argparse.Namespace) -> int:
    """Extract text, one file at a time, with a clean exit code.

    A corrupt PDF previously raised a raw traceback; now it is reported
    like any other failure and the run continues with the next file,
    exiting non-zero at the end. The same applies to scan_inputs'
    ``[error extracting text: ...]`` strings: those are errors, not
    extracted text, so they are reported instead of printed as content.
    """
    failed = False
    for raw in args.files:
        path = Path(raw)
        try:
            if path.is_dir():
                for name, text in scan_inputs(path).items():
                    if text.startswith("[error extracting text:"):
                        print(f"tech6-cv-generator: {name}: {text}", file=sys.stderr)
                        failed = True
                        continue
                    print(f"--- {name} ---")
                    print(text)
                continue
            suffix = path.suffix.lower()
            if suffix == ".pdf":
                text = extract_text_from_pdf(path)
            elif suffix == ".docx":
                text = extract_text_from_docx(path)
            else:
                print(f"tech6-cv-generator: unsupported file type: {path}", file=sys.stderr)
                return 2
        except Exception as exc:
            print(f"tech6-cv-generator: {path}: {exc}", file=sys.stderr)
            failed = True
            continue
        print(text)
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tech6-cv-generator",
        description="Generate TECH-6 CV documents (DOCX) from structured JSON.",
    )
    parser.add_argument("--version", action="version", version=f"tech6-cv-generator {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate DOCX files from JSON inputs.")
    gen.add_argument("inputs", nargs="+", help="JSON file(s) or directory/ies of JSON files.")
    gen.add_argument(
        "--schema-dir",
        type=Path,
        default=None,
        help="Directory of schema JSON files to map into the input directory first.",
    )
    _add_output_args(gen)
    gen.set_defaults(func=_cmd_generate)

    mapping = sub.add_parser("map", help="Map one schema JSON file to TECH-6 JSON.")
    mapping.add_argument("schema", help="Schema JSON file (e.g. a Kosovo-style schema).")
    mapping.add_argument("--output", help="Output JSON path (default: <stem>_mapped.json).")
    mapping.set_defaults(func=_cmd_map)

    extract = sub.add_parser("extract", help="Extract text from PDF/DOCX files or a directory.")
    extract.add_argument("files", nargs="+", help="File(s) or directory to extract text from.")
    extract.set_defaults(func=_cmd_extract)
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
