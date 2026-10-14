"""Pattern-based removal of direct identifiers from health conversation text.

Patterns are tuned for English and German text, and to leave clinical
numbers alone (blood pressure 128/80, weight 78.2 kg, 2 kg in 3 days).
They catch structured identifiers well and free-text names poorly. See the
README for what this does and does not protect against.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# --- patterns ---------------------------------------------------------------

EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")

URL = re.compile(r"\b(?:https?://|www\.)[^\s<>\"')\]]+", re.IGNORECASE)

# International (+49 / 0049) or national trunk-prefix (0...) numbers, with
# optional spaces, dashes, slashes or a bracketed area code. Dots are not
# accepted as separators so that dates (03.10.2026) are not read as numbers.
PHONE = re.compile(
    r"(?<![\w/.,])"
    r"(?:(?:\+|00)\d{1,3}[\s\-/]?(?:\(0\)[\s\-]?)?|\(?0)"
    r"\d[\d\s\-/()]{5,}\d"
    r"(?![\w/])"
)
MIN_PHONE_DIGITS = 7

IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}(?:[ ]?[A-Z0-9]{1,4})?\b")

# German statutory health insurance number (Krankenversichertennummer):
# one capital letter followed by nine digits. No checksum is applied, so the
# pattern errs on the side of redacting.
KVNR = re.compile(r"\b[A-Z]\d{9}\b")

_MONTHS = (
    r"jan(?:uary|uar)?|feb(?:ruary|ruar)?|m(?:ar(?:ch)?|ärz|aerz)|apr(?:il)?|ma[iy]|"
    r"jun[ei]?|jul[iy]?|aug(?:ust)?|sep(?:t(?:ember)?)?|o[ck]t(?:ober)?|nov(?:ember)?|"
    r"de[cz](?:ember)?"
)
DATE = re.compile(
    r"\b(?:"
    r"\d{4}-\d{1,2}-\d{1,2}"                                   # 2026-10-14
    r"|\d{1,2}[./]\d{1,2}[./](?:\d{4}|\d{2})(?![\d/])"         # 14.10.2026, 14/10/26
    rf"|\d{{1,2}}\.?\s+(?:{_MONTHS})\.?\s+\d{{4}}"             # 14 October 2026, 14. Okt 2026
    rf"|(?:{_MONTHS})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}"  # October 14, 2026
    r")\b",
    re.IGNORECASE,
)

_STREET_SUFFIX = r"(?:straße|strasse|str\.|weg|allee|platz|gasse|ring|damm|ufer|chaussee)"
ADDRESS = re.compile(
    rf"\b[A-ZÄÖÜ][\wäöüß-]*{_STREET_SUFFIX}\s+\d+\s?[a-zA-Z]?\b"
    r"(?:,?\s+\d{5}\s+[A-ZÄÖÜ][\wäöüß-]+)?"
    r"|\b\d+\s+[A-Z][a-z]+(?:\s[A-Z][a-z]+)?\s(?:Street|St\.|Road|Rd\.|Avenue|Ave\.|Lane|Ln\.|Drive|Dr\.|Close|Way)\b"
)

# Names introduced by an explicit cue. Free-text names without a cue are not
# detected; use a named-entity model for those.
_NAME = r"[A-ZÄÖÜ][a-zäöüß]+(?:[- ][A-ZÄÖÜ][a-zäöüß]+)?"
NAME_AFTER_CUE = re.compile(
    rf"(?:\b(?:[Mm]y name is|[Mm]ein [Nn]ame ist|[Ii]ch heiße|[Ii]ch heisse|[Cc]all me)\s+)({_NAME})"
    rf"|(?:\b(?:Dr|Prof|Mr|Mrs|Ms|Miss|Herr|Frau)\.?\s+)({_NAME})"
)


@dataclass(frozen=True)
class Span:
    kind: str
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class Result:
    text: str
    spans: tuple[Span, ...]


def _iban_is_valid(candidate: str) -> bool:
    s = candidate.replace(" ", "")
    if not 15 <= len(s) <= 34:
        return False
    rearranged = s[4:] + s[:4]
    digits = "".join(str(int(ch, 36)) for ch in rearranged)
    return int(digits) % 97 == 1


def _find(text: str, dates: bool) -> list[Span]:
    spans: list[Span] = []

    def add(kind: str, start: int, end: int) -> None:
        spans.append(Span(kind, start, end, text[start:end]))

    for m in EMAIL.finditer(text):
        add("EMAIL", m.start(), m.end())
    for m in URL.finditer(text):
        add("URL", m.start(), m.end())
    for m in IBAN.finditer(text):
        if _iban_is_valid(m.group(0)):
            add("IBAN", m.start(), m.end())
    for m in KVNR.finditer(text):
        add("INSURANCE_NUMBER", m.start(), m.end())
    for m in ADDRESS.finditer(text):
        add("ADDRESS", m.start(), m.end())
    if dates:
        for m in DATE.finditer(text):
            add("DATE", m.start(), m.end())
    # Phone numbers are the loosest pattern, so they never override a
    # fixed-format match found above (a date followed by a number, say).
    fixed = list(spans)
    for m in PHONE.finditer(text):
        if sum(ch.isdigit() for ch in m.group(0)) < MIN_PHONE_DIGITS:
            continue
        if any(m.start() < s.end and s.start < m.end() for s in fixed):
            continue
        add("PHONE", m.start(), m.end())
    for m in NAME_AFTER_CUE.finditer(text):
        group = 1 if m.group(1) else 2
        add("NAME", m.start(group), m.end(group))
    return spans


def _resolve_overlaps(spans: list[Span]) -> list[Span]:
    """Keep the longest span where spans overlap (earlier wins on ties)."""
    kept: list[Span] = []
    for span in sorted(spans, key=lambda s: (s.start, -(s.end - s.start))):
        if kept and span.start < kept[-1].end:
            if span.end - span.start > kept[-1].end - kept[-1].start:
                kept[-1] = span
            continue
        kept.append(span)
    return kept


def redact(text: str, *, dates: bool = True, placeholder: str = "[{kind}]") -> Result:
    """Replace identifiers in ``text`` with placeholders such as ``[EMAIL]``.

    Set ``dates=False`` to keep calendar dates, for example when a study needs
    them and they are handled separately (shifted or coarsened).
    """
    spans = _resolve_overlaps(_find(text, dates))
    out = []
    last = 0
    for s in spans:
        out.append(text[last:s.start])
        out.append(placeholder.format(kind=s.kind))
        last = s.end
    out.append(text[last:])
    return Result("".join(out), tuple(spans))
