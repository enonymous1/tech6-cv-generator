import re
from datetime import datetime
from typing import Any, Dict, List, Optional

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\+?\d[\d \-()]{5,}\d")


def _normalize_date(value: Optional[str]) -> str:
    """Normalize common date strings into a consistent, compact format.

    - 'DD/MM/YYYY' -> 'YYYY-MM-DD'
    - 'MM/YYYY' -> 'YYYY-MM'
    - 'YYYY' -> 'YYYY'
    - Empty, 'Not Listed in CV', 'Not listed', or clearly placeholder -> ''
    Otherwise return original trimmed string.
    """
    if not value:
        return ""
    v = str(value).strip()
    if not v or v.lower() in ("not listed in cv", "not listed", "n/a", "not available"):
        return ""

    # DD/MM/YYYY
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", v)
    if m:
        d, mth, y = m.groups()
        try:
            return datetime(int(y), int(mth), int(d)).strftime("%Y-%m-%d")
        except Exception:
            return v

    # MM/YYYY
    m = re.match(r"^(\d{1,2})/(\d{4})$", v)
    if m:
        mth, y = m.groups()
        try:
            return f"{y}-{int(mth):02d}"
        except Exception:
            return v

    # ISO-like YYYY-MM-DD or YYYY-MM
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", v)
    if m:
        return v
    m = re.match(r"^(\d{4})-(\d{2})$", v)
    if m:
        return v

    # Year only
    m = re.match(r"^(\d{4})$", v)
    if m:
        return v

    return v


def _parse_contact(value: Any) -> Dict[str, str]:
    """Return a contact object {email, phone} from a string or dict input."""
    if not value:
        return {"email": "", "phone": ""}

    if isinstance(value, dict):
        # try common keys
        email = value.get("email") or value.get("Email") or value.get("e-mail", "")
        phone = value.get("phone") or value.get("Phone") or value.get("telephone") or value.get("tel", "")
        # if nested contact is a single string like 'Tel: 123 / name@example.com', fall back to parsing
        if (not email and isinstance(value, dict)) and any(isinstance(x, str) and ("@" in x or any(ch.isdigit() for ch in x)) for x in value.values()):
            # flatten values
            combined = " ".join(str(x) for x in value.values())
            found_email = EMAIL_RE.search(combined)
            found_phone = PHONE_RE.search(combined)
            return {"email": found_email.group(0) if found_email else "", "phone": found_phone.group(0) if found_phone else ""}
        return {"email": email or "", "phone": phone or ""}

    # string
    s = str(value)
    found_email = EMAIL_RE.search(s)
    found_phone = PHONE_RE.search(s)
    return {"email": found_email.group(0) if found_email else "", "phone": found_phone.group(0) if found_phone else ""}


def _normalize_languages(langs: Any) -> List[str]:
    out: List[str] = []
    if not langs:
        return out
    if isinstance(langs, str):
        # split on semicolon or comma
        parts = re.split(r"[,;]\s*", langs)
        return [p.strip() for p in parts if p.strip()]
    if isinstance(langs, list):
        for item in langs:
            if isinstance(item, dict):
                lang = item.get("language") or item.get("name") or ""
                prof = item.get("proficiency") or item.get("proficiency_level") or ""
                entry = f"{lang} ({prof})".strip()
                out.append(entry if entry != "()" else lang)
            else:
                out.append(str(item).strip())
    return out


