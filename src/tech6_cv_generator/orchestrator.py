"""Batch orchestration for TECH-6 CV generation.

The original project ran only from inside ``src/`` with relative
``inputs/`` / ``outputs/`` paths baked in. This version takes explicit
directories, returns a structured report instead of only printing, and
lets the caller decide whether a single bad file fails the whole run.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from .form_builder import FormBuilder
from .ingestor import list_json_inputs
from .schema_mappers import map_kosovo_to_tech6, map_to_canonical

logger = logging.getLogger(__name__)

PLACEHOLDER_NAME = "{Insert full name}"


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path.name}: expected a JSON object at the top level")
    return data


def map_schema_file(
    schema_path: Path, json_dir: Path, *, force: bool = False
) -> Path | None:
    """Map one schema file to TECH-6 JSON and write it into ``json_dir``.

    Returns the output path, or ``None`` when no mapping rule applies.
    An up-to-date mapped file is left untouched unless ``force`` is set.
    """
    data = _load_json(schema_path)
    # Only the Kosovo-style schema has a mapping rule; already-canonical
    # TECH-6 files and unknown shapes are left alone.
    has_kosovo_shape = "expert_profile" in data or any(
        isinstance(v, dict) and "personal_info" in v for v in data.values()
    )
    if not has_kosovo_shape:
        logger.info("No mapping rule for %s", schema_path.name)
        return None
    mapped = map_to_canonical(data)
    if not mapped.get("name"):
        mapped["name"] = PLACEHOLDER_NAME
    json_dir.mkdir(parents=True, exist_ok=True)
    out_file = json_dir / f"{schema_path.stem}_mapped.json"
    if out_file.exists() and not force:
        if out_file.stat().st_mtime >= schema_path.stat().st_mtime:
            logger.info("Skipping mapping for %s; mapped file up-to-date.", schema_path.name)
            return out_file
    out_file.write_text(json.dumps(mapped, indent=2), encoding="utf-8")
    logger.info("Mapped %s -> %s", schema_path.name, out_file.name)
    return out_file


def map_schemas(schema_dir: Path, json_dir: Path, *, force: bool = False) -> List[Path]:
    """Map every known schema file in ``schema_dir`` into ``json_dir``."""
    mapped: List[Path] = []
    if not schema_dir.exists():
        return mapped
    for schema_path in sorted(schema_dir.glob("*.json")):
        try:
            out = map_schema_file(schema_path, json_dir, force=force)
        except Exception as exc:  # keep one bad schema from killing the batch
            logger.warning("Error mapping %s: %s", schema_path, exc)
            continue
        if out is not None:
            mapped.append(out)
    return mapped


def generate_one(
    json_path: Path,
    output_dir: Path,
    *,
    write_mapped_copy: bool = False,
    mapped_dir: Path | None = None,
) -> Dict[str, Any]:
    """Generate one DOCX from ``json_path``. Returns a report entry.

    ``write_mapped_copy`` used to default to True and write a
    ``*_mapped.json`` file *next to the source input*. On the next run
    that copy was itself picked up as an input, generating a duplicate
    document for the same expert. Mapped copies are therefore off by
    default; when explicitly requested, they go to ``mapped_dir`` (or
    the output directory), never back into the input directory.
    """
    entry: Dict[str, Any] = {
        "input": json_path.name,
        "output": None,
        "status": "unknown",
        "report": None,
        "error": None,
    }
    try:
        data = _load_json(json_path)
        # A non-standard schema placed directly among the inputs (e.g. a
        # Kosovo-style file with an ``expert_profile`` key) is mapped
        # in-memory so FormBuilder can consume it.
        if "expert_profile" in data:
            mapped = map_kosovo_to_tech6(data)
            if not mapped.get("name"):
                mapped["name"] = PLACEHOLDER_NAME
            if write_mapped_copy:
                target_dir = mapped_dir if mapped_dir is not None else output_dir
                target_dir.mkdir(parents=True, exist_ok=True)
                mapped_path = target_dir / f"{json_path.stem}_mapped.json"
                mapped_path.write_text(json.dumps(mapped, indent=2), encoding="utf-8")
                logger.info("Mapped inline %s -> %s", json_path.name, mapped_path.name)
            data = mapped
        # Copy before annotating: _source_stem is a pipeline concern and
        # must not leak into the caller's dictionary.
        data = dict(data)
        data["_source_stem"] = json_path.stem
        builder = FormBuilder(data)
        out = builder.build(output_dir=str(output_dir))
        entry["output"] = out
        entry["status"] = "ok"
        entry["report"] = builder.report
    except Exception as exc:
        entry["status"] = "error"
        entry["error"] = str(exc)
        logger.error("Error generating from %s: %s", json_path, exc)
    return entry


def generate_report(
    json_dir: Path,
    output_dir: Path,
    *,
    schema_dir: Path | None = None,
    write_report: bool = True,
) -> List[Dict[str, Any]]:
    """Generate a DOCX for every JSON file in ``json_dir``.

    Optionally maps schemas from ``schema_dir`` first. Returns one report
    entry per input file. When ``write_report`` is set, the full report is
    also written to ``output_dir/generation_report.json``.
    """
    if schema_dir is not None:
        map_schemas(schema_dir, json_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report = [generate_one(p, output_dir) for p in list_json_inputs(json_dir)]
    if write_report:
        report_path = output_dir / "generation_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        logger.info("Wrote generation report: %s", report_path)
    return report


def generate_all_from_jsons(
    json_folder: str | Path = "inputs/json",
    output_dir: str | Path | None = None,
    *,
    schema_folder: str | Path | None = None,
    fail_on_error: bool = False,
) -> List[str]:
    """Generate DOCXs for every JSON file in ``json_folder``.

    Returns the list of output paths. With ``fail_on_error`` set, the first
    failing input raises a ``RuntimeError`` instead of being recorded in
    the report and skipped.
    """
    json_dir = Path(json_folder)
    out_dir = Path(output_dir) if output_dir else Path("outputs")
    report = generate_report(
        json_dir,
        out_dir,
        schema_dir=Path(schema_folder) if schema_folder else None,
    )
    failures = [e for e in report if e["status"] != "ok"]
    if fail_on_error and failures:
        first = failures[0]
        raise RuntimeError(f"{first['input']}: {first['error']}")
    return [str(e["output"]) for e in report if e["output"]]


def main() -> int:
    """Backwards-compatible entry point: generate from ``inputs/json``."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    outputs = generate_all_from_jsons()
    if outputs:
        print("Generated:")
        for out in outputs:
            print(f" - {out}")
        return 0
    print("No JSON files found in inputs/json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
