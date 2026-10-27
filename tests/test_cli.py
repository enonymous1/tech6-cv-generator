import json
from pathlib import Path

from tech6_cv_generator.cli import main


def test_cli_generate_and_map(tmp_path):
    root = Path(__file__).resolve().parents[1]
    sample = root / "examples" / "sample_data.json"
    out_dir = tmp_path / "outputs"
    assert main(["generate", str(sample), "--output-dir", str(out_dir)]) == 0
    generated = list(out_dir.glob("*.docx"))
    assert len(generated) == 1
    assert (out_dir / "generation_report.json").exists()

    kosovo = root / "examples" / "tech6_kosovo_schema.json"
    mapped_out = tmp_path / "kosovo_mapped.json"
    assert main(["map", str(kosovo), "--output", str(mapped_out)]) == 0
    mapped = json.loads(mapped_out.read_text(encoding="utf-8"))
    assert mapped["name"]  # placeholder name from the schema template


def test_cli_generate_missing_input_returns_error(tmp_path):
    assert main(["generate", str(tmp_path / "nope.json")]) == 2
