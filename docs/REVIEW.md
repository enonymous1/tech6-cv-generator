# Staff review — tech6-cv-generator v2.0.0 → v2.1.0

Reviewer role: staff-level software engineer and open-source maintainer.
Scope: the whole repository as of v2.0.0 (single squashed export commit
`ab05791`): `src/tech6_cv_generator/` (form builder, schema mappers,
orchestrator, ingestor, CLI), `tests/`, `pyproject.toml`, CI, README,
and `examples/`. This review was conducted against the actual code, not
the README's description of it — several findings below are places
where the two disagreed.

## Verdict

**Solid for a small CLI, with three genuine bugs and one security
issue, all fixed in v2.1.0.** There are no secrets, no network access,
and no real-person data in the repository (the 2.0.0 export scrubbed
those). The architecture is honest for the problem size — a batch
document generator does not need a framework — but the builder was a
god class that swallowed its own errors, and the mapper had
data-corrupting edge cases. None of the fixes change the generated
document's text or tables (verified by output parity, below); one fix
does change layout in the way the code always intended (see H3).

The largest remaining risk is not a bug but a design debt: the
"canonical" TECH-6 shape is an untyped dictionary whose fields change
type depending on which mapper produced them. That is the next refactor
(see M1), and it is deliberately *not* done here, because it touches
every section of the builder and would have broken output parity in
this pass.

## Severity summary

| # | Finding | Severity | Status in v2.1.0 |
|---|---------|----------|------------------|
| H1 | Builder reuse duplicates every section | High | Fixed |
| H2 | Expert name used as a filename: path traversal | High | Fixed |
| H3 | Silent `try/except: pass` hid dead styling code (cell margins never applied) | High | Fixed (data path); layout guards remain, see below |
| H4 | Mapped copies written into the input directory, then re-generated as duplicates | High | Fixed |
| M1 | Untyped, shape-shifting canonical dict | Medium | Deferred, with plan |
| M2 | Mapper data bugs: authorized rep = a date; nested `expert_profile` mapped to empty; `"English ()"` | Medium | Fixed |
| M3 | CLI `extract` raised raw tracebacks on corrupt files | Medium | Fixed |
| M4 | Duplicate inputs generated twice; orchestrator mutated the caller's dict | Medium | Fixed |
| M5 | DOCX extraction scrambled paragraph/table order | Medium | Fixed |
| M6 | CLI and orchestrator each implement report writing | Medium | Deferred, with plan |
| L1 | CI matrix did not cover `requires-python` floor (3.10); dependencies unpinned | Low | Matrix fixed; pinning deferred |
| L2 | `scan_inputs` returns error strings as if they were extracted text | Low | Documented; CLI now reports them; API change deferred |
| L3 | No type checking, no formatting gate; `py.typed` absent | Low | `py.typed` added; gates deferred |

## Pillar 1 — Best practices and code quality

### H1 (fixed): `FormBuilder.build()` was not idempotent

`__init__` created the `Document` once, and `build()` appended every
section to it. Calling `build()` twice on one builder — a perfectly
reasonable thing for a library consumer to do — produced a document
with every section twice, and the report kept accumulating counts.
`build()` now creates a fresh `Document` and a fresh report on every
call (`_fresh_report()`), and the module docstring states this
contract. Test: `test_build_twice_produces_identical_documents`.

### H2 (fixed): filename derived from untrusted input — path traversal

`build()` built the output filename from `data["name"]` with only
spaces replaced. A name of `../../secret` or `a/b` wrote outside the
output directory. This is the one security finding: the tool processes
JSON it did not author (CVs from third parties), so the name is
untrusted input. `safe_filename_stem()` (in `form_builder.py`) keeps
alphanumerics, `_`, `-`, and `.`, collapses everything else to
underscores, and strips leading dots; the placeholder rule is shared
via `is_placeholder()` so "missing" means the same thing in the
personal-info table and in filename selection (previously the two
checks disagreed: one looked for `insert` anywhere, the other only at
the start). Tests: `test_safe_filename_stem_blocks_path_traversal`,
`test_build_with_traversal_name_stays_inside_output_dir`.

### H3 (fixed, in part): 41 silent exception sites hid a dead feature

`grep "except Exception"` found 41 sites in v2.0.0, most of them
`try: ... except Exception: pass` around styling and report updates.
The worst case was the personal-info cell margins: the code called
`table._tbl.get_or_add_tblPr()`, which does not exist on python-docx's
`CT_Tbl` — so the padding code raised on *every* build and was
silently discarded. The padding was documented in a comment, intended
by the author, and never applied.

