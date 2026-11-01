# Changelog

## 2.2.0 — 2026-11-01

Static demo site for GitHub Pages, plus a JSON authoring form.

### Added

- `site/` — landing page and a JSON authoring form (vanilla HTML/CSS/JS,
  no dependencies, no backend). The form covers the canonical TECH-6
  fields, flags the same gaps the builder would highlight (missing
  personal/contact fields, references without contact details), loads
  the fictional sample or a JSON file, previews the exact JSON that
  will be downloaded, and copies the CLI command to generate the DOCX.
  Nothing entered leaves the browser; the page states plainly that it
  does not generate the DOCX itself.
- `.github/workflows/pages.yml` — Pages deploy on push to `main`
  (plus manual dispatch): ruff + pytest first, then the sample DOCX
  is generated in CI from the fictional sample data and staged into
  the deploy artifact, so the downloadable sample always matches the
  current code. One-time setup after the first push: Settings →
  Pages → Source: GitHub Actions.
- `tests/test_site.py` — site file/reference checks, workflow
  staging checks, and (via Node when available) the form logic's
  sample round-trip.

### Notes

- `site/sample_data.json` is a copy of `examples/sample_data.json`
  for local previews; the Pages workflow overwrites it at build time
  with the canonical copy so it cannot drift (see `site/README.md`).
- `site/sample-output.docx` is deliberately not committed: it is
  generated in CI (see above). The README Deployment section now
  describes the demo deploy; the tool itself remains a local CLI.

## 2.1.0 — 2026-11-01

Staff review of v2.0.0 (full findings in `docs/REVIEW.md`) with the
fixes applied, not just reported. Generated document text and tables
are unchanged from v2.0.0 (verified by output parity); the one layout
change is cell padding that v2.0.0 intended but never applied.

### Fixed

- Builder reuse no longer duplicates every section: each `build()`
  starts from a fresh document and report.
- Path traversal via expert names: output filenames are sanitized,
  so a name containing `/` or `..` cannot write outside the output
  directory; the placeholder rule is now shared (`is_placeholder`).
- Silent exception swallowing around highlighting, borders, and
  report counts is gone: that XML work lives in the new
  `docx_helpers.py` module and fails loudly. This exposed that the
  personal-info cell padding had never been applied (wrong
  python-docx API, swallowed by `try/except: pass`); it is now
  applied as intended.
- Mapped copies are no longer written into the input directory (they
  used to be re-generated as duplicate CVs on the next run); they are
  off by default and go to the output directory when requested.
- Mapper bugs: the authorized representative no longer receives a
  signature *date* as its name; nested `expert_profile` documents
  map instead of returning empty; languages without a proficiency no
  longer render as `"English ()"`.
- CLI `extract` reports corrupt files with a clean error and exit
  code instead of a traceback; duplicate inputs are deduplicated;
  the orchestrator no longer mutates the caller's data dictionary.
- DOCX text extraction now follows document order (paragraphs and
  tables interleaved) instead of all paragraphs then all tables.

### Added

- `docs/REVIEW.md` (staff review), rewritten README with
  Description / Prerequisites / Installation / Local Development /
  Deployment sections, and a real pipeline diagram in
  `docs/assets/pipeline.svg` (screenshots and demo GIF remain
  commented placeholders until captured from real runs — see
  `docs/assets/README.md`).
- 10 new tests pinning the fixed behaviours (21 total).
- `py.typed` marker; CI matrix now covers Python 3.10–3.13,
  matching `requires-python`.

## 2.0.0 — 2026-10-26

Public export and modernization of the original `ss-docTemplater` project,
published under the name `tech6-cv-generator`.
This is a squashed, single-commit export: the original private history is
not included, and no real person's CV data is in this repository.

### Changed

- Installable package (`tech6_cv_generator`) with a `tech6-cv-generator` CLI:
  `generate`, `map`, and `extract` replace the old `cd src && python -m
  orchestrator` workflow and the duplicate shell scripts.
- Explicit input/output directories everywhere. The builder no longer
  defaults to a folder next to the package source, and an existing output
  file is never overwritten.
- Batch runs return a structured report and exit non-zero when any input
  fails, instead of printing errors and continuing as if all was well.
- Tests run only on fictional data in temporary directories; the old test
  that regenerated documents from the real input folder is gone.
- Line endings normalized to LF; `.gitignore` now actually ignores
  `outputs/` and generated `.docx` files (the original claimed this but
  had those lines commented out).

### Removed

- All real CV inputs, generated DOCXs, and the source resume PDF from the
  original project. `examples/` keeps only fictional sample data, the
  TECH-6 schema, and a placeholder Kosovo-style schema template. The
  Kosovo template's RFP reference was generalized to a placeholder so no
  trace of a real assignment remains.
- Unused dependencies (`openai`, `pypdf`; only `pdfplumber` was used for
  PDF extraction) and the stale entry points that pointed at paths that
  no longer existed.

### Added

- `pyproject.toml`, MIT LICENSE, GitHub Actions CI (ruff + pytest on
  Python 3.11/3.12), and a landing-page README.