def map_kosovo_to_tech6(kosovo: Dict[str, Any]) -> Dict[str, Any]:
    """Map the Kosovo TECH-6-like schema to the project's expected TECH-6 schema.

    This function performs best-effort mapping and some normalization (dates, contact parsing, languages).
    """
    out: Dict[str, Any] = {}
    ep = kosovo.get("expert_profile", {})

    # Personal info
    personal = ep.get("personal_info", {})
    out["name"] = personal.get("full_name", "")
    out["dob"] = _normalize_date(personal.get("date_of_birth", ""))
    out["citizenship"] = personal.get("citizenship") or personal.get("residence_country", "")

    # Position (map proposed position info when present)
    meta = ep.get("meta_data", {})
    proposed_code = meta.get("proposed_position_code") or meta.get("proposed_position") or ""
    proposed_title = meta.get("proposed_position_title") or meta.get("proposed_position_title") or ""
    if proposed_code or proposed_title:
        # Format as 'K-1, TEAM LEADER' if both present
        if proposed_code and proposed_title:
            out["position_title"] = f"{proposed_code}, {proposed_title}"
        else:
            out["position_title"] = proposed_code or proposed_title

    # Contact
    contact = personal.get("contact_details", {})
    out["contact"] = _parse_contact(contact)

    # Education
    education_raw = ep.get("education", [])
    edu: List[Dict[str, str]] = []
    for e in education_raw:
        edu.append({
            "institution": e.get("institution", ""),
            "degree": e.get("degree_diploma", "") or e.get("degree", ""),
            "start_year": _normalize_date(e.get("start_date", "")),
            "end_year": _normalize_date(e.get("end_date", "")),
            "notes": e.get("notes", ""),
        })
    out["education"] = edu or ["{List college/university or other specialized education, giving names of educational institutions, dates attended, degree(s)/diploma(s) obtained}"]

    # Employment
    emp_raw = ep.get("employment_record", [])
    emp: List[Dict[str, str]] = []
    for j in emp_raw:
        period_from = j.get("period_from", "")
        period_to = j.get("period_to", "")
        # Normalize dates inside period where possible
        from_norm = _normalize_date(period_from)
        to_norm = _normalize_date(period_to) or period_to
        if from_norm and to_norm:
            period = f"{from_norm} - {to_norm}"
        else:
            # fall back to original strings as they appear in the CV
            period = f"{period_from} - {period_to}" if (period_from or period_to) else ""

        ref = j.get("reference_contact", {})
        contact_parsed = _parse_contact(ref)
        contact_str_parts = [v for v in (contact_parsed.get("email"), contact_parsed.get("phone")) if v]
        contact_str = " / ".join(contact_str_parts) if contact_str_parts else ""
        emp.append({
            "period": period,
            "title": j.get("position_title", ""),
            "organization": j.get("employer_name", ""),
            "contact": contact_str or j.get("reference_contact", ""),
            "country": j.get("country", ""),
            "summary": j.get("summary_of_activities", ""),
        })
    out["employment"] = emp

    # Memberships & publications
    prof = ep.get("professional_associations", []) or []
    pubs = ep.get("publications", []) or []
    if isinstance(prof, list):
        prof_join = "; ".join(str(x) for x in prof if x)
    else:
        prof_join = str(prof)
    if isinstance(pubs, list):
        pubs_join = "; ".join(str(x) for x in pubs if x)
    else:
        pubs_join = str(pubs)
    combined = "; ".join([p for p in (prof_join, pubs_join) if p])
    out["memberships"] = combined
    # Also expose publications separately if they existed as a list
    if isinstance(pubs, list) and pubs:
        out["publications"] = pubs

    # Languages
    languages = ep.get("language_skills", [])
    out["languages"] = _normalize_languages(languages)

    # Adequacy mapping
    adequacy = ep.get("adequacy_for_assignment", []) or []
    mapped_adequacy = []
    for a in adequacy:
        mapped_adequacy.append({
            "task": a.get("task_assigned", "") or a.get("task", ""),
            "reference": a.get("prior_work_reference", "") or a.get("reference", ""),
        })
    out["adequacy_for_assignment"] = mapped_adequacy

    # Certification
    cert = ep.get("certification_statement", {})
    out["certification_text"] = cert.get("text", "")

    # Authorized rep
    out["authorized_representative"] = cert.get("representative_signature_date") or "{Insert Name of Authorized Representative}"

    return out


def map_flat_to_tech6(flat: Dict[str, Any]) -> Dict[str, Any]:
    """Accept an already flattened TECH-6-like dict and normalize fields."""
    out: Dict[str, Any] = {}
    out["name"] = flat.get("name") or flat.get("full_name") or flat.get("expert_profile", {}).get("personal_info", {}).get("full_name", "")
    out["dob"] = _normalize_date(flat.get("dob") or flat.get("date_of_birth"))
    out["citizenship"] = flat.get("citizenship") or ""
    # contact may be dict or string
    out["contact"] = _parse_contact(flat.get("contact") or flat.get("contact_details") or flat.get("contact_info"))

    # education may already be in canonical form
    if isinstance(flat.get("education"), list):
        edu = []
        for e in flat.get("education", []):
            if isinstance(e, dict):
                edu.append({
                    "institution": e.get("institution", ""),
                    "degree": e.get("degree", ""),
                    "start_year": _normalize_date(e.get("start_year") or e.get("start_date")),
                    "end_year": _normalize_date(e.get("end_year") or e.get("end_date")),
                    "notes": e.get("notes", ""),
                })
            else:
                edu.append(str(e))
        out["education"] = edu
    else:
        out["education"] = flat.get("education", [])

    # employment
    if isinstance(flat.get("employment"), list):
        emp = []
        for j in flat.get("employment", []):
            if isinstance(j, dict):
                emp.append({
                    "period": j.get("period", ""),
                    "title": j.get("title", ""),
                    "organization": j.get("organization", ""),
                    "contact": j.get("contact", ""),
                    "country": j.get("country", ""),
                    "summary": j.get("summary", ""),
                })
            else:
                emp.append({"period": "", "title": "", "organization": str(j), "contact": "", "country": "", "summary": ""})
        out["employment"] = emp
    else:
        out["employment"] = flat.get("employment", [])

    out["memberships"] = flat.get("memberships") or ""
    out["publications"] = flat.get("publications")
    out["languages"] = _normalize_languages(flat.get("languages"))
    out["adequacy_for_assignment"] = flat.get("adequacy_for_assignment") or flat.get("tasks") or []
    out["certification_text"] = flat.get("certification_text") or flat.get("certification_statement") or ""
    out["authorized_representative"] = flat.get("authorized_representative") or "{Insert Name of Authorized Representative}"

    # position title
    out["position_title"] = flat.get("position_title") or flat.get("position") or ""

    return out


def map_to_canonical(data: Dict[str, Any]) -> Dict[str, Any]:
    """Top-level entry point to convert various input shapes into the canonical TECH-6 structure.

    - If `expert_profile` present, use Kosovo mapper
    - If top-level `name` present assume flattened and normalize
    - Otherwise return the input unchanged
    """
    if not data:
        return {}
    if "expert_profile" in data:
        return map_kosovo_to_tech6(data)
    if data.get("name") or data.get("position_title"):
        return map_flat_to_tech6(data)
    # unknown shape: try to find an expert_profile inside
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict) and "personal_info" in v:
                return map_kosovo_to_tech6(v)
    # fallback: return as-is
    return data


__all__ = ["map_kosovo_to_tech6", "map_flat_to_tech6", "map_to_canonical"]
