import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from document_builder import (  # noqa: E402
    DocumentError,
    InvalidValueError,
    MissingFieldsError,
    TemplateError,
    UnresolvedPlaceholderError,
    build_document,
)

TODAY = "२०८३-०८-०७"


def make_template():
    """A small test template. It is not a real government template."""
    return {
        "form_fields": [
            {"id": "name", "label": "नाम", "type": "text", "required": True},
            {"id": "dob", "label": "जन्म मिति", "type": "date", "required": True},
            {"id": "ward", "label": "वडा नं.", "type": "number", "required": True},
            {"id": "place", "label": "ठेगाना", "type": "text", "required": False},
            {"id": "father", "label": "पिताको नाम", "type": "text", "required": False},
            {"id": "mother", "label": "माताको नाम", "type": "text", "required": False},
            {"id": "phone", "label": "सम्पर्क नं.", "type": "tel", "required": False},
        ],
        "document": {
            "recipient": {
                "designation": "To the Ward Chair,",
                "lines": ["Ward {ward}", "{place}, Nepal"],
            },
            "subject": "Application of {name}",
            "body": ["{name} was born on {dob}."],
            "details": {
                "heading": "Details:",
                "rows": [
                    {"label": "Name", "value": "{name}"},
                    {"label": "Father", "value": "{father}"},
                    {"label": "Mother", "value": "{mother}"},
                    {"label": "Birth date", "value": "{dob}"},
                ],
            },
            "closing": "Please register this birth.",
            "signature": {
                "heading": "Applicant,",
                "name": "{name}",
                "contact": "Contact: {phone}",
            },
        },
    }


def make_data(**extra):
    data = {"name": "Ram Thapa", "dob": "2026-11-23", "ward": "5"}
    data.update(extra)
    return data


def build(template=None, data=None):
    template = make_template() if template is None else template
    data = make_data() if data is None else data
    return build_document(template, data, today_bs=TODAY)


def rows_of(result):
    return [(r["no"], r["label"], r["value"]) for r in result["details"]["rows"]]


class FillTest(unittest.TestCase):
    def test_placeholders_filled(self):
        r = build()
        self.assertEqual(r["subject"], "Application of Ram Thapa")
        self.assertEqual(r["body"], ["Ram Thapa was born on २०८३-०८-०७."])
        self.assertEqual(r["closing"], "Please register this birth.")
        self.assertEqual(r["recipient"]["designation"], "To the Ward Chair,")
        self.assertEqual(r["signature"]["heading"], "Applicant,")
        self.assertEqual(r["signature"]["name"], "Ram Thapa")

    def test_text_fields_unchanged(self):
        r = build(data=make_data(name="Ram Thapa 2nd", place="Tole 12, Room 5"))
        self.assertEqual(r["subject"], "Application of Ram Thapa 2nd")
        self.assertEqual(r["recipient"]["lines"][1], "Tole 12, Room 5, Nepal")

    def test_values_are_trimmed(self):
        r = build(data=make_data(name="  Ram  "))
        self.assertEqual(r["subject"], "Application of Ram")

    def test_braces_in_user_values_are_not_expanded(self):
        r = build(data=make_data(name="{ward}"))
        self.assertEqual(r["subject"], "Application of {ward}")

    def test_input_is_not_modified(self):
        template, data = make_template(), make_data(father="A")
        template_copy, data_copy = copy.deepcopy(template), copy.deepcopy(data)
        build(template, data)
        self.assertEqual(template, template_copy)
        self.assertEqual(data, data_copy)

    def test_date_bs_builtin(self):
        t = make_template()
        t["document"]["closing"] = "Date {date_bs}"
        r = build(t)
        self.assertEqual(r["closing"], "Date " + TODAY)
        self.assertEqual(r["date_bs"], TODAY)

    def test_minimal_template(self):
        t = {
            "form_fields": [{"id": "a", "label": "A", "type": "text", "required": True}],
            "document": {"subject": "S {a}"},
        }
        r = build_document(t, {"a": "x"}, today_bs=TODAY)
        self.assertEqual(r["subject"], "S x")
        self.assertIsNone(r["recipient"])
        self.assertEqual(r["body"], [])
        self.assertIsNone(r["details"])
        self.assertEqual(r["closing"], "")
        self.assertIsNone(r["signature"])


class ConvertTest(unittest.TestCase):
    def test_date_field_converted(self):
        r = build(data=make_data(dob="2026-11-23"))
        self.assertEqual(r["body"][0], "Ram Thapa was born on २०८३-०८-०७.")
        r = build(data=make_data(dob="2023-04-14"))
        self.assertEqual(r["body"][0], "Ram Thapa was born on २०८०-०१-०१.")

    def test_number_field_converted(self):
        self.assertEqual(build(data=make_data(ward="5"))["recipient"]["lines"][0], "Ward ५")
        self.assertEqual(build(data=make_data(ward="12"))["recipient"]["lines"][0], "Ward १२")

    def test_number_zero_and_int(self):
        self.assertEqual(build(data=make_data(ward=0))["recipient"]["lines"][0], "Ward ०")
        self.assertEqual(build(data=make_data(ward=5))["recipient"]["lines"][0], "Ward ५")

    def test_tel_field_converted(self):
        r = build(data=make_data(phone="+977-98 12345"))
        self.assertEqual(r["signature"]["contact"], "Contact: +९७७-९८ १२३४५")

    def test_invalid_date_names_the_field(self):
        with self.assertRaises(InvalidValueError) as ctx:
            build(data=make_data(dob="23/11/2026"))
        self.assertIn("जन्म मिति", str(ctx.exception))


