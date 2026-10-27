"""FormBuilder

Provides FormBuilder that accepts a data dictionary and generates a TECH-6 CV Word document.
"""
from pathlib import Path
from typing import Any, Dict, List

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt


class FormBuilder:
    def __init__(self, data: Dict[str, Any]):
        self.data = data or {}
        self.doc = Document()
        # Report of issues/highlights detected during build
        self.report = {
            "missing_personal": [],  # list of personal fields that were missing/placeholder
            "highlighted_count": 0,  # total number of highlighted runs applied
            "employment_highlights": [],  # short descriptions for employment highlights
            "missing_contact": False,  # whether main contact email/phone missing
            "output_path": None,
            "errors": None,
        }

    def build(self, output_path: str = None, output_dir: str = None) -> str:
        """Build the document and save to output_path.

        If output_path is not provided, a filename will be created in
        ``output_dir`` (default ``outputs/`` in the current working directory).
        An existing file is never overwritten: a numeric suffix is appended.
        """
        self._add_header()
        self._add_personal_info()
        self._add_education()
        self._add_employment_records()
        self._add_memberships_and_languages()
        self._add_adequacy_table()
        self._add_contact_and_certification()
        self._add_signatures()

        # Default output file
        if not output_path:
            raw_name = (self.data.get("name") or "").strip()
            # Treat obvious placeholders as missing
            if not raw_name or raw_name.startswith("{") or "insert" in raw_name.lower():
                stem = (self.data.get("_source_stem") or "expert").replace(" ", "_")
                base_name = f"Form_TECH-6_CV_{stem}"
            else:
                base_name = f"Form_TECH-6_CV_{raw_name.replace(' ', '_')}"

            outputs_dir = Path(output_dir) if output_dir else Path("outputs")
            outputs_dir.mkdir(parents=True, exist_ok=True)

            # Avoid overwriting by appending a numeric suffix if file exists
            candidate = outputs_dir / f"{base_name}.docx"
            counter = 1
            while candidate.exists():
                counter += 1
                candidate = outputs_dir / f"{base_name}_{counter}.docx"
            output_path = str(candidate)

        self.doc.save(output_path)
        # record in report
        try:
            self.report["output_path"] = output_path
        except Exception:
            pass
        return output_path

    def _add_header(self):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(6)
        runner = p.add_run("Section 3. Technical Proposal - Standard Forms\n")
        runner.bold = True
        runner.font.size = Pt(10)
        runner = p.add_run("FORM TECH-6\n")
        runner.bold = True
        runner.font.size = Pt(12)
        runner = p.add_run("CURRICULUM VITAE (CV)")
        runner.bold = True
        runner.font.size = Pt(12)
        # small spacer paragraph for visual separation
        spacer = self.doc.add_paragraph()
        spacer.paragraph_format.space_after = Pt(6)

    def _add_personal_info(self):
        table_info = self.doc.add_table(rows=4, cols=2)
        table_info.style = "Table Grid"
        # set column widths (left label narrow, right content wide)
        try:
            table_info.columns[0].width = Inches(2)
            table_info.columns[1].width = Inches(4)
        except Exception:
            pass
        # add small cell padding for readability (top, left, bottom, right in twips/dxa)
        try:
            tbl = table_info._tbl
            tblPr = tbl.get_or_add_tblPr()
            tblCellMar = OxmlElement('w:tblCellMar')
            for side, val in (('top', '120'), ('left', '160'), ('bottom', '120'), ('right', '160')):
                elem = OxmlElement(f'w:{side}')
                elem.set(qn('w:w'), val)
                elem.set(qn('w:type'), 'dxa')
                tblCellMar.append(elem)
            tblPr.append(tblCellMar)
        except Exception:
            pass
        # ensure visible gridlines (table borders) like the PDF - set borders explicitly on each cell
        try:
            for row in table_info.rows:
                for cell in row.cells:
                    tc = cell._tc
                    tcPr = tc.get_or_add_tcPr()
                    tcBorders = OxmlElement('w:tcBorders')
                    for edge in ('top', 'left', 'bottom', 'right'):
                        elem = OxmlElement(f'w:{edge}')
                        elem.set(qn('w:val'), 'single')
                        elem.set(qn('w:sz'), '4')
                        elem.set(qn('w:space'), '0')
                        elem.set(qn('w:color'), '000000')
                        tcBorders.append(elem)
                    tcPr.append(tcBorders)
        except Exception:
            pass

        # Left column labels in bold
        left_labels = ["Position Title and No.", "Name of Expert:", "Date of Birth:", "Country of Citizenship/Residence"]
        values = [self.data.get("position_title", "{e.g., K-1, TEAM LEADER}"),
                  self.data.get("name", "{Insert full name}"),
                  self.data.get("dob", "{day/month/year}"),
                  self.data.get("citizenship", "")]

        for i, label in enumerate(left_labels):
            cell_left = table_info.cell(i, 0)
            cell_left.text = label
            # bold the label run
            for run in cell_left.paragraphs[0].runs:
                run.bold = True
                try:
                    run.font.size = Pt(10)
                except Exception:
                    pass

            # set right cell text and make font a little smaller for compactness
            right_cell = table_info.cell(i, 1)
            val = values[i]
            needs_highlight = False
            # Detect missing or placeholder values (empty, placeholders wrapped in braces, or obvious insert prompts)
            if not isinstance(val, str) or not val.strip() or val.strip().startswith("{") or val.strip().endswith("}") or val.strip().lower().startswith("insert"):
                # Provide a helpful placeholder for empty citizenship field specifically
                if i == 3 and (not isinstance(val, str) or not val.strip()):
                    val = "{Insert country of citizenship/residence}"
                needs_highlight = True

            # Record missing personal field once
            if needs_highlight:
                key_map = ["position_title", "name", "dob", "citizenship"]
                try:
                    key = key_map[i]
                except Exception:
                    key = f"personal_{i}"
                if key not in self.report["missing_personal"]:
                    self.report["missing_personal"].append(key)

            right_cell.text = val
            for run in right_cell.paragraphs[0].runs:
                try:
                    run.font.size = Pt(10)
                except Exception:
                    pass
                try:
                    if needs_highlight:
                        # apply yellow shading to indicate missing or incomplete info
                        rPr = run._r.get_or_add_rPr()
                        shd = OxmlElement('w:shd')
                        shd.set(qn('w:fill'), 'FFFF00')
                        rPr.append(shd)
                except Exception:
                    pass

            # If we added shading, increment the global highlighted counter
            if needs_highlight:
                try:
                    self.report["highlighted_count"] += 1
                except Exception:
                    pass

            # add paragraph spacing (space before/after) to add breathing room inside cells
            try:
                for cell in (cell_left, right_cell):
                    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                    for para in cell.paragraphs:
                        para.paragraph_format.space_before = Pt(4)
                        para.paragraph_format.space_after = Pt(4)
            except Exception:
                pass

        self.doc.add_paragraph()

    def _add_education(self):
        # Education header
        header = self.doc.add_paragraph()
        runner = header.add_run("Education:")
        runner.bold = True
        header.paragraph_format.space_after = Pt(4)

        education = self.data.get("education", "{List college/university or other specialized education, giving names of educational institutions, dates attended, degree(s)/diploma(s) obtained}")
        # If we have a list, render each education entry on its own paragraph for clarity
        if isinstance(education, list):
            for e in education:
                if isinstance(e, dict):
                    inst = e.get("institution", "")
                    degree = e.get("degree", "")
                    yrs = []
                    if e.get("start_year"):
                        yrs.append(str(e.get("start_year")))
                    if e.get("end_year"):
                        yrs.append(str(e.get("end_year")))
                    years = (f" ({' - '.join(yrs)})" if yrs else "")
                    note = f": {e.get('notes')}" if e.get('notes') else ""
                    text = f"{inst} - {degree}{years}{note}"
                else:
                    text = str(e)
                p_edu = self.doc.add_paragraph(text)
                p_edu.paragraph_format.space_after = Pt(2)
        elif isinstance(education, dict):
            p = self.doc.add_paragraph(str(education))
            p.paragraph_format.space_after = Pt(6)
        else:
            p = self.doc.add_paragraph(str(education))
            p.paragraph_format.space_after = Pt(6)

        # tighten spacing after the Education section
        self.doc.add_paragraph()  # small spacer
        self._add_horizontal_rule()

    def _long_text_or_default(self, key: str, default: str, min_length: int = 120) -> str:
        """Return a value from data if it's at least min_length, otherwise return the default."""
        val = self.data.get(key)
        if not val or not isinstance(val, str) or len(val.strip()) < min_length:
            return default
        return val

    def _normalize_contact(self, contact) -> Dict[str, str]:
        """Normalize a contact value (string, dict, list) into a dict with 'email' and 'phone' keys."""
        if isinstance(contact, dict):
            email = contact.get("email") or contact.get("e-mail") or contact.get("email_address") or ""
            phone = contact.get("phone") or contact.get("telephone") or contact.get("mobile") or ""
            return {"email": email or "", "phone": phone or ""}
        if isinstance(contact, list):
            out = {"email": "", "phone": ""}
            for it in contact:
                if isinstance(it, str):
                    if "@" in it and not out["email"]:
                        out["email"] = it
                    elif any(ch.isdigit() for ch in it) and not out["phone"]:
                        out["phone"] = it
                elif isinstance(it, dict):
                    inner = self._normalize_contact(it)
                    out["email"] = out["email"] or inner.get("email", "")
                    out["phone"] = out["phone"] or inner.get("phone", "")
            return out
        if isinstance(contact, str):
            s = contact.strip()
            if "@" in s:
                return {"email": s, "phone": ""}
            if any(ch.isdigit() for ch in s):
                return {"email": "", "phone": s}
            return {"email": "", "phone": ""}
        return {"email": "", "phone": ""}

    def _add_employment_records(self):
        p = self.doc.add_paragraph()
        runner = p.add_run("Employment record relevant to the assignment:")
        runner.bold = True
        p.paragraph_format.space_after = Pt(6)

        # Create table with header row - use 4 columns so Country and Summary are separate columns
        table_emp = self.doc.add_table(rows=1, cols=4)
        table_emp.style = "Table Grid"
        # set column widths to better match the original layout
        try:
            table_emp.columns[0].width = Inches(1.25)  # Period
            table_emp.columns[1].width = Inches(3.5)   # Organization / Title
            table_emp.columns[2].width = Inches(1.0)   # Country
            table_emp.columns[3].width = Inches(2.0)   # Summary
        except Exception:
            pass

        headers = table_emp.rows[0].cells
        headers[0].text = "Period"
        headers[1].text = "Employing organization and your title/position. Contact information for references"
        headers[2].text = "Country"
        headers[3].text = "Summary of activities performed relevant to the Assignment"

        # Format header cells (bold + centered)
        for cell in headers:
            para = cell.paragraphs[0]
            for run in para.runs:
                run.bold = True
                try:
                    run.font.size = Pt(10)
                except Exception:
                    pass
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            try:
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            except Exception:
                pass
            # Optional light gray fill for header
            try:
                tc = cell._tc
                tcPr = tc.get_or_add_tcPr()
                shd = OxmlElement('w:shd')
                shd.set(qn('w:fill'), 'F2F2F2')
                tcPr.append(shd)
            except Exception:
                pass

        employment: List[Dict[str, Any]] = self.data.get("employment", [])
        if not employment:
            # Add a single placeholder row so the table isn't empty
            row = table_emp.add_row().cells
            row[0].text = "[e.g., May 2005-present]"
            row[1].text = "[e.g., Ministry of ..., advisor/consultant to... References: Tel.........]"
            row[2].text = "[Country]"
            row[3].text = "[e.g., summary of activities relevant to the assignment]"
        else:
            for job in employment:
                row = table_emp.add_row().cells
                row[0].text = job.get("period", "")

                # Write organization, title and references each on their own paragraph in the cell.
                cell = row[1]
                # first paragraph: organization (use existing first paragraph)
                if job.get("organization"):
                    cell.paragraphs[0].text = job.get("organization")
                else:
                    # ensure first paragraph exists
                    cell.paragraphs[0].text = ""

                # title on its own line
                if job.get("title"):
                    cell.add_paragraph(job.get("title"))

                # references line - accept string, dict or list for contact/reference info
                contact = job.get("contact") or job.get("reference_contact") or ""

                # Normalize contact to a string if it's a dict or list
                if isinstance(contact, dict):
                    parts = []
                    # prefer explicit name/title then contact details
                    if contact.get("name"):
                        parts.append(contact.get("name"))
                    if contact.get("title"):
                        parts.append(contact.get("title"))
                    if contact.get("email"):
                        parts.append(contact.get("email"))
                    if contact.get("phone"):
                        parts.append(contact.get("phone"))
                    contact_str = " | ".join([p for p in parts if p])
                elif isinstance(contact, list):
                    contact_str = "; ".join(str(c) for c in contact)
                else:
                    contact_str = str(contact)

                contact_lower = contact_str.lower()
                needs_highlight = False
                if not contact_str.strip():
                    ref_text = "References: [missing]"
                    needs_highlight = True
                else:
                    # detect 'on request' phrases
                    if any(phrase in contact_lower for phrase in ("on request", "available on request", "available upon request")):
                        needs_highlight = True
                    # basic detection for email/phone
                    has_email = "@" in contact_str
                    has_phone = any(ch.isdigit() for ch in contact_str)
                    if not (has_email or has_phone):
                        needs_highlight = True
                    ref_text = f"References: {contact_str}"

                p_ref = cell.add_paragraph()
                run = p_ref.add_run(ref_text)
                try:
                    if needs_highlight:
                        # set yellow shading on the run to indicate missing/incomplete references
                        rPr = run._r.get_or_add_rPr()
                        shd = OxmlElement('w:shd')
                        shd.set(qn('w:fill'), 'FFFF00')
                        rPr.append(shd)
                        # record employment highlight and bump the counter
                        try:
                            summary = job.get("organization") or job.get("title") or ref_text
                            self.report["employment_highlights"].append(summary)
                            self.report["highlighted_count"] += 1
                        except Exception:
                            pass
                except Exception:
                    pass

                # Country
                row[2].text = job.get("country", "")
                # Summary
                row[3].text = job.get("summary", "")

        self.doc.add_paragraph()

    def _add_memberships_and_languages(self):
        p = self.doc.add_paragraph()
        runner = p.add_run("Membership in Professional Associations, Publications, and Certifications:")
        runner.bold = True

        # Memberships (optional)
        if self.data.get("memberships"):
            self.doc.add_paragraph(self.data.get("memberships"))

        # Publications (optional) - accept string or list
        pubs = self.data.get("publications")
        if pubs:
            if isinstance(pubs, list):
                p_pub_label = self.doc.add_paragraph()
                r = p_pub_label.add_run("Publications:")
                r.bold = True
                for item in pubs:
                    self.doc.add_paragraph(str(item))
            else:
                p_pub = self.doc.add_paragraph()
                r = p_pub.add_run("Publications: ")
                r.bold = True
                p_pub.add_run(str(pubs))

        # Certifications (optional) - accept string or list
        certs = self.data.get("certifications")
        if certs:
            if isinstance(certs, list):
                p_cert_label = self.doc.add_paragraph()
                r = p_cert_label.add_run("Certifications:")
                r.bold = True
                for c in certs:
                    self.doc.add_paragraph(str(c))
            else:
                p_cert = self.doc.add_paragraph()
                r = p_cert.add_run("Certifications: ")
                r.bold = True
                p_cert.add_run(str(certs))

        p = self.doc.add_paragraph()
        runner = p.add_run("Language Skills (indicate only languages in which you can work):")
        runner.bold = True
        if self.data.get("languages"):
            self.doc.add_paragraph(self.data.get("languages"))

        self.doc.add_paragraph()

    def _add_adequacy_table(self):
        p = self.doc.add_paragraph()
        runner = p.add_run("Adequacy for the Assignment:")
        runner.bold = True

        table_tasks = self.doc.add_table(rows=1, cols=2)
        table_tasks.style = "Table Grid"
        try:
            table_tasks.columns[0].width = Inches(3)
            table_tasks.columns[1].width = Inches(3)
        except Exception:
            pass

        # Set headers
        table_tasks.cell(0, 0).text = "Detailed Tasks Assigned on Consultant's Team of Experts:"
        table_tasks.cell(0, 1).text = "Reference to Prior Work/Assignments that Best Illustrates Capability to Handle the Assigned Tasks"

        # Bold headers and set alignment/font size
        for i in (0, 1):
            cell = table_tasks.cell(0, i)
            para = cell.paragraphs[0]
            for run in para.runs:
                run.bold = True
                try:
                    run.font.size = Pt(10)
                except Exception:
                    pass
            try:
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            except Exception:
                pass

        # Accept new schema key `adequacy_for_assignment` (list of {task, reference})
        adequacy = self.data.get("adequacy_for_assignment")
        # Backward compatibility: also accept `tasks` (string or list)
        if adequacy is None:
            adequacy = self.data.get("tasks")

        if adequacy is None:
            # placeholder
            row = table_tasks.add_row().cells
            row[0].text = "{List all deliverables/tasks as in TECH-5 in which the Expert will be involved}"
            row[1].text = ""
        elif isinstance(adequacy, str):
            row = table_tasks.add_row().cells
            row[0].text = adequacy
            row[1].text = ""
        elif isinstance(adequacy, list):
            for item in adequacy:
                row = table_tasks.add_row().cells
                if isinstance(item, dict):
                    row[0].text = item.get("task", "")
                    row[1].text = item.get("reference", "")
                else:
                    row[0].text = str(item)
                    row[1].text = ""
        else:
            # Unknown type, render its string representation
            row = table_tasks.add_row().cells
            row[0].text = str(adequacy)
            row[1].text = ""


    def _add_contact_and_certification(self):
        p = self.doc.add_paragraph()
        runner = p.add_run("Expert's contact information: ")
        runner.bold = True
        raw_contact = self.data.get("contact", "")
        contact = self._normalize_contact(raw_contact)
        # render labeled contact fields using a small table for alignment
        table_contact = self.doc.add_table(rows=2, cols=2)
        table_contact.style = "Table Grid"
        try:
            table_contact.columns[0].width = Inches(1.2)
            table_contact.columns[1].width = Inches(4.8)
        except Exception:
            pass
        # Label cells bold
        email = contact.get("email", "")
        phone = contact.get("phone", "")
        email_display = email if email else "(e-mail ..................)"
        phone_display = phone if phone else "(phone ............... )"
        table_contact.cell(0, 0).text = "e-mail"
        table_contact.cell(0, 1).text = email_display
        table_contact.cell(1, 0).text = "phone"
        table_contact.cell(1, 1).text = phone_display
        for r in range(2):
            try:
                # bold the label run in left column
                left_cell = table_contact.cell(r, 0)
                for run in left_cell.paragraphs[0].runs:
                    run.bold = True
                    run.font.size = Pt(10)
                # set a small space-after on right cell paragraphs
                right_cell = table_contact.cell(r, 1)
                for para in right_cell.paragraphs:
                    para.paragraph_format.space_after = Pt(2)
                # highlight missing contact fields (email/phone) individually
                if r == 0 and not email:
                    for run in table_contact.cell(0, 1).paragraphs[0].runs:
                        try:
                            rPr = run._r.get_or_add_rPr()
                            shd = OxmlElement('w:shd')
                            shd.set(qn('w:fill'), 'FFFF00')
                            rPr.append(shd)
                        except Exception:
                            pass
                    self.report["highlighted_count"] += 1
                if r == 1 and not phone:
                    for run in table_contact.cell(1, 1).paragraphs[0].runs:
                        try:
                            rPr = run._r.get_or_add_rPr()
                            shd = OxmlElement('w:shd')
                            shd.set(qn('w:fill'), 'FFFF00')
                            rPr.append(shd)
                        except Exception:
                            pass
                    self.report["highlighted_count"] += 1
                # consider contact missing only if both missing
                try:
                    self.report["missing_contact"] = (not email and not phone)
                except Exception:
                    pass
            except Exception:
                pass

        self.doc.add_paragraph()

        p = self.doc.add_paragraph()
        runner = p.add_run("Certification:")
        runner.bold = True
        cert_default = (
            "I, the undersigned, certify that to the best of my knowledge and belief, this CV correctly "
            "describes myself, my qualifications, and my experience, and I am available, as and when "
            "necessary, to undertake the assignment in case of an award. I understand that any misstatement "
            "or misrepresentation described herein may lead to my disqualification or dismissal by the "
            "Client, and/or sanctions by the Bank."
        )
        cert_text = self._long_text_or_default("certification_text", cert_default, min_length=160)
        self.doc.add_paragraph(cert_text)
        self.doc.add_paragraph()
        # Removed horizontal rule here to match PDF: no separator line between Certification and Signatures
        # (Spacing is handled by the signature spacer in _add_signatures)

    def _add_signatures(self):
        def make_signature_row(name_value: str = "", name_label: str = "Name of Expert"):
            table_sig = self.doc.add_table(rows=1, cols=3)
            table_sig.style = "Table Grid"
            try:
                table_sig.columns[0].width = Inches(3)
                table_sig.columns[1].width = Inches(3)
                table_sig.columns[2].width = Inches(2)
            except Exception:
                pass

            # Add a top-border paragraph (the visible line) in each cell
            for c in range(3):
                cell = table_sig.cell(0, c)
                p_line = cell.paragraphs[0]
                try:
                    p_pr = p_line._p.get_or_add_pPr()
                    pbdr = OxmlElement('w:pBdr')
                    top = OxmlElement('w:top')
                    top.set(qn('w:val'), 'single')
                    top.set(qn('w:sz'), '4')
                    top.set(qn('w:color'), 'BFBFBF')
                    pbdr.append(top)
                    p_pr.append(pbdr)
                    # tighter spacing so the label sits close to the line
                    # set zero spacing to reduce offset between the line and subsequent label
                    p_line.paragraph_format.space_before = Pt(0)
                    p_line.paragraph_format.space_after = Pt(0)
                except Exception:
                    pass

            # Name column: label and value under the line
            name_cell = table_sig.cell(0, 0)
            name_label_p = name_cell.add_paragraph(name_label)
            try:
                name_label_p.runs[0].bold = True
                name_label_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                name_label_p.paragraph_format.space_before = Pt(0)
            except Exception:
                pass
            if name_value:
                name_val_p = name_cell.add_paragraph(name_value)
                try:
                    name_val_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    name_val_p.paragraph_format.space_after = Pt(4)
                except Exception:
                    pass

            # Signature column: label under line
            sig_cell = table_sig.cell(0, 1)
            sig_label_p = sig_cell.add_paragraph("Signature")
            try:
                sig_label_p.runs[0].bold = True
                sig_label_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                sig_label_p.paragraph_format.space_before = Pt(0)
            except Exception:
                pass

            # Date column: label + placeholder
            date_cell = table_sig.cell(0, 2)
            date_label_p = date_cell.add_paragraph("Date")
            try:
                date_label_p.runs[0].bold = True
                date_label_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                date_label_p.paragraph_format.space_before = Pt(0)
            except Exception:
                pass
            date_val_p = date_cell.add_paragraph("{day/month/year}")
            try:
                date_val_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                date_val_p.paragraph_format.space_after = Pt(4)
            except Exception:
                pass

            # Remove inner borders so only the top lines (paragraph borders) are visible.
            # Explicitly nil all cell borders (including top) to avoid duplicate/offset lines
            try:
                for row in table_sig.rows:
                    for cell in row.cells:
                        tc = cell._tc
                        tcPr = tc.get_or_add_tcPr()
                        tcBorders = OxmlElement('w:tcBorders')
                        for edge in ('top', 'left', 'bottom', 'right'):
                            elem = OxmlElement(f'w:{edge}')
                            elem.set(qn('w:val'), 'nil')
                            tcBorders.append(elem)
                        tcPr.append(tcBorders)
            except Exception:
                pass
            return table_sig

        # Spacer before signatures
        sp = self.doc.add_paragraph()
        try:
            sp.paragraph_format.space_before = Pt(12)
            sp.paragraph_format.space_after = Pt(6)
        except Exception:
            pass

        # Expert signature row
        expert_name = self.data.get('name', '')
        make_signature_row(expert_name, "Name of Expert")

        # Spacer between the two signature rows
        sp2 = self.doc.add_paragraph()
        try:
            sp2.paragraph_format.space_before = Pt(12)
            sp2.paragraph_format.space_after = Pt(6)
        except Exception:
            pass

        # Authorized Representative signature row
        # Avoid echoing the expert's name as the authorized representative by mistake.
        auth = (self.data.get('authorized_representative') or '').strip()
        try:
            if auth and expert_name:
                # Normalize and token-compare names to catch partial matches like
                # 'Jane Mburu' vs 'Jane Njeri Mburu'
                auth_tokens = [t.lower().strip('.,') for t in auth.split() if t.strip()]
                expert_tokens = [t.lower().strip('.,') for t in expert_name.split() if t.strip()]
                if auth_tokens and expert_tokens and set(auth_tokens).issubset(set(expert_tokens)):
                    auth = '{Insert Name of Authorized Representative}'
                elif auth.lower() in expert_name.lower() or expert_name.lower() in auth.lower():
                    auth = '{Insert Name of Authorized Representative}'
        except Exception:
            # In case of unexpected data types, fall back to placeholder behavior
            auth = '{Insert Name of Authorized Representative}' if not auth else auth
        # If empty, use placeholder
        if not auth:
            auth = '{Insert Name of Authorized Representative}'
        make_signature_row(auth, "Name of authorized Representative of the Consultant (the same who signs the Proposal)")

    def _add_horizontal_rule(self):
        """Insert a horizontal rule (paragraph bottom border) similar to the lines in the PDF."""
        p = self.doc.add_paragraph()
        # create a paragraph border (bottom)
        p_pr = p._p.get_or_add_pPr()
        p_bdr = OxmlElement('w:pBdr')
        bottom = OxmlElement('w:bottom')
        bottom.set(qn('w:val'), 'single')
        bottom.set(qn('w:sz'), '6')
        bottom.set(qn('w:space'), '1')
        bottom.set(qn('w:color'), '000000')
        p_bdr.append(bottom)
        p_pr.append(p_bdr)
