from __future__ import annotations

import re
from dataclasses import dataclass

ACCEPT_STRENGTH = 1.0
WEAK_STRENGTH = 0.6

ANCHORED_FACTOR = 1.0
UNANCHORED_FACTOR = 0.85

MAX_MRP_AMOUNT = 1_000_000.0
MAX_QTY_VALUE = 100_000.0


@dataclass(frozen=True)
class Verdict:
    status: str  # "accept" | "weak" | "reject"
    reason: str

    @property
    def strength(self) -> float:
        return ACCEPT_STRENGTH if self.status == "accept" else WEAK_STRENGTH

    @property
    def usable(self) -> bool:
        return self.status in ("accept", "weak")


def accept(reason: str) -> Verdict:
    return Verdict("accept", reason)


def weak(reason: str) -> Verdict:
    return Verdict("weak", reason)


def reject(reason: str) -> Verdict:
    return Verdict("reject", reason)


TAX_PHRASE_RE = re.compile(
    r"\b(?:incl(?:usive)?\W{0,12}(?:of\s*)?all\s*tax\w*|all\s*tax\w*|tax\w*\s*(?:included|inclusive))\b",
    re.IGNORECASE,
)
FIELD_HEADER_RE = re.compile(
    r"\bm[\s.\-]*r[\s.\-]*p\b|\bnet\s*(?:qty|quantity|wt|weight|vol|volume)\b|\bbest\s*before\b|"
    r"\buse\s*b[oy]\b|\bexp(?:iry)?\b|\bunit\s*(?:sale\s*)?price\b|\bingredients?\b|"
    r"\bconsumer\s*care\b|\bcustomer\s*care\b|\bhelpline\b|\bcountry\s*of\s*origin\b|\bmade\s*in\b|"
    r"\bmanufactur\w*\b|\bmark(et)?ed\s*by\b|\bpacked?\b|\bmfg\b|\bmfd\b|\bstore\s*in\b|"
    r"\bbatch\b|\blot\s*no\b|\blic(?:ence|ense)?\.?\s*no\b|\bfssai\b|\bmarketed\s*by\b",
    re.IGNORECASE,
)
BOILERPLATE_RE = re.compile(
    r"\bfssai\b|\blic(?:ence|ense)\b|\bgrievance\b|\bjurisdiction\b|\bsubject\s*to\b|"
    r"\bdisclaimer\b|\bterms\s*(?:and|&)\s*conditions\b|\bisoo?[\s-]?\d{3,}",
    re.IGNORECASE,
)
PINCODE_RE = re.compile(r"\b\d{6}\b")
ADDRESS_HINT_RE = re.compile(
    r"\b(?:plot|khasra|survey|nagar|road|\brd\b|street|\bst\b|sector|phase|industrial|"
    r"complex|tower|floor|extension|colony|marg)\b",
    re.IGNORECASE,
)
PRICEY_RE = re.compile(r"(?:\u20b9|\brs\.?|\binr\b|\$)\s*\d", re.IGNORECASE)
EMAIL_SHAPE_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_SHAPE_RE = re.compile(r"(?:\+?91[\s-]?)?[6-9]\d{9}\b|\b1800[\s-]?\d{3,4}[\s-]?\d{3,4}\b")
URL_SHAPE_RE = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)
QTY_SHAPE_RE = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:kg|kgs|g|gm|gms|gr|ml|l|lt|cl|pcs|pieces?|units?)\b\.?", re.IGNORECASE)
DATE_SHAPE_RE = re.compile(
    r"\b(?:0?[1-9]|[12]\d|3[01])[/.-](?:0?[1-9]|1[0-2])[/.-](?:20\d{2}|\d{2})\b"
    r"|\b(?:0?[1-9]|1[0-2])[/.-](?:20\d{2})\b"
    r"|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s./-]*(?:20\d{2}|\d{2})\b"
    r"|\b(?:20\d{2})[/.-](?:0?[1-9]|1[0-2])\b",
    re.IGNORECASE,
)
DURATION_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:days?|weeks?|months?|years?)\b", re.IGNORECASE)
ENTITY_STOPWORD_RE = re.compile(
    r"^(?:on|by|in|at|of|for|the|and|to|a|an|no|dt|date|pack|packing|mfg|mfd|mkd)$",
    re.IGNORECASE,
)
NAME_NOISE_RE = re.compile(r"[@\u20b9]|\d{4,}")
ALPHA_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z.&'-]*")

