# Visual assets

This folder holds the repository's visual assets. One is real; the
rest are intentionally not here yet, because a screenshot or GIF for a
public repository must come from a real run, never a mockup.

## Included

- `pipeline.svg` — hand-drawn pipeline diagram, embedded in the README
  after the Description. It contains no data, so it needs no capture.

## To capture (from real runs, fictional sample data only)

Never use a real person's CV for any of these. All captures use
`examples/sample_data.json` (Jane Q. Expert, fictional) or a record
with deliberately blank fields for the highlighting shot.

### `sample-output.png` — first page of a generated CV

```bash
tech6-cv-generator generate examples/sample_data.json --output-dir /tmp/tech6-shot
libreoffice --headless --convert-to pdf --outdir /tmp/tech6-shot /tmp/tech6-shot/*.docx
pdftoppm -png -f 1 -l 1 -r 150 /tmp/tech6-shot/*.pdf /tmp/tech6-shot/page
# -> /tmp/tech6-shot/page-1.png, copy to docs/assets/sample-output.png
```

### `highlighted-fields.png` — yellow highlighting close-up

Generate from a record with blank name/position fields (so the
personal-info table highlights), render as above, and crop to the
personal-info table. The shot must show the yellow fill and the
corresponding report entry concept, not a recoloured mockup.

### `demo.gif` — terminal run

Record a terminal session running:

```bash
tech6-cv-generator generate examples/sample_data.json
ls outputs/
```

Use a terminal recorder (for example `asciinema` + `agg`, or your
terminal's screen recorder) and export as GIF. Keep it under ~15
seconds and at a readable font size; the generated filename and the
"Wrote generation report" line should be legible.

## Enabling a captured asset

Each asset has a commented placeholder in `README.md` at the exact
spot it belongs. When the file exists, remove the surrounding HTML
comment markers for that image only, and check the rendered README
before committing — a referenced-but-missing image must never ship.
