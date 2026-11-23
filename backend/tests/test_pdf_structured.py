import copy
import os
import sys
import tempfile
import unittest

BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, BACKEND)

import pdf_render  # noqa: E402
from pdf_render import build_html, page_count, render_structured  # noqa: E402

LABELS = ["सन्तानको नाम", "जन्म मिति", "जन्म स्थान", "पिताको नाम",
          "माताको नाम", "हजुरबाको नाम", "हजुरआमाको नाम", "स्थायी ठेगाना"]


def sample_doc():
    """A hand-written document dict. It is not the real birth template."""
    return {
        "date_bs": "२०८३-०८-०७",
        "recipient": {
            "designation": "माननीय वडा अध्यक्षज्यू,",
            "lines": ["काठमाडौं महानगरपालिका, वडा नं. ५", "काठमाडौं, बागमती प्रदेश"],
        },
        "subject": "जन्म दर्ताको निवेदन",
        "body": ["मेरो सन्तान आरव शर्मा (Aarav Sharma) को जन्म भएको २०८३-०१-२७ मा "
                 "स्थान काठमाडौं मा भएको हो।"],
        "details": {
            "heading": "विवरण:",
            "rows": [
                {"no": str(i + 1), "label": LABELS[i], "value": "मान %d" % (i + 1)}
                for i in range(8)
            ],
        },
        "closing": "यस्तो, माथि उल्लिखित विवरण अनुसार मेरो सन्तानको जन्म दर्ता "
                   "गरिदिनुहुन विनम्र निवेदन गर्दछु।",
        "signature": {"heading": "निवेदक,", "name": "राम शर्मा",
                      "contact": "सम्पर्क: ९८१२३४५६७८"},
    }


def body_of(html_text):
    return html_text.split("<body>")[1].split("</body>")[0]


class HtmlTest(unittest.TestCase):
    def test_date_first_and_once(self):
        body = body_of(build_html(sample_doc()))
        date_line = '<div class="date">मिति:'
        self.assertEqual(body.count(date_line), 1)
        self.assertLess(body.index(date_line), body.index("माननीय"))

    def test_no_letterhead(self):
        body = body_of(build_html(sample_doc()))
        self.assertNotIn("नेपाल सरकार", body)
        self.assertNotIn("को कार्यालय", body)

    def test_subject_once(self):
        body = body_of(build_html(sample_doc()))
        self.assertEqual(body.count("विषय:"), 1)
        self.assertEqual(body.count("जन्म दर्ताको निवेदन"), 1)

    def test_white_background_and_black_text(self):
        html_text = build_html(sample_doc())
        self.assertIn("background: #fff", html_text)
        self.assertIn("color: #000", html_text)

    def test_no_dotted_blanks_or_braces_in_body(self):
        body = body_of(build_html(sample_doc()))
        for bad in ("....", "{", "}", "["):
            with self.subTest(bad=bad):
                self.assertNotIn(bad, body)

    def test_values_are_escaped(self):
        doc = sample_doc()
        doc["subject"] = "A <b>&</b>"
        body = body_of(build_html(doc))
        self.assertIn("A &lt;b&gt;&amp;&lt;/b&gt;", body)
        self.assertNotIn("<b>", body)

    def test_rows_in_order_with_numbers(self):
        body = body_of(build_html(sample_doc()))
        self.assertIn('<td class="no">१.</td>'.replace("१", "1"), body)
        self.assertLess(body.index("सन्तानको नाम"), body.index("जन्म स्थान"))
        self.assertLess(body.index("जन्म स्थान"), body.index("स्थायी ठेगाना"))

    def test_optional_parts_missing(self):
        doc = sample_doc()
        doc["recipient"] = None
        doc["details"] = None
        doc["closing"] = ""
        doc["signature"] = None
        body = body_of(build_html(doc))
        for part in ('class="recipient"', 'class="rows"', 'class="end"'):
            with self.subTest(part=part):
                self.assertNotIn(part, body)
        self.assertIn("विषय:", body)

    def test_empty_contact_not_printed(self):
        doc = sample_doc()
        doc["signature"]["contact"] = ""
        self.assertNotIn("सम्पर्क", body_of(build_html(doc)))

    def test_signature_space_and_kept_together(self):
        html_text = build_html(sample_doc())
        self.assertIn("height: 25mm", html_text)
        self.assertIn("break-inside: avoid", html_text)

    def test_font_is_referenced_and_exists(self):
        html_text = build_html(sample_doc())
        self.assertIn("NotoSansDevanagari-Regular.ttf", html_text)
        self.assertTrue(os.path.exists(
            os.path.join(BACKEND, "static", "fonts", "NotoSansDevanagari-Regular.ttf")))


class PdfTest(unittest.TestCase):
    def test_pdf_file_is_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = render_structured(sample_doc(), os.path.join(tmp, "a.pdf"))
            with open(path, "rb") as fh:
                self.assertEqual(fh.read(4), b"%PDF")

    def test_typical_document_is_one_page(self):
        self.assertEqual(page_count(sample_doc()), 1)

    def test_long_document_uses_more_pages(self):
        doc = sample_doc()
        doc["body"] = ["लामो अनुच्छेद। " * 40] * 25
        self.assertGreaterEqual(page_count(doc), 2)

    def test_input_is_not_modified(self):
        doc = sample_doc()
        before = copy.deepcopy(doc)
        build_html(doc)
        page_count(doc)
        self.assertEqual(doc, before)


class LegacyTest(unittest.TestCase):
    def test_legacy_render_pdf_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pdf_render.render_pdf(
                "नमस्ते\nटेस्ट", "birth_registration",
                {"municipality": "काठमाडौं"}, "२०८३-०८-०७",
                os.path.join(tmp, "legacy.pdf"))
            self.assertTrue(os.path.exists(path))


if __name__ == "__main__":
    unittest.main()
