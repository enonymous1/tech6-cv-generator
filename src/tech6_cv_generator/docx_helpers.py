"""Small python-docx helpers, extracted from ``form_builder``.

Why this module exists: the builder used to repeat the same low-level
``OxmlElement``/``qn`` dance in five places (yellow highlighting, cell
borders, cell margins, paragraph borders). A copy-paste slip in any one
of them silently changed the output, because every call site wrapped
the styling in ``try/except: pass``. These helpers are the single place
that knows the XML, and they fail loudly instead of swallowing errors —
a styling failure should fail the build (and be recorded by the
orchestrator), not produce a subtly malformed document.
"""

from __future__ import annotations

from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

HIGHLIGHT_FILL = "FFFF00"
HEADER_FILL = "F2F2F2"


def highlight_run(run, fill: str = HIGHLIGHT_FILL) -> None:
    """Shade one run yellow (or ``fill``) to flag missing/incomplete data.

    Highlighting is a *signal*, not decoration: downstream, the builder's
    report counts highlighted runs so a batch report can say which CVs
    still have gaps. That is why the fill value lives in one constant.
    """
    r_pr = run._r.get_or_add_rPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    r_pr.append(shd)


def shade_cell(cell, fill: str) -> None:
    """Fill a whole table cell with ``fill`` (e.g. a header background)."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_borders(cell, val: str = "single", sz: str = "4", color: str = "000000") -> None:
    """Set all four borders of one cell. ``val="nil"`` hides them."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        elem = OxmlElement(f"w:{edge}")
        elem.set(qn("w:val"), val)
        if val != "nil":
            elem.set(qn("w:sz"), sz)
            elem.set(qn("w:space"), "0")
            elem.set(qn("w:color"), color)
        tc_borders.append(elem)
    tc_pr.append(tc_borders)


def set_table_cell_margins(table, top: str = "120", left: str = "160", bottom: str = "120", right: str = "160") -> None:
    """Set cell padding for a table, in twentieths of a point (dxa).

    The defaults are the values the original builder used for the
    personal-info table; they are parameters here so a future table
    style can reuse the helper without copying the XML again.

    Implementation note, and a cautionary tale: the original builder
    called ``table._tbl.get_or_add_tblPr()``, which does not exist on
    python-docx's ``CT_Tbl`` — the call raised on every build and was
    silently swallowed by a surrounding ``try/except: pass``, so the
    padding was never actually applied. ``CT_Tbl.tblPr`` is the correct
    accessor (it creates the element when absent).
    """
    tbl_pr = table._tbl.tblPr
    tbl_cell_mar = OxmlElement("w:tblCellMar")
    for side, value in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        elem = OxmlElement(f"w:{side}")
        elem.set(qn("w:w"), value)
        elem.set(qn("w:type"), "dxa")
        tbl_cell_mar.append(elem)
    tbl_pr.append(tbl_cell_mar)


def add_paragraph_border(
    paragraph, edge: str, val: str = "single", sz: str = "6", space: str = "1", color: str = "000000"
) -> None:
    """Add a single border (``"top"`` or ``"bottom"``) to a paragraph.

    Used for the horizontal rule after Education and for the signature
    lines, where the visible line is a paragraph border, not a table
    border — the table's own borders are set to ``nil`` in that case.
    """
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = OxmlElement("w:pBdr")
    border = OxmlElement(f"w:{edge}")
    border.set(qn("w:val"), val)
    border.set(qn("w:sz"), sz)
    border.set(qn("w:space"), space)
    border.set(qn("w:color"), color)
    p_bdr.append(border)
    p_pr.append(p_bdr)


def set_run_font_size(run, size_pt: int) -> None:
    """Set a run's font size. Kept as a helper so call sites stop
    wrapping a one-line assignment in ``try/except: pass``."""
    run.font.size = Pt(size_pt)
