# Changelog

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