The fix extracts the repeated XML work into `docx_helpers.py`
(`highlight_run`, `shade_cell`, `set_cell_borders`,
`set_table_cell_margins`, `add_paragraph_border`) with the correct
`CT_Tbl.tblPr` accessor, and the builder now calls them unguarded: a
styling failure fails the build and is recorded by the orchestrator's
per-file error handling, instead of producing a subtly wrong document.
The previously dead padding is now live — that is the *only* layout
change in v2.1.0, and it is the layout the code always described.

What remains: 29 `except Exception` sites, verified to be layout-only
(column widths, spacing, alignment, font sizes) plus legitimate
per-file batch guards in the orchestrator/CLI and date-parse fallbacks
in the mappers. They are acceptable for one release but should be
deleted in a follow-up — on a fresh default `Document` these
operations do not fail, and the guards only exist to hide that fact.
Do not reintroduce `try/except: pass` around report updates or
highlighting; those are data, not decoration.

### H4 (fixed): mapped copies polluted the input directory

`generate_one(..., write_mapped_copy=True)` — the default — wrote a
`*_mapped.json` next to the *source* input whenever an input was a
Kosovo-style schema. The next batch run picked that copy up as a new
input and generated a duplicate document for the same expert (with a
`_2` suffix, so it looked like a real second CV). The default is now
`False`; when a mapped copy is explicitly requested it goes to
`mapped_dir` (or the output directory), never back into the inputs.
The `--schema-dir` pipeline is unchanged and intentional: mapping a
schema *directory* into the input directory is its documented job, and
it is the caller's explicit choice. Test:
`test_generate_one_does_not_pollute_input_dir`.

### M1 (deferred): the canonical shape is an untyped, shape-shifting dict

`education` may be a list of dicts, a list of strings, a dict, or a
long placeholder string; `contact` may be a string, dict, or list;
`languages` may be a string or a list; `employment[].contact` may be
a string, dict, or list. The builder defends against all of them with
`isinstance` ladders, and the mappers do not guarantee which shape
they emit. This is the root cause of most of the builder's complexity
and of M2's bugs.

Deferred plan, in order: (1) define the canonical shape once, as
`TypedDict`s (or a frozen dataclass with `asdict()` at the boundary),
with `name: str`, `contact: Contact`, `education: list[Education]`,
and so on; (2) make `map_to_canonical` the *only* producer of that
shape and validate at its exit (missing keys become `""`, wrong types
raise `ValueError` with the field name); (3) delete the builder's
`isinstance` ladders one section at a time, with the output-parity
check below run after each. Do not start this without first adding a
golden-output test (generate the sample DOCX, assert paragraph and
table text) — it is the only thing that makes the refactor safe.

### M2 (fixed): three mapper data bugs

* **Authorized representative was a date.** `map_kosovo_to_tech6` read
  `certification_statement.representative_signature_date` into the
  `authorized_representative` *name* field, so generated CVs showed a
  date where the signatory's name belongs. It now reads
  `representative_name` / `authorized_representative` /
  `representative`, falling back to the placeholder.
* **Nested `expert_profile` mapped to empty.** `map_to_canonical`'s
  fallback passed a bare inner dict to `map_kosovo_to_tech6`, which
  expects the `{"expert_profile": ...}` wrapper and therefore returned
  an empty mapping. The inner dict is now re-wrapped.
* **Language without proficiency rendered as `"English ()"`.**
  `_normalize_languages` appended the parenthetical unconditionally;
  it is now added only when a proficiency exists.
* Also fixed: a dead duplicate lookup (`proposed_position_title or
  proposed_position_title`).

### M3 (fixed): CLI `extract` raised raw tracebacks

A corrupt PDF (or any extraction failure) escaped as an unhandled
exception with a traceback. `_cmd_extract` now catches per-file
errors, reports them on stderr, continues with the remaining files,
and exits non-zero. Test: `test_cli_extract_corrupt_pdf_reports_error_not_traceback`.

### M4 (fixed): duplicate inputs, and a mutated caller dictionary

* Passing both a file and its directory (or the same file twice) to
  `generate` generated the same CV twice. Inputs are now deduplicated
  preserving order.
* `generate_one` added `_source_stem` to the caller's dictionary
  in place. It now copies first. (`_source_stem` itself is a smell —
  pipeline metadata smuggled through the data dict — but removing it
  requires the M1 model; the copy at least stops the leak.)