class RequiredTest(unittest.TestCase):
    def test_missing_labels_in_form_order(self):
        with self.assertRaises(MissingFieldsError) as ctx:
            build(data={})
        self.assertEqual(ctx.exception.missing, ["नाम", "जन्म मिति", "वडा नं."])
        for label in ctx.exception.missing:
            self.assertIn(label, str(ctx.exception))

    def test_blank_and_none_count_as_missing(self):
        with self.assertRaises(MissingFieldsError) as ctx:
            build(data={"name": "   ", "dob": None, "ward": ""})
        self.assertEqual(ctx.exception.missing, ["नाम", "जन्म मिति", "वडा नं."])

    def test_optional_fields_may_be_missing(self):
        self.assertIsInstance(build(), dict)

    def test_errors_are_value_errors(self):
        for cls in (DocumentError, TemplateError, MissingFieldsError,
                    InvalidValueError, UnresolvedPlaceholderError):
            with self.subTest(cls=cls.__name__):
                self.assertTrue(issubclass(cls, ValueError))
        self.assertTrue(issubclass(MissingFieldsError, DocumentError))


class RowsTest(unittest.TestCase):
    def test_all_rows_numbered(self):
        r = build(data=make_data(father="A", mother="B"))
        self.assertEqual(rows_of(r), [
            ("१", "Name", "Ram Thapa"),
            ("२", "Father", "A"),
            ("३", "Mother", "B"),
            ("४", "Birth date", "२०८३-०८-०७"),
        ])

    def test_empty_optional_row_dropped_and_renumbered(self):
        r = build(data=make_data(mother="B"))
        self.assertEqual(rows_of(r), [
            ("१", "Name", "Ram Thapa"),
            ("२", "Mother", "B"),
            ("३", "Birth date", "२०८३-०८-०७"),
        ])

    def test_both_optional_rows_dropped(self):
        r = build()
        self.assertEqual(rows_of(r), [
            ("१", "Name", "Ram Thapa"),
            ("२", "Birth date", "२०८३-०८-०७"),
        ])

    def test_no_rows_left_means_no_details(self):
        t = make_template()
        t["document"]["details"]["rows"] = [
            {"label": "Father", "value": "{father}"},
            {"label": "Mother", "value": "{mother}"},
        ]
        self.assertIsNone(build(t)["details"])

    def test_recipient_line_dropped_when_optional_empty(self):
        self.assertEqual(build()["recipient"]["lines"], ["Ward ५"])
        r = build(data=make_data(place="Kathmandu"))
        self.assertEqual(r["recipient"]["lines"], ["Ward ५", "Kathmandu, Nepal"])

    def test_contact_line_omitted_when_empty(self):
        self.assertEqual(build()["signature"]["contact"], "")
        self.assertEqual(build(data=make_data(phone="   "))["signature"]["contact"], "")


class PlaceholderTest(unittest.TestCase):
    def test_undeclared_placeholder_is_an_error(self):
        t = make_template()
        t["document"]["body"].append("{unknown}")
        with self.assertRaises(UnresolvedPlaceholderError) as ctx:
            build(t)
        self.assertEqual(ctx.exception.placeholders, ["unknown"])
        self.assertIn("{unknown}", str(ctx.exception))

    def test_empty_optional_in_running_text_is_an_error(self):
        t = make_template()
        t["document"]["body"].append("Born at {place}")
        with self.assertRaises(UnresolvedPlaceholderError) as ctx:
            build(t)
        self.assertEqual(ctx.exception.placeholders, ["place"])

    def test_optional_in_running_text_ok_when_filled(self):
        t = make_template()
        t["document"]["body"].append("Born at {place}")
        r = build(t, make_data(place="Kathmandu"))
        self.assertEqual(r["body"][-1], "Born at Kathmandu")

    def test_undeclared_user_keys_not_usable(self):
        t = make_template()
        t["document"]["body"].append("{secret}")
        with self.assertRaises(UnresolvedPlaceholderError) as ctx:
            build(t, make_data(secret="x"))
        self.assertEqual(ctx.exception.placeholders, ["secret"])

    def test_all_unresolved_reported_sorted(self):
        t = make_template()
        t["document"]["body"] = ["{zeta} {alpha}", "{zeta}"]
        with self.assertRaises(UnresolvedPlaceholderError) as ctx:
            build(t)
        self.assertEqual(ctx.exception.placeholders, ["alpha", "zeta"])


class TemplateErrorTest(unittest.TestCase):
    def test_missing_document_block(self):
        t = make_template()
        del t["document"]
        with self.assertRaises(TemplateError):
            build(t)

    def test_missing_form_fields(self):
        t = make_template()
        del t["form_fields"]
        with self.assertRaises(TemplateError):
            build(t)

    def test_missing_subject(self):
        t = make_template()
        t["document"]["subject"] = "  "
        with self.assertRaises(TemplateError):
            build(t)

    def test_duplicate_field_id(self):
        t = make_template()
        t["form_fields"].append({"id": "name", "label": "again", "type": "text"})
        with self.assertRaises(TemplateError):
            build(t)

    def test_reserved_field_id(self):
        t = make_template()
        t["form_fields"].append({"id": "date_bs", "label": "x", "type": "text"})
        with self.assertRaises(TemplateError):
            build(t)

    def test_bad_field_id(self):
        t = make_template()
        t["form_fields"].append({"id": "child name", "label": "x", "type": "text"})
        with self.assertRaises(TemplateError):
            build(t)

    def test_user_data_not_a_dict(self):
        with self.assertRaises(DocumentError):
            build_document(make_template(), None, today_bs=TODAY)

    def test_body_must_be_a_list(self):
        t = make_template()
        t["document"]["body"] = "just text"
        with self.assertRaises(TemplateError):
            build(t)


if __name__ == "__main__":
    unittest.main()
