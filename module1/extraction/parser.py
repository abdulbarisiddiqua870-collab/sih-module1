from __future__ import annotations

import re

from module1.models.schemas import (
    COMMON_OR_GENERIC_NAME,
    CONSUMER_CARE,
    COUNTRY_OF_ORIGIN,
    BEST_BEFORE_USE_BY,
    DIMENSIONS,
    MANUFACTURER_ADDRESS,
    MANUFACTURER_NAME,
    MANUFACTURE_PACK_IMPORT_DATE,
    IMPORTER_ADDRESS,
    IMPORTER_NAME,
    MRP,
    NET_QUANTITY,
    PACKER_ADDRESS,
    PACKER_NAME,
    PRODUCT_NAME,
    UNIT_SALE_PRICE,
    KNOWN_FIELDS,
    DetectionStatus,
    FieldResult,
    UnmappedDetection,
)
from module1.extraction.validation import (
    BARE_MONEY_RE,
    UNANCHORED_FACTOR,
    Verdict,
    accept,
    validate_best_before,
    validate_contact,
    validate_entity_name,
    validate_manufacture_date,
    validate_mrp_amount,
    validate_net_quantity,
    validate_product_name,
)
from module1.ocr.engine import OcrLine, OcrResult
from module1.ocr.text import clean_line

DETECT_THRESHOLD = 0.45
MAX_UNMAPPED = 100
MAX_EVIDENCE_CHARS = 300

AMOUNT = r"(\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)"

MRP_RE = re.compile(
    r"\bm[\s.\-]*r[\s.\-]*p\.?\b[^0-9\n]{0,24}(?:₹|inr\.?|rs\.?)?\s*" + AMOUNT,
    re.IGNORECASE,
)
UNIT_PRICE_RE = re.compile(r"\bunit\s*(?:sale\s*)?price\b[^0-9\n]{0,30}" + AMOUNT, re.IGNORECASE)
NET_QTY_RE = re.compile(
    r"\bnet\s*(?:qty\.?|quantity|wt\.?|weight|contents?|vol\.?|volume|measure\w*)\b"
    r"[^0-9\n]{0,18}(\d+(?:[.,]\d+)?)\s*"
    r"(kilograms?|kgs?|milliliters?|millilitres?|mls?|liters?|litres?|ltrs?|lts?|grams?|gms?|gr|g|ml|l|cl)\b\.?",
    re.IGNORECASE,
)

DATE_RE = re.compile(
    r"\b(?:0?[1-9]|[12]\d|3[01])[/.-](?:0?[1-9]|1[0-2])[/.-](?:20\d{2}|\d{2})"
    r"|\b(?:0?[1-9]|1[0-2])[/.-](20\d{2})\b"
    r"|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s./-]?(?:20\d{2}|\d{2})\b"
    r"|\b(?:20\d{2})[/.-](?:0?[1-9]|1[0-2])\b",
    re.IGNORECASE,
)
MFG_DATE_KEY_RE = re.compile(
    r"\b(?:mfg|mfd|mkd|manufact\w*|production|prod|packed|pkgd?|pkd|pre[\s-]?pack\w*|import(?:ed)?)\b"
    r"(?:\s*(?:date|dt))?\.?\s*[:\-]?",
    re.IGNORECASE,
)

BEST_BEFORE_RE = re.compile(
    r"\b(best\s*before|use\s*by|use\s*within|exp(?:iry)?(?:\s*date|\s*dt)?)\b\s*[:\-]?\s*(.*)",
    re.IGNORECASE,
)

COUNTRY_RE = re.compile(
    r"\bcountry\s*of\s*origin\b\s*[:\-]?\s*([A-Za-z][A-Za-z\s]{1,39})|\bmade\s*in\b\s*[:\-]?\s*([A-Za-z][A-Za-z\s]{1,39})",
    re.IGNORECASE,
)

CONSUMER_CARE_KEY_RE = re.compile(
    r"\bconsumer\s*(?:care|services)|\bcustomer\s*care|\bhelpline\b|toll[\s-]?free|\bgrievance\b|"
    r"\bfeedback\b|\bcontact\s*(?:us|no\.?|number)?\b",
    re.IGNORECASE,
)
PHONE_RE = re.compile(
    r"(?:\+?91[\s-]?)?[6-9]\d{9}\b|\b1800[\s-]?\d{3,4}[\s-]?\d{3,4}\b|\b0\d{2,4}[\s-]?\d{6,8}\b"
)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
URL_RE = re.compile(r"\b(?:https?://|www\.)[^\s]{4,}", re.IGNORECASE)

