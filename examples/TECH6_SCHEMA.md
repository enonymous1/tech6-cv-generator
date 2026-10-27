# TECH-6 Schema & Expected Fields

This file documents the expected keys and value types that the Analyzer should produce when converting raw resume text into the structured data consumed by `FormBuilder`.

- `position_title` (string): e.g. "K-1, TEAM LEADER".
- `name` (string): Full expert name, e.g. "Jane Q. Expert".
- `dob` (string, ISO or human-readable): e.g. "1980-05-17" or "17 May 1980".
- `citizenship` (string): Country of citizenship or residence.

- `education` (array of objects or string): Preferably an array of objects with fields:
  - `institution` (string)
  - `degree` (string)
  - `start_year` / `end_year` (string or int, optional)
  - `notes` (string, optional)
  Alternatively the extractor may supply a single formatted string.

- `employment` (array of objects) — each job record should include:
  - `period` (string): e.g. "Jan 2020 - Present"
  - `title` (string)
  - `organization` (string)
  - `contact` (string): phone or email references, e.g. "Tel: +1-555-0100 / ref@example.com"
  - `country` (string)
  - `summary` (string): short description of activities relevant to the assignment

- `memberships` (string): professional associations and publications.
- `languages` (array of strings or string): e.g. `["English (fluent)", "French (working)"]`.
- `adequacy_for_assignment` (array of objects): Each entry corresponds to a row in the Adequacy table and should include:
  - `task` (string): Detailed task assigned on the Consultant's Team of Experts.
  - `reference` (string): Reference to prior work/assignments that best illustrates capability to handle the task.

  Example:
  ```json
  "adequacy_for_assignment": [
    { "task": "Technical oversight", "reference": "Examples of prior technical oversight on XYZ projects" }
  ]
  ```

  **Backward compatibility:** If the analyzer produces the older `tasks` string field, `FormBuilder` will accept it and render it as a single row in the table.

- `contact` (object):
  - `email` (string)
  - `phone` (string)

- `certification_text` (string): full certification paragraph for the CV (the default will be used if missing or too short).
- `authorized_representative` (string): name of the signatory representing the consultant.

Notes & guidance
- Optional fields are allowed; `FormBuilder` supplies reasonable defaults for missing fields.
- `employment` should be in reverse chronological order when possible.
- Dates and phone numbers do not need to be normalized by the analyzer but normalization is helpful.
- If an LLM is used, instruct it to return values in this schema exactly (JSON). Provide a fallback and validation step to catch missing or malformed fields.

Example: `inputs/schema/tech6_schema_example.json` contains a working example you can use to test `FormBuilder` directly.

---

## Machine-readable JSON Schema ✅
We also maintain a machine-readable JSON Schema at `inputs/schema/tech6_schema.json` that formalizes the expected fields, types, and basic formats (dates, contact structure). Use it for automated validation and as the canonical source of truth for mappings.

## Field aliases & mapping guidance 🔁
The analyzer may produce variants of the same data; `FormBuilder` and `schema_mappers.py` accept common aliases. Key aliases to be aware of:

- `full_name` -> `name`
- `date_of_birth` -> `dob`
- `employment_record` -> `employment`
- `personal_info.contact_details` -> `contact` (object with `email` and `phone`)
- `professional_associations` + `publications` -> `memberships` (string) and `publications` retained as list when available
- `language_skills` -> `languages` (normalized to array of strings)
- `adequacy_for_assignment` <-> `tasks`

Add other aliases to this section as you encounter them and include mapping tests to prevent regressions.
