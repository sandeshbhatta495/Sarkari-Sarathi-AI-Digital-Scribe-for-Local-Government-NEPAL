"""Build a print-ready document structure from a template and the user's data.

Input : a template dict (with "form_fields" and "document") and user_data.
Output: a plain dict with every text already filled in. The PDF renderer
        only has to draw it. No layout or PDF code lives here.

Rules
- Only fields declared in "form_fields" (plus the built-in {date_bs}) can be
  used as {placeholders}. Other keys in user_data are ignored.
- Required fields are checked first. Missing ones are reported by label.
- Field types: "date" (AD YYYY-MM-DD in, BS Nepali digits out), "number" and
  "tel" (Nepali digits). Every other type is left exactly as typed.
- Lines in lists (recipient lines, detail rows) and the contact line are
  dropped when they use an empty optional field. Detail rows are then
  renumbered. All other text must resolve fully, or an error is raised.
- User values are inserted once and never re-scanned, so a value that
  contains "{something}" is printed as typed.
"""
import re

from dates import DateError, ad_to_bs_nepali, to_nepali_digits, today_bs_nepali

_PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
_FIELD_ID = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_RESERVED_IDS = {"date_bs"}
_DIGIT_TYPES = {"number", "tel"}


class DocumentError(ValueError):
    """Base class for every error raised while building a document."""


class TemplateError(DocumentError):
    """The template itself is wrong (a bug in the template, not the user's data)."""


class MissingFieldsError(DocumentError):
    """One or more required fields are empty. `.missing` holds their labels."""

    def __init__(self, labels):
        self.missing = list(labels)
        super().__init__("Required fields missing: " + ", ".join(self.missing))


class InvalidValueError(DocumentError):
    """A field value cannot be used (for example a bad date)."""


class UnresolvedPlaceholderError(DocumentError):
    """A {placeholder} has no value. `.placeholders` holds the sorted names."""

    def __init__(self, names):
        self.placeholders = sorted(names)
        super().__init__(
            "Unresolved placeholders: " + ", ".join("{%s}" % n for n in self.placeholders)
        )


class _Context:
    """Holds the filled values and collects placeholders that could not be filled."""

    def __init__(self, values, empty_fields):
        self.values = values          # field id -> non-empty text
        self.empty = empty_fields     # declared fields that have no value
        self.unresolved = set()

    def fill(self, text):
        """Fill every {key} in one pass. Unknown or empty keys are recorded."""
        def replace(match):
            name = match.group(1)
            if name in self.values:
                return self.values[name]
            self.unresolved.add(name)
            return match.group(0)

        return _PLACEHOLDER.sub(replace, text)

    def fill_line(self, text):
        """Like fill(), but returns None if the line uses an empty declared field."""
        if any(name in self.empty for name in _PLACEHOLDER.findall(text)):
            return None
        return self.fill(text)


def _text(block, key):
    value = block.get(key, "")
    if not isinstance(value, str):
        raise TemplateError(f"'{key}' must be text")
    return value


def _items(block, key):
    value = block.get(key, [])
    if not isinstance(value, list):
        raise TemplateError(f"'{key}' must be a list")
    return value


def _block(parent, key):
    value = parent.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise TemplateError(f"'{key}' must be an object")
    return value


def _check_fields(template):
    fields = template.get("form_fields")
    if not isinstance(fields, list) or not fields:
        raise TemplateError("Template has no form_fields")
    seen = set()
    for field in fields:
        if not isinstance(field, dict) or not field.get("id"):
            raise TemplateError("Every form field needs an id")
        fid = field["id"]
        if not isinstance(fid, str) or not _FIELD_ID.fullmatch(fid):
            raise TemplateError(f"Field id is not a valid name: {fid!r}")
        if fid in _RESERVED_IDS:
            raise TemplateError(f"Field id is reserved: {fid}")
        if fid in seen:
            raise TemplateError(f"Duplicate field id: {fid}")
        seen.add(fid)
    return fields