BARE_MONEY_RE = re.compile(r"(?:\u20b9|\brs\.?|\binr\b)\s*(\d{1,6}(?:\.\d{1,2})?)", re.IGNORECASE)


def _alpha_tokens(text: str) -> list[str]:
    return ALPHA_TOKEN_RE.findall(text)


def validate_product_name(text: str) -> Verdict:
    stripped = text.strip()
    if len(stripped) < 3:
        return reject("too_short")
    if TAX_PHRASE_RE.search(stripped):
        return reject("tax_statement")
    if FIELD_HEADER_RE.search(stripped):
        return reject("field_header_or_boilerplate")
    if BOILERPLATE_RE.search(stripped):
        return reject("legal_boilerplate")
    if EMAIL_SHAPE_RE.search(stripped) or URL_SHAPE_RE.search(stripped):
        return reject("contact_info")
    if PHONE_SHAPE_RE.search(stripped.replace(" ", "")):
        return reject("contact_info")
    if PINCODE_RE.search(stripped):
        return reject("address_like")
    if len(set(ADDRESS_HINT_RE.findall(stripped))) >= 2:
        return reject("address_like")
    if DATE_SHAPE_RE.search(stripped) and not _alpha_tokens(stripped):
        return reject("date_like")
    if QTY_SHAPE_RE.fullmatch(stripped.strip(" .,")):
        return reject("quantity_like")
    tokens = _alpha_tokens(stripped)
    if not tokens:
        return reject("no_alphabetic_content")
    letters = sum(ch.isalpha() for ch in stripped)
    nonspace = len(stripped.replace(" ", ""))
    if nonspace == 0:
        return reject("empty")
    letter_ratio = letters / nonspace
    if letter_ratio < 0.4:
        return weak("low_letter_ratio")
    if PRICEY_RE.search(stripped):
        return weak("contains_price")
    digits = sum(ch.isdigit() for ch in stripped)
    if digits / nonspace > 0.34:
        return weak("digit_heavy")
    if len(tokens) == 1:
        return accept("descriptive_title") if len(tokens[0]) >= 4 else weak("single_short_token")
    return accept("descriptive_title")


def validate_mrp_amount(raw_amount: str) -> Verdict:
    try:
        value = float(raw_amount.replace(",", ""))
    except ValueError:
        return reject("not_numeric")
    if value <= 0 or value > MAX_MRP_AMOUNT:
        return reject("implausible_amount")
    return accept("monetary_amount")


def validate_net_quantity(raw_number: str, unit: str) -> Verdict:
    try:
        value = float(raw_number.replace(",", ""))
    except ValueError:
        return reject("not_numeric")
    if not unit:
        return reject("missing_unit")
    if value <= 0 or value > MAX_QTY_VALUE:
        return reject("implausible_quantity")
    return accept("quantity_with_unit")


def validate_manufacture_date(value_text: str) -> Verdict:
    if DATE_SHAPE_RE.search(value_text):
        return accept("recognized_date_shape")
    return weak("unrecognized_date_shape")


def validate_best_before(detail: str) -> Verdict:
    if DURATION_RE.search(detail):
        return accept("duration_pattern")
    if DATE_SHAPE_RE.search(detail):
        return accept("recognized_date_shape")
    return weak("no_date_or_duration_shape")


def validate_entity_name(name: str) -> Verdict:
    stripped = name.strip(" :-,.")
    if len(stripped) < 2:
        return reject("name_too_short")
    if ENTITY_STOPWORD_RE.fullmatch(stripped):
        return reject("stopword_not_a_name")
    if not any(ch.isalpha() for ch in stripped):
        return reject("no_alphabetic_content")
    if NAME_NOISE_RE.search(stripped):
        return weak("noise_in_name")
    return accept("organization_like_name")


def validate_contact(value_text: str) -> Verdict:
    if EMAIL_SHAPE_RE.fullmatch(value_text) or PHONE_SHAPE_RE.fullmatch(value_text):
        return accept("contact_shape")
    if URL_SHAPE_RE.fullmatch(value_text):
        return accept("url_shape")
    return weak("loose_contact_shape")