ENTITY_PATTERNS: dict[str, re.Pattern[str]] = {
    "manufacturer": re.compile(r"\b(manufactur\w*|mfg|mfd|mkd)\b(?:\s*by)?\s*[:\-]?\s*(.*)", re.IGNORECASE),
    "packer": re.compile(r"\b(packer|packed|pkd|packaged|pre[\s-]?pack\w*)\b(?:\s*by)?\s*[:\-]?\s*(.*)", re.IGNORECASE),
    "importer": re.compile(r"\b(importer|imported|imp)\b(?:\s*by)?\s*[:\-]?\s*(.*)", re.IGNORECASE),
}
ENTITY_FIELDS = {
    "manufacturer": (MANUFACTURER_NAME, MANUFACTURER_ADDRESS),
    "packer": (PACKER_NAME, PACKER_ADDRESS),
    "importer": (IMPORTER_NAME, IMPORTER_ADDRESS),
}

ADDRESS_HINT_RE = re.compile(
    r"\d|[,&]|nagar|road|\brd\b|street|\bst\b|area|sector|phase|industrial|complex|tower|floor|pin",
    re.IGNORECASE,
)
ADDRESS_STOP_RE = re.compile(
    r"\bm[\s.\-]*r[\s.\-]*p\b|\bnet\s|\bbest\s*before\b|\buse\s*b[oy]\b|\bcountry\b|\bconsumer\b|"
    r"\bcustomer\b|\bhelpline\b|\bmfg\b|\bmfd\b|\bpkd\b|\bimport",
    re.IGNORECASE,
)
DIMENSIONS_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*[xX\u00d7]\s*(\d+(?:\.\d+)?)\s*(?:[xX\u00d7]\s*(\d+(?:\.\d+)?))?\s*(cm|mm|m|inch|in)?\b"
)

STANDALONE_QTY_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(kilograms?|kgs?|milliliters?|millilitres?|liters?|litres?|grams?|gms?|g|ml|l|cl|pcs)\b\.?",
    re.IGNORECASE,
)
FIELD_KEYWORD_GUARD_RE = re.compile(
    r"\bm[\s.\-]*r[\s.\-]*p\b|\bnet\s|\bunit\s*(?:sale\s*)?price\b|\bbest\s*before\b|\buse\s*b[oy]\b|"
    r"\bexp(?:iry)?\b|\bmfg\b|\bmfd\b|\bpacked?\b|\bmanufactur\w*\b|\bimport(?:ed|er)?\b|"
    r"\bconsumer\s*care\b|\bcustomer\s*care\b|\bhelpline\b|\bcountry\b|\bingredients?\b",
    re.IGNORECASE,
)

UNIT_ALIASES = {
    "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg",
    "g": "g", "gm": "g", "gms": "g", "gr": "g", "gram": "g", "grams": "g",
    "ml": "ml", "mls": "ml", "millilitre": "ml", "millilitres": "ml", "milliliter": "ml", "milliliters": "ml",
    "l": "l", "lt": "l", "lts": "l", "ltr": "l", "ltrs": "l", "litre": "l", "litres": "l", "liter": "l", "liters": "l",
    "cl": "cl",
    "pcs": "pcs", "pc": "pcs", "pieces": "pcs", "piece": "pcs", "units": "units", "unit": "units",
}


def _clean_amount(raw: str) -> str:
    if "," in raw:
        thousands = re.fullmatch(r"\d{1,3}(?:,\d{2,3})+(?:\.\d+)?", raw)
        if thousands:
            return raw.replace(",", "")
        if re.fullmatch(r"\d+,\d{1,2}", raw):
            return raw.replace(",", ".")
        return raw.replace(",", "")
    return raw


def _normalize_unit(unit: str) -> str:
    key = unit.lower().rstrip(".")
    return UNIT_ALIASES.get(key, key)


def _union_bbox(boxes: list[list[int]]) -> list[int]:
    return [
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    ]


