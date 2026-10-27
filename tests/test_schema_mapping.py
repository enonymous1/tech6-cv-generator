from tech6_cv_generator import map_to_canonical


def _kosovo_fixture():
    # Fictional Kosovo-style schema, constructed in the test so no real
    # person's data is needed to cover the mapper.
    return {
        "expert_profile": {
            "meta_data": {"proposed_position_code": "K-1", "proposed_position_title": "TEAM LEADER"},
            "personal_info": {
                "full_name": "Jane Q. Expert",
                "date_of_birth": "17/05/1980",
                "citizenship": "Wonderland",
                "contact_details": {"email": "jane@example.com", "phone": "+1-555-0100"},
            },
            "education": [
                {
                    "institution": "Fictional University",
                    "degree_diploma": "M.Sc. Computer Science",
                    "start_date": "2002",
                    "end_date": "2004",
                }
            ],
            "employment_record": [
                {
                    "period_from": "2020",
                    "period_to": "Present",
                    "position_title": "Lead Consultant",
                    "employer_name": "Acme Consulting Ltd.",
                    "reference_contact": {"email": "ref@example.com", "phone": ""},
                    "country": "Fantasia",
                    "summary_of_activities": "Led a team.",
                }
            ],
            "professional_associations": ["Association of Imaginary Engineers"],
            "publications": [],
            "language_skills": [{"language": "English", "proficiency": "fluent"}],
            "adequacy_for_assignment": [],
            "certification_statement": {"text": "I certify."},
        }
    }


def test_map_kosovo_fixture():
    mapped = map_to_canonical(_kosovo_fixture())
    assert mapped["name"] == "Jane Q. Expert"
    assert mapped["dob"] == "1980-05-17"
    assert mapped["contact"]["email"] == "jane@example.com"
    assert mapped["employment"][0]["organization"] == "Acme Consulting Ltd."
    assert any("English" in lang for lang in mapped["languages"])


def test_map_flat_normalizes_placeholder_dob():
    mapped = map_to_canonical(
        {"name": "Jane Q. Expert", "dob": "Not Listed in CV", "contact": "jane@example.com"}
    )
    assert mapped["dob"] == ""
    assert isinstance(mapped["contact"], dict)


def test_map_unknown_shape_passes_through():
    data = {"unrelated": True}
    assert map_to_canonical(data) == data
