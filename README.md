# tech6-cv-generator

Turn structured JSON into a filled-in TECH-6 CV document — without retyping the same form by hand for every expert.

Give it a JSON file describing an expert (name, education, employment, languages, and so on) and it produces a formatted `.docx` in the TECH-6 layout. Missing fields are highlighted in yellow so gaps are visible at a glance instead of slipping through, and every batch run ends with a `generation_report.json` saying what succeeded, what failed, and what was highlighted.

It can also map a differently-shaped schema into TECH-6 first — the included example is a Kosovo-style schema with an `expert_profile` block — and extract plain text from PDF or DOCX resumes to help populate the data.

TECH-6 is the curriculum vitae form used in technical proposals for consulting assignments procured by multilateral development banks, including the World Bank and the Asian Development Bank. This tool is not affiliated with or endorsed by any of them; it just produces documents in that shared form's layout.

## Quick start

```bash
pip install -e .
tech6-cv-generator generate examples/sample_data.json
# -> outputs/Form_TECH-6_CV_Jane_Q._Expert.docx
```

Generate a whole folder at once:

```bash
tech6-cv-generator generate my-experts/ --output-dir outputs/
```

Map a schema file to TECH-6 JSON before generating:

```bash
tech6-cv-generator map examples/tech6_kosovo_schema.json --output mapped.json
tech6-cv-generator generate mapped.json
```

Extract text from a resume:

```bash
tech6-cv-generator extract examples/sample_resume.docx
```

An existing output file is never overwritten: a numeric suffix is appended instead (`..._2.docx`, `..._3.docx`). If any input fails, the run still finishes the rest, reports the error, and exits non-zero.

## Library use

```python
import json
from tech6_cv_generator import FormBuilder, map_to_canonical

data = json.load(open("examples/sample_data.json"))
out = FormBuilder(data).build(output_dir="outputs")
print(out)

mapped = map_to_canonical(json.load(open("examples/tech6_kosovo_schema.json")))
```

## What is in here

- `src/tech6_cv_generator/form_builder.py` — builds the TECH-6 document: personal info, education, employment records, memberships and languages, adequacy table, contact and certification, signatures. Missing personal/contact fields get yellow highlighting and are recorded in the builder's report.
- `src/tech6_cv_generator/schema_mappers.py` — normalizes dates, contacts, and languages, and maps Kosovo-style and flat schemas into the canonical TECH-6 shape.
- `src/tech6_cv_generator/orchestrator.py` — batch generation with a structured report; one bad file no longer kills the whole run silently.
- `src/tech6_cv_generator/ingestor.py` — PDF (pdfplumber) and DOCX text extraction, and JSON input listing.
- `src/tech6_cv_generator/cli.py` — the `tech6-cv-generator` command: `generate`, `map`, `extract`.
- `examples/` — fictional sample data only (Jane Q. Expert, example.com addresses), the TECH-6 schema and its documentation, and a Kosovo-style schema template with placeholder names.

## Development

```bash
pip install -e ".[dev]"
pytest -q
ruff check src tests
make generate-sample
```

## A note on the data in this repo

This is a cleaned public export. The original project contained real experts' CV data and generated documents; none of that is in this repository. Every example here is fictional, generated outputs are git-ignored, and the original private history is not included — see `CHANGELOG.md`.

## License

MIT — see `LICENSE`.