### M5 (fixed): DOCX extraction order

`extract_text_from_docx` appended all paragraphs, then all table
rows, scrambling any document whose tables sit between paragraphs.
It now iterates `doc.element.body` children in document order.
Test: `test_docx_extraction_keeps_document_order`.

### M6 (deferred): report writing is implemented twice

`cli._cmd_generate` builds its own report list and writes
`generation_report.json`, duplicating `orchestrator.generate_report`
(which does the same for a directory). They can already drift: the
CLI version groups by parent directory and supports `--schema-dir`,
the library version does not support mixed file lists. The fix is a
`generate_files(paths, output_dir, ...)` in the orchestrator that
both use. Deferred because the CLI's grouping behaviour needs a
decision first (it exists to keep mapped copies next to sources —
see H4).

### L1: CI and dependency hygiene

CI tested Python 3.11/3.12 while `requires-python` allowed 3.10; the
matrix now covers 3.10–3.13, matching the declared floor and the
current release. Dependencies are still lower-bounded only
(`python-docx>=0.8.11`, `pdfplumber>=0.7.5`). For a CLI this is
acceptable, but a lock file (`pip-tools` or `uv lock`) would make
"works on my machine" reproducible for contributors; add it when the
first dependency-related CI failure appears, not before.

### L2: `scan_inputs` error strings

`scan_inputs` returns `"[error extracting text: ...]"` as the
"value" for a failed file. That is an error masquerading as data, and
any consumer that prints the mapping prints the error as content.
The CLI now detects and reports those strings instead of printing
them. The proper fix — return `(results, errors)` — is a breaking API
change and is deferred to the next major version; it is documented in
`ingestor.py`'s module docstring so the next maintainer finds it.

### Performance

There is no performance problem to fix, and none was invented. The
workloads are tiny (one DOCX per expert, one PDF page at a time). The
only superlinear-looking code is the non-overwrite loop
(`while candidate.exists()`), which is linear in the number of
same-named outputs and irrelevant at this scale. Do not add caching,
parallelism, or streaming here; the next bottleneck, if any, will be
pdfplumber on very large resumes, and that is a one-line
`--max-pages` conversation, not an architecture.

## Pillar 2 — Commenting and in-code documentation

What was missing and is now added:

* `schema_mappers.py` had **no module docstring at all**. It now
  explains the module's contract (builder renders one canonical
  shape; dialects are translated here), and documents the day-first
  `DD/MM/YYYY` assumption explicitly — the old code silently assumed
  it, and a `MM/DD/YYYY` source would have been misread without any
  warning.
* `form_builder.py`'s module docstring now states the two conventions
  the rest of the codebase depends on: yellow highlighting as a
  "not submittable yet" signal counted in the report, and per-build
  fresh documents.
* `docx_helpers.py` is written as explanation-first documentation:
  each helper says *why* it exists (single place for the XML, fail
  loudly) and the `tblPr` helper carries the cautionary tale of the
  dead code it replaced.
* Inline "why" comments were added at every fixed bug (traversal,
  mapped copies, representative date, document order, deduplication)
  so the next reader knows what regression the code is guarding
  against, not just what it does.

What remains thin: the individual `_add_*` section methods in the
builder describe the TECH-6 layout only by their code. A short
comment per section naming the corresponding TECH-6 field (e.g.
"Section 6 of the form: adequacy for the assignment") would help a
contributor who does not have the form in front of them. Low priority;
the README's layout section now covers this at a higher level.

## Pillar 3 — Future-proofing and architecture

Current shape, honestly: a four-module pipeline with a clear data
flow — `ingestor` (bytes → text) → `schema_mappers` (dialect →
canonical dict) → `form_builder` (dict → DOCX + report) →
`orchestrator` (files → batch report), with `cli` as a thin shell.
That layering is good and should be preserved. The problems are inside
the layers, not between them:

* **Tight coupling:** `FormBuilder` does data interpretation,
  layout, file naming, file writing, and reporting. Splitting it is
  the M1 plan's second half: a `DocumentRenderer` that takes a
  validated model and a `Report` object, with filename policy moved
  to the orchestrator (which already owns output directories).
* **Hardcoded configuration:** highlight/header fills, the
  `"Table Grid"` style, placeholder strings, and the TECH-6
  certification text are scattered across the builder and mappers.
  The fills are now constants in `docx_helpers.py` and the placeholder
  name in `orchestrator.py`; the next step is a single `constants.py`
  (or a small TOML template file) for all of them, so a rebrand or a
  form revision touches one file.
