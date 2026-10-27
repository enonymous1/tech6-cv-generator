.PHONY: test lint generate-sample

test:
	pytest -q

lint:
	ruff check src tests

# Generate the fictional sample CV into ./outputs (git-ignored).
generate-sample:
	tech6-cv-generator generate examples/sample_data.json