def _read_values(fields, user_data):
    """Return (values, empty_ids). Raises if a required field is missing or invalid."""
    cleaned = {}
    empty = set()
    missing = []
    for field in fields:
        fid = field["id"]
        raw = user_data.get(fid)
        text = "" if raw is None else str(raw).strip()
        if text:
            cleaned[fid] = text
        else:
            empty.add(fid)
            if field.get("required"):
                missing.append(field.get("label") or fid)
    if missing:
        raise MissingFieldsError(missing)

    values = {}
    for field in fields:
        fid = field["id"]
        if fid not in cleaned:
            continue
        text = cleaned[fid]
        ftype = field.get("type", "text")
        if ftype == "date":
            try:
                text = ad_to_bs_nepali(text, field=fid)
            except DateError as exc:
                raise InvalidValueError(f"{field.get('label') or fid}: {exc}") from exc
        elif ftype in _DIGIT_TYPES:
            text = to_nepali_digits(text)
        values[fid] = text
    return values, empty


def _build_recipient(block, ctx):
    if block is None:
        return None
    lines = []
    for line in _items(block, "lines"):
        if not isinstance(line, str):
            raise TemplateError("Recipient lines must be text")
        filled = ctx.fill_line(line)
        if filled is not None:
            lines.append(filled)
    return {"designation": ctx.fill(_text(block, "designation")), "lines": lines}


def _build_details(block, ctx):
    if block is None:
        return None
    rows = []
    for row in _items(block, "rows"):
        if not isinstance(row, dict):
            raise TemplateError("Each detail row must be an object")
        value = ctx.fill_line(_text(row, "value"))
        if value is None:
            continue
        rows.append({
            "no": to_nepali_digits(len(rows) + 1),
            "label": ctx.fill(_text(row, "label")),
            "value": value,
        })
    if not rows:
        return None
    return {"heading": ctx.fill(_text(block, "heading")), "rows": rows}


def _build_signature(block, ctx):
    if block is None:
        return None
    contact = ctx.fill_line(_text(block, "contact"))
    return {
        "heading": ctx.fill(_text(block, "heading")),
        "name": ctx.fill(_text(block, "name")),
        "contact": contact or "",
    }


def build_document(template, user_data, today_bs=None):
    """Return the filled document as a plain dict.

    template : dict with "form_fields" and "document".
    user_data: dict of values, as sent by the form.
    today_bs : optional BS date text, for tests. Default is today in Kathmandu.

    Raises a DocumentError subclass for any problem. Nothing is modified.
    """
    if not isinstance(template, dict):
        raise TemplateError("Template must be an object")
    doc = template.get("document")
    if not isinstance(doc, dict):
        raise TemplateError("Template has no 'document' block")
    if not isinstance(user_data, dict):
        raise DocumentError("user_data must be an object")

    fields = _check_fields(template)
    subject = _text(doc, "subject")
    if not subject.strip():
        raise TemplateError("Template 'document' needs a subject")

    values, empty = _read_values(fields, user_data)
    values["date_bs"] = today_bs if today_bs else today_bs_nepali()
    ctx = _Context(values, empty)

    body = []
    for paragraph in _items(doc, "body"):
        if not isinstance(paragraph, str):
            raise TemplateError("Body paragraphs must be text")
        body.append(ctx.fill(paragraph))

    result = {
        "date_bs": values["date_bs"],
        "recipient": _build_recipient(_block(doc, "recipient"), ctx),
        "subject": ctx.fill(subject),
        "body": body,
        "details": _build_details(_block(doc, "details"), ctx),
        "closing": ctx.fill(_text(doc, "closing")),
        "signature": _build_signature(_block(doc, "signature"), ctx),
    }

    if ctx.unresolved:
        raise UnresolvedPlaceholderError(ctx.unresolved)
    return result
