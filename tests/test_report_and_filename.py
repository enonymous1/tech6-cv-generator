import json
from pathlib import Path

from tech6_cv_generator import FormBuilder
from tech6_cv_generator.orchestrator import generate_report


def test_filename_fallback_uses_source_stem(tmp_path):
    builder = FormBuilder({"name": "", "_source_stem": "Test_Stem"})
    out_path = builder.build(output_dir=str(tmp_path))
    assert "Test_Stem" in Path(out_path).name


def test_generate_writes_report(tmp_path):
    json_dir = tmp_path / "inputs"
    json_dir.mkdir()
    (json_dir / "jane.json").write_text(
        json.dumps({"name": "Jane Q. Expert", "contact": "jane@example.com"}),
        encoding="utf-8",
    )
    (json_dir / "broken.json").write_text("{not json", encoding="utf-8")
    output_dir = tmp_path / "outputs"

    report = generate_report(json_dir, output_dir)

    assert (output_dir / "generation_report.json").exists()
    by_input = {entry["input"]: entry for entry in report}
    assert by_input["jane.json"]["status"] == "ok"
    assert by_input["broken.json"]["status"] == "error"
    assert by_input["broken.json"]["error"]
