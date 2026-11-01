"""Tests for the static demo site and its Pages workflow.

The site is static HTML/CSS/JS with no build step, so these tests
check the properties that actually break a deploy: every referenced
file exists, the workflow stages what the page links to, and the
form's pure logic (validated through Node when available) round-trips
the fictional sample.
"""

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


def test_site_files_exist():
    for name in ("index.html", "styles.css", "app.js", "sample_data.json", "README.md"):
        assert (SITE / name).exists(), f"missing site/{name}"


def test_site_sample_matches_examples_sample():
    # site/sample_data.json is a build-time copy (see site/README.md);
    # the Pages workflow overwrites it with the canonical copy, but
    # the checked-in copy must not drift in the meantime.
    assert json.loads((SITE / "sample_data.json").read_text(encoding="utf-8")) == json.loads(
        (ROOT / "examples" / "sample_data.json").read_text(encoding="utf-8")
    )


def test_index_references_only_shipped_files():
    html = (SITE / "index.html").read_text(encoding="utf-8")
    for ref in ('href="styles.css"', 'src="app.js"', 'href="sample-output.docx"', 'href="sample_data.json"'):
        assert ref in html, f"index.html missing reference {ref}"
    # The page must not promise DOCX generation in the browser: the
    # CLI is the generator, and the page says so.
    assert "does <em>not</em> generate the DOCX itself" in html


def test_pages_workflow_stages_what_the_page_links():
    workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    for fragment in (
        "configure-pages",
        "upload-pages-artifact",
        "deploy-pages",
        "pages: write",
        "id-token: write",
        "pytest -q",
        "tech6-cv-generator generate examples/sample_data.json",
        "cp examples/sample_data.json site-build/sample_data.json",
        "sample-output.docx",
        "path: site-build",
    ):
        assert fragment in workflow, f"pages.yml missing {fragment!r}"


def test_app_js_syntax_and_sample_round_trip():
    node = shutil.which("node")
    if node is None:
        import pytest

        pytest.skip("node not available")
    subprocess.run([node, "--check", str(SITE / "app.js")], check=True)
    script = """
const f = require(process.argv[1]);
const fs = require('fs');
const sample = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const out = f.buildExpertJson(f.expertFromJson(sample));
if (out.name !== 'Jane Q. Expert') throw new Error('sample round-trip lost the name');
if (f.validateExpert(out).length !== 0) throw new Error('sample should validate clean');
if (f.downloadFilename('../../evil') !== 'evil.json') throw new Error('filename sanitization failed');
console.log('site JS checks passed');
"""
    result = subprocess.run(
        [node, "-e", script, str(SITE / "app.js"), str(ROOT / "examples" / "sample_data.json")],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "site JS checks passed" in result.stdout