class _Extractor:
    def __init__(self, ocr_result: OcrResult, image_height_px: int) -> None:
        self.lines = ocr_result.lines
        self.image_height_px = image_height_px
        self.used: set[int] = set()
        self.fields: dict[str, FieldResult] = {}
        self.unmapped: list[UnmappedDetection] = []

    def free(self, index: int) -> bool:
        return index not in self.used and index < len(self.lines)

    def build(
        self,
        value: str | None,
        evidence_lines: list[OcrLine],
        confidence01: float,
        scale: float = 1.0,
        verdict: Verdict | None = None,
    ) -> FieldResult:
        boxes = [line.bounding_box for line in evidence_lines if line.bounding_box]
        bbox = _union_bbox(boxes) if boxes else None
        validation_strength = verdict.strength if verdict is not None else 1.0
        confidence = round(max(0.0, min(1.0, confidence01 * scale * validation_strength)), 3)
        if verdict is not None and verdict.status == "weak":
            status = DetectionStatus.UNCERTAIN
        elif confidence >= DETECT_THRESHOLD:
            status = DetectionStatus.DETECTED
        elif confidence > 0.0:
            status = DetectionStatus.UNCERTAIN
        else:
            status = DetectionStatus.NOT_DETECTED
        char_height = max((line.char_height_px for line in evidence_lines), default=None)
        evidence = " | ".join(line.text for line in evidence_lines)[:MAX_EVIDENCE_CHARS]
        return FieldResult(
            value=value,
            detection_status=status,
            confidence=confidence,
            evidence=evidence,
            bounding_box=bbox,
            region_width_px=(bbox[2] - bbox[0]) if bbox else None,
            region_height_px=(bbox[3] - bbox[1]) if bbox else None,
            char_height_px=char_height,
        )

    def add(self, name: str, result: FieldResult) -> None:
        self.fields[name] = result

    def find(self, pattern: re.Pattern[str], start: int = 0) -> tuple[int, re.Match[str]] | None:
        for index in range(start, len(self.lines)):
            if index in self.used:
                continue
            match = pattern.search(self.lines[index].text)
            if match:
                return index, match
        return None

    def match_simple(
        self,
        pattern: re.Pattern[str],
        name: str,
        group: int,
        scale: float = 1.0,
        validator=None,
    ) -> bool:
        found = self.find(pattern)
        if not found:
            return False
        index, match = found
        raw_value = match.group(group)
        if raw_value is None:
            return False
        value = clean_line(raw_value.strip())
        if not value:
            return False
        if validator is not None and not validator(value, self.lines[index].text).usable:
            return False
        self.used.add(index)
        self.add(name, self.build(value, [self.lines[index]], self.lines[index].confidence, scale))
        return True

    def match_mrp(self) -> None:
        matched = self.match_simple(
            MRP_RE,
            MRP,
            group=1,
            validator=lambda amount, _line: validate_mrp_amount(amount),
        )
        if matched:
            return
        self._match_bare_money()

    def _match_bare_money(self) -> None:
        for index, line in enumerate(self.lines):
            if index in self.used or FIELD_KEYWORD_GUARD_RE.search(line.text):
                continue
            match = BARE_MONEY_RE.search(line.text)
            if not match:
                continue
            amount = match.group(1)
            verdict = validate_mrp_amount(amount)
            if not verdict.usable:
                continue
            weak_verdict = Verdict("weak", "currency_without_mrp_keyword")
            self.used.add(index)
            self.add(
                MRP,
                self.build(
                    amount,
                    [line],
                    line.confidence,
                    scale=UNANCHORED_FACTOR,
                    verdict=weak_verdict,
                ),
            )
            return

    def match_unit_price(self) -> None:
        self.match_simple(UNIT_PRICE_RE, UNIT_SALE_PRICE, group=1)

    def match_net_quantity(self) -> None:
        found = self.find(NET_QTY_RE)
        if not found:
            self._match_standalone_quantity()
            return
        index, match = found
        number = match.group(1).replace(",", "")
        unit = _normalize_unit(match.group(2))
        verdict = validate_net_quantity(number, unit)
        if not verdict.usable:
            return
        self.used.add(index)
        self.add(
            NET_QUANTITY,
            self.build(f"{number} {unit}", [self.lines[index]], self.lines[index].confidence, verdict=verdict),
        )

    def _match_standalone_quantity(self) -> None:
        for index, line in enumerate(self.lines):
            if index in self.used or FIELD_KEYWORD_GUARD_RE.search(line.text):
                continue
            match = STANDALONE_QTY_RE.fullmatch(clean_line(line.text))
            if not match:
                continue
            number = match.group(1).replace(",", "")
            unit = _normalize_unit(match.group(2))
            verdict = Verdict("weak", "quantity_without_net_keyword")
            self.used.add(index)
            self.add(
                NET_QUANTITY,
                self.build(
                    f"{number} {unit}",
                    [line],
                    line.confidence,
                    scale=UNANCHORED_FACTOR,
                    verdict=verdict,
                ),
            )
            return

    def match_manufacture_date(self) -> None:
        for index, line in enumerate(self.lines):
            if index in self.used or not MFG_DATE_KEY_RE.search(line.text):
                continue
            date_match = DATE_RE.search(line.text)
            consumed = [index]
            if not date_match and self.free(index + 1):
                date_match = DATE_RE.search(self.lines[index + 1].text)
                if date_match:
                    consumed.append(index + 1)
            if not date_match:
                continue
            verdict = validate_manufacture_date(date_match.group(0))
            self.used.update(consumed)
            evidence_lines = [self.lines[i] for i in consumed]
            confidence = sum(l.confidence for l in evidence_lines) / len(evidence_lines)
            self.add(
                MANUFACTURE_PACK_IMPORT_DATE,
                self.build(date_match.group(0).strip(), evidence_lines, confidence, verdict=verdict),
            )
            return

    def match_best_before(self) -> None:
        found = self.find(BEST_BEFORE_RE)
        if not found:
            return
        index, match = found
        detail = clean_line(match.group(2).strip())
        consumed = [index]
        if len(detail) < 2 and self.free(index + 1):
            detail = clean_line(self.lines[index + 1].text)
            if detail:
                consumed.append(index + 1)
        if not detail:
            return
        verdict = validate_best_before(detail)
        self.used.update(consumed)
        evidence_lines = [self.lines[i] for i in consumed]
        confidence = sum(l.confidence for l in evidence_lines) / len(evidence_lines)
        self.add(
            BEST_BEFORE_USE_BY,
            self.build(detail[:60], evidence_lines, confidence, verdict=verdict),
        )

    def match_country(self) -> None:
        found = self.find(COUNTRY_RE)
        if not found:
            return
        index, match = found
        value = clean_line((match.group(1) or match.group(2)).strip(" .,-"))
        if not value:
            return
        self.used.add(index)
        self.add(COUNTRY_OF_ORIGIN, self.build(value.title(), [self.lines[index]], self.lines[index].confidence))

    def match_consumer_care(self) -> None:
        for index, line in enumerate(self.lines):
            if index in self.used or not CONSUMER_CARE_KEY_RE.search(line.text):
                continue
            window: list[int] = [index]
            for offset in (1, 2):
                if self.free(index + offset):
                    window.append(index + offset)
            hit_index: int | None = None
            value: str | None = None
            for candidate_index in window:
                candidate_text = self.lines[candidate_index].text
                phone_match = PHONE_RE.search(candidate_text)
                email_match = EMAIL_RE.search(candidate_text)
                url_match = URL_RE.search(candidate_text)
                contact_hit = phone_match or email_match or url_match
                if contact_hit:
                    hit_index = candidate_index
                    value = contact_hit.group(0)
                    break
            if value is None or hit_index is None:
                continue
            verdict = validate_contact(value)
            consumed = list(dict.fromkeys(window[: window.index(hit_index) + 1]))
            self.used.update(consumed)
            evidence_lines = [self.lines[i] for i in consumed]
            confidence = sum(l.confidence for l in evidence_lines) / len(evidence_lines)
            self.add(CONSUMER_CARE, self.build(value, evidence_lines, confidence, verdict=verdict))
            return

    def match_entities(self) -> None:
        for entity_key in ("manufacturer", "packer", "importer"):
            pattern = ENTITY_PATTERNS[entity_key]
            name_field, address_field = ENTITY_FIELDS[entity_key]
            for index, line in enumerate(self.lines):
                if index in self.used:
                    continue
                match = pattern.search(line.text)
                if not match:
                    continue
                name = clean_line(match.group(2).strip(" :-,"))
                name_verdict = validate_entity_name(name) if name else None
                if name is not None and name_verdict is not None and not name_verdict.usable:
                    name = None
                address_parts: list[str] = []
                cursor = index + 1
                while cursor < len(self.lines) and len(address_parts) < 3 and cursor not in self.used:
                    candidate = self.lines[cursor]
                    if any(p.search(candidate.text) for p in ENTITY_PATTERNS.values()):
                        break
                    if ADDRESS_STOP_RE.search(candidate.text):
                        break
                    if not ADDRESS_HINT_RE.search(candidate.text):
                        break
                    address_parts.append(candidate.text)
                    cursor += 1
                address = ", ".join(clean_line(part) for part in address_parts)
                if not name and not address:
                    continue
                consumed = [index] + list(range(index + 1, cursor))
                self.used.update(consumed)
                evidence_lines = [self.lines[i] for i in consumed]
                confidence = sum(l.confidence for l in evidence_lines) / len(evidence_lines)
                if name:
                    self.add(name_field, self.build(name, [self.lines[index]], line.confidence, verdict=name_verdict))
                if address:
                    self.add(address_field, self.build(address, evidence_lines, confidence))
                break

    def match_dimensions(self) -> None:
        found = self.find(DIMENSIONS_RE)
        if not found:
            return
        index, match = found
        parts = [match.group(1), match.group(2)]
        if match.group(3):
            parts.append(match.group(3))
        unit = (match.group(4) or "").lower()
        value = " x ".join(parts) + (f" {unit}" if unit else "")
        self.used.add(index)
        self.add(DIMENSIONS, self.build(value, [self.lines[index]], self.lines[index].confidence, scale=0.9))

    def match_product_name(self) -> None:
        candidates: list[tuple[float, int]] = []
        for index, line in enumerate(self.lines):
            if index in self.used or len(line.text) < 3:
                continue
            center_y = (line.bounding_box[1] + line.bounding_box[3]) / 2
            if center_y > self.image_height_px * 0.5:
                continue
            uppercase_boost = 1.25 if line.text.isupper() else 1.0
            digit_penalty = 0.75 if any(ch.isdigit() for ch in line.text) else 1.0
            score = line.char_height_px * (line.confidence**2) * uppercase_boost * digit_penalty
            candidates.append((score, index))
        candidates.sort(key=lambda item: item[0], reverse=True)
        chosen: tuple[int, Verdict] | None = None
        for _, index in candidates[:5]:
            verdict = validate_product_name(self.lines[index].text)
            if verdict.usable:
                chosen = (index, verdict)
                break
        if chosen is None:
            return
        best_index, verdict = chosen
        line = self.lines[best_index]
        self.used.add(best_index)
        self.add(PRODUCT_NAME, self.build(line.text, [line], line.confidence, scale=0.65, verdict=verdict))
        generic = self.fields[PRODUCT_NAME].model_copy(deep=True)
        generic.detection_status = DetectionStatus.UNCERTAIN
        self.add(COMMON_OR_GENERIC_NAME, generic)

    def collect_unmapped(self) -> None:
        for index, line in enumerate(self.lines):
            if index in self.used or len(line.text) < 2 or not any(ch.isalnum() for ch in line.text):
                continue
            if len(self.unmapped) >= MAX_UNMAPPED:
                break
            self.unmapped.append(
                UnmappedDetection(
                    text=line.text,
                    confidence=line.confidence,
                    bounding_box=line.bounding_box,
                    region_width_px=line.bounding_box[2] - line.bounding_box[0],
                    region_height_px=line.bounding_box[3] - line.bounding_box[1],
                    char_height_px=line.char_height_px,
                )
            )

    def run(self) -> None:
        self.match_mrp()
        self.match_unit_price()
        self.match_net_quantity()
        self.match_manufacture_date()
        self.match_best_before()
        self.match_country()
        self.match_consumer_care()
        self.match_entities()
        self.match_dimensions()
        self.match_product_name()
        self.collect_unmapped()
        for name in KNOWN_FIELDS:
            self.fields.setdefault(name, FieldResult())


def extract_fields(ocr_result: OcrResult, image_height_px: int) -> tuple[dict[str, FieldResult], list[UnmappedDetection]]:
    extractor = _Extractor(ocr_result, image_height_px)
    extractor.run()
    return extractor.fields, extractor.unmapped
