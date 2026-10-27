from tech6_cv_generator import FormBuilder


def test_contact_normalization_string(tmp_path):
    builder = FormBuilder({"name": "Jane Q. Expert", "contact": "jane@example.com"})
    out = builder.build(output_path=str(tmp_path / "contact.docx"))
    assert builder.report["missing_contact"] is False
    assert out.endswith("contact.docx")


def test_contact_normalization_empty(tmp_path):
    builder = FormBuilder({"name": "Jane Q. Expert", "contact": {}})
    builder.build(output_path=str(tmp_path / "contact.docx"))
    assert builder.report["missing_contact"] is True
    assert builder.report["highlighted_count"] >= 1
