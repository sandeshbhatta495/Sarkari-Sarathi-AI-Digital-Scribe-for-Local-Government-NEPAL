"""Render a government form to a one-page A4 PDF (HTML -> PDF)."""
import html
import os

from weasyprint import HTML

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_URL = "file://" + os.path.join(
    BASE_DIR, "static", "fonts", "NotoSansDevanagari-Regular.ttf"
)

SUBJECTS = {
    "birth_registration": "जन्म दर्ता निवेदन",
    "death_registration": "मृत्यु दर्ता निवेदन",
    "marriage_registration": "विवाह दर्ता निवेदन",
    "divorce_registration": "सम्बन्ध विच्छेद निवेदन",
    "electricity_connection": "विद्युत जडान निवेदन",
    "water_connection": "खानेपानी जडान निवेदन",
    "migration_certificate": "बसाइसराई प्रमाणपत्र निवेदन",
    "residence_certificate": "बसोबास प्रमाणपत्र निवेदन",
    "road_access": "बाटो निकासा निवेदन",
}

CSS = """
@font-face { font-family: 'NotoDev'; src: url('%s'); }
@page { size: A4; margin: 20mm 20mm 18mm 20mm; }
body { font-family: 'NotoDev', sans-serif; font-size: 11pt; line-height: 1.7; color: #000; }
.head { text-align: center; border-bottom: 1px solid #000; padding-bottom: 6px; margin-bottom: 10px; }
.head .gov { font-size: 14pt; }
.head .muni { font-size: 16pt; }
.head .line { font-size: 11pt; }
.date { text-align: right; font-size: 10pt; margin-bottom: 6px; }
.subject { font-size: 12pt; margin-bottom: 10px; }
.body p { margin: 0 0 6px 0; text-align: justify; }
table.sign { width: 100%%; margin-top: 36px; }
table.sign td { width: 50%%; padding-top: 24px; }
table.sign td.r { text-align: right; }
""" % FONT_URL


def _e(value):
    return html.escape(str(value or ""))


def render_pdf(content, dtype, data, date_bs, out_path):
    subject = SUBJECTS.get(dtype, dtype.replace("_", " ").title())
    paras = "".join(
        f"<p>{_e(line)}</p>" if line.strip() else "<p>&nbsp;</p>"
        for line in str(content).split("\n")
    )
    place = ", ".join(x for x in (data.get("district"), data.get("province")) if x)
    ward = f"वडा नं. {_e(data['ward'])} को कार्यालय" if data.get("ward") else ""

    doc = f"""<!doctype html><html lang="ne"><head><meta charset="utf-8">
<style>{CSS}</style></head><body>
<div class="head">
  <div class="gov">नेपाल सरकार</div>
  <div class="muni">{_e(data.get('municipality') or 'स्थानीय तह')}</div>
  <div class="line">{_e(place)}</div>
  <div class="line">{ward}</div>
</div>
<div class="date">मिति: {_e(date_bs)}</div>
<div class="subject">विषय: {_e(subject)}</div>
<div class="body">{paras}</div>
<table class="sign"><tr>
  <td>..................<br>निवेदक</td>
  <td class="r">..................<br>अधिकृत</td>
</tr></table>
</body></html>"""
    HTML(string=doc, base_url=BASE_DIR).write_pdf(out_path)
    return out_path


# ---------------------------------------------------------------------------
# Structured renderer (added). Draws the dict made by document_builder.
# The legacy render_pdf() above is unchanged.
# ---------------------------------------------------------------------------
import html as _html
import os as _os
from pathlib import Path as _Path

from weasyprint import HTML as _HTML

_S_BASE = _os.path.dirname(_os.path.abspath(__file__))
_S_FONT_URL = _Path(
    _os.path.join(_S_BASE, "static", "fonts", "NotoSansDevanagari-Regular.ttf")
).as_uri()

_S_CSS = """
@font-face { font-family: 'NotoDev'; src: url('__FONT__'); }
@page { size: A4; margin: 20mm 22mm 20mm 22mm; background: #fff; }
html, body { background: #fff; color: #000; }
body { font-family: 'NotoDev', 'DejaVu Sans', sans-serif; font-size: 11.5pt;
       line-height: 1.5; margin: 0; }
.date { text-align: right; margin-bottom: 8mm; }
.recipient { margin-bottom: 6mm; }
.subject { margin-bottom: 5mm; }
.subject .u { text-decoration: underline; }
p { margin: 0 0 3mm 0; text-align: justify; }
.heading { margin: 4mm 0 1.5mm 0; break-after: avoid; page-break-after: avoid; }
table.rows { border-collapse: collapse; margin: 0 0 4mm 0; }
table.rows td { padding: 0 0 0.8mm 0; vertical-align: top; }
td.no { width: 9mm; }
td.label { width: 48mm; padding-right: 3mm; }
.end { break-inside: avoid; page-break-inside: avoid; margin-top: 4mm; }
.sig { margin-left: 56%; margin-top: 8mm; }
.sig .space { height: 25mm; }
""".replace("__FONT__", _S_FONT_URL)


def build_html(doc):
    """Return the full HTML text for a document dict made by build_document()."""
    e = _html.escape
    out = ['<div class="date">मिति: %s</div>' % e(doc["date_bs"])]

    rec = doc.get("recipient")
    if rec:
        lines = [x for x in [rec.get("designation", "")] + list(rec.get("lines", [])) if x]
        if lines:
            out.append('<div class="recipient">%s</div>' % "<br>".join(e(x) for x in lines))

    out.append('<div class="subject">विषय: <span class="u">%s</span></div>' % e(doc["subject"]))

    for para in doc.get("body", []):
        out.append("<p>%s</p>" % e(para))

    det = doc.get("details")
    if det:
        if det.get("heading"):
            out.append('<div class="heading">%s</div>' % e(det["heading"]))
        rows = "".join(
            '<tr><td class="no">%s.</td><td class="label">%s:</td><td>%s</td></tr>'
            % (e(r["no"]), e(r["label"]), e(r["value"]))
            for r in det["rows"]
        )
        out.append('<table class="rows">%s</table>' % rows)

    end = []
    if doc.get("closing"):
        end.append("<p>%s</p>" % e(doc["closing"]))
    sig = doc.get("signature")
    if sig:
        parts = []
        if sig.get("heading"):
            parts.append("<div>%s</div>" % e(sig["heading"]))
        parts.append('<div class="space"></div>')
        if sig.get("name"):
            parts.append("<div>%s</div>" % e(sig["name"]))
        if sig.get("contact"):
            parts.append("<div>%s</div>" % e(sig["contact"]))
        end.append('<div class="sig">%s</div>' % "".join(parts))
    if end:
        out.append('<div class="end">%s</div>' % "".join(end))

    return (
        '<!doctype html><html lang="ne"><head><meta charset="utf-8">'
        "<style>%s</style></head><body>%s</body></html>" % (_S_CSS, "\n".join(out))
    )


def render_structured(doc, out_path):
    """Write the document dict as an A4 PDF at out_path. Returns out_path."""
    _HTML(string=build_html(doc), base_url=_S_BASE).write_pdf(out_path)
    return out_path


def page_count(doc):
    """Number of A4 pages the document needs. Used by tests."""
    return len(_HTML(string=build_html(doc), base_url=_S_BASE).render().pages)