* **Scaling:** if the project grows form variants (TECH-5, TECH-7),
  the code-built layout will not scale — each variant would duplicate
  the builder. The correct abstraction then is a DOCX *template* file
  plus a field-binding layer, not more builder code. Do not build that
  now: there is one form, and a template engine would be the largest
  unforced change available.
* **Testing seam:** the builder is now testable in isolation
  (fresh document per build, no global state), and the new tests use
  that seam. The missing seam is a golden-output test (see M1) and
  a test for the `--schema-dir` pipeline end to end; both are listed
  as next tests, not done here.

## Pillar 4 — README modernization

The README was rewritten in v2.1.0 (see `README.md`) against the
actual code, not the 2.0.0 text. What changed:

* Required sections added: **Description**, **Prerequisites**,
  **Installation**, **Local Development**, **Deployment**.
* The old README claimed `pip install -e .` as if the package were
  on PyPI; it is not. Installation now says so plainly (install from
  a clone) and the Deployment section describes the real release
  process (tag → GitHub release → CI) instead of inventing a hosting
  story for a CLI that has none.
* The old "Development" section was three commands. Local Development
  now covers environment setup, the test/lint/sample commands, the
  project layout, and how to verify a change without breaking
  generated output.
* The old README did not mention exit codes, the non-overwrite rule's
  suffix behaviour, or the `--schema-dir` pipeline; all three are now
  documented because they are behaviour a user will hit.
* The not-affiliated note for the World Bank / Asian Development Bank
  is kept verbatim in spirit: topics and tags are discoverability,
  not endorsement.

## Pillar 5 — Visual asset strategy

No screenshots or GIFs in this repository are real yet, and none
were faked for this review. The strategy, with exact placements in
the rewritten README, is:

| Asset | Depicts | README placement | Status |
|-------|---------|------------------|--------|
| `docs/assets/pipeline.svg` | The pipeline: JSON inputs + Kosovo schema → `map_to_canonical` → `FormBuilder` → DOCX + `generation_report.json`; PDF/DOCX resumes → `extract` → text. Hand-drawn, no data. | Embedded immediately after Description, before Prerequisites (the hero visual) | **Real, included** |
| `docs/assets/sample-output.png` | First page of the generated Jane Q. Expert DOCX, rendered from a real run | Commented placeholder after the first Quick-start example | Placeholder — see capture instructions |
| `docs/assets/highlighted-fields.png` | Close-up of a personal-info table with yellow-highlighted missing fields, from a real run on an incomplete record | Commented placeholder in "How missing fields are flagged" | Placeholder |
| `docs/assets/demo.gif` | A terminal recording of `tech6-cv-generator generate examples/sample_data.json` and the resulting `outputs/` listing | Commented placeholder in Local Development | Placeholder |

Placeholders are HTML comments in the README, not broken image
links, so the README renders cleanly until the assets exist.
`docs/assets/README.md` gives exact capture commands (LibreOffice
headless render → `pdftoppm` for the PNGs; a terminal recorder for
the GIF) and the rule that matters: capture from a real run on the
fictional sample data, never a mockup, and never a real person's CV.

## Verification

* `ruff check src tests`: clean.
* `pytest -q`: **21 passed** (11 pre-existing + 10 new tests in
  `tests/test_staff_review_fixes.py`).
* Output parity: the sample DOCX generated by v2.1.0 was compared
  against v2.0.0's from a fresh worktree of `ab05791`. Paragraph
  text, table count (6), and table cell text (34 cells) are
  identical; the only `document.xml` difference is the
  `tblCellMar` padding that v2.0.0 intended but never applied (H3).
  The sample DOCX contains no highlights because the sample data is
  complete — highlighting is covered by the pre-existing tests.
* Fresh-extraction check and the new commit hash are recorded in
  the delivery message; the zip in the delivery supersedes the
  v2.0.0 zip. The pre-review caveats still stand: CI has not run on
  GitHub yet (first push), and the destination-repo checks for
  `enonymous1/tech6-cv-generator` and `enonymous1/ss-docTemplater`
  are still the user's to do before pushing.
* Privacy re-check after the changes: no new data was introduced;
  examples remain fictional (Jane Q. Expert, example.com); the
  scrubbed RFP reference remains a placeholder; no secrets, network
  calls, or telemetry were added.
