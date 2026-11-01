# Demo site

Static site deployed to GitHub Pages by `.github/workflows/pages.yml`.
There is no backend: the JSON authoring form runs entirely in the
visitor's browser (`app.js`), and DOCX generation still happens with
the Python CLI.

## Files

- `index.html` — landing page plus the authoring form. The pipeline
  diagram is inlined (not a separate file) so the page is
  self-contained; the canonical diagram also lives at
  `docs/assets/pipeline.svg`.
- `styles.css`, `app.js` — styling and form logic, no dependencies.
- `sample_data.json` — a copy of `examples/sample_data.json` so the
  "Load fictional sample" button works when previewing this folder
  on its own. **The Pages workflow overwrites it at build time with
  the canonical copy from `examples/`**, so the deployed sample can
  never drift from the repository sample. If you change the sample,
  do not edit this copy by hand — the next deploy replaces it.
- `sample-output.docx` is **not** checked in: the Pages workflow
  generates it in CI from the sample data and stages it into the
  deploy artifact, so the downloadable sample always matches the
  current code. Locally, generate it yourself into this folder if
  you want the download link to work in a preview (it is git-ignored
  via `*.docx`).

## Local preview

```bash
python3 -m http.server -d site 8000
# open http://127.0.0.1:8000/
```

Serve over HTTP, not `file://`: the sample load uses `fetch`, which
browsers block from local files.
