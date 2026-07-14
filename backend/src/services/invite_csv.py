"""Pure invite-CSV parsing + preview categorization — no DB, no I/O.

Handles the messy real files admins produce: UTF-8 BOM (Excel), ';' vs ','
delimiters (Excel in EU locales), header order, extra columns, blank rows.
Whole-file problems raise InvalidCsvError (→ 400); per-row problems are marked
on the row so the admin sees exactly which line failed and why.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass

from src.services.exceptions import InvalidCsvError

__all__ = [
    "MAX_INVITE_CSV_BYTES",
    "MAX_INVITE_ROWS",
    "ParsedRow",
    "PreviewRow",
    "build_preview",
    "parse_invite_csv",
]

MAX_INVITE_CSV_BYTES = 1_048_576  # 1 MiB
MAX_INVITE_ROWS = 200

_REQUIRED_COLUMNS = ("first_name", "last_name", "email")
# Syntactic sanity check only (the DB has no format constraint): one '@', a dot
# in the domain, no spaces. Deliberately lenient — it catches typos, not RFC edge cases.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class ParsedRow:
    row_number: int  # 1-based line in the file (header = line 1)
    first_name: str
    last_name: str
    email: str  # stripped + lowercased when syntactically valid
    error: str | None  # None = a clean candidate


@dataclass
class PreviewRow:
    row_number: int
    first_name: str
    last_name: str
    email: str
    status: str  # valid | duplicate | invalid | created | email_failed
    detail: str | None


def parse_invite_csv(raw: bytes) -> list[ParsedRow]:
    # Friendly nudge for the #1 Excel footgun: a saved .xlsx (ZIP/OOXML) or .xls
    # (OLE) instead of a CSV. Caught before decode so the admin gets guidance,
    # not "not valid UTF-8".
    if raw[:4] in (b"PK\x03\x04", b"\xd0\xcf\x11\xe0"):
        raise InvalidCsvError(
            "This looks like an Excel workbook (.xlsx/.xls). In Excel, use "
            "File → Save As → CSV, then upload the .csv file."
        )
    try:
        text = raw.decode("utf-8-sig")  # utf-8-sig transparently drops a BOM
    except UnicodeDecodeError as exc:
        raise InvalidCsvError("The file is not valid UTF-8 text.") from exc

    lines = text.splitlines()
    if not lines or not lines[0].strip():
        raise InvalidCsvError("The CSV file is empty.")

    delimiter = ";" if lines[0].count(";") > lines[0].count(",") else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    header = next(reader, [])
    index = {name.strip().lower(): i for i, name in enumerate(header)}
    missing = [c for c in _REQUIRED_COLUMNS if c not in index]
    if missing:
        raise InvalidCsvError(f"CSV is missing required column(s): {', '.join(missing)}")

    fi, li, ei = index["first_name"], index["last_name"], index["email"]
    rows: list[ParsedRow] = []
    seen: set[str] = set()
    line_number = 1  # header consumed above
    for record in reader:
        line_number += 1
        cells = [c.strip() for c in record]
        if not any(cells):
            continue  # blank line (e.g. trailing newline)
        first = cells[fi] if fi < len(cells) else ""
        last = cells[li] if li < len(cells) else ""
        email = (cells[ei] if ei < len(cells) else "").lower()

        error: str | None = None
        if not first or not last:
            error = "missing first or last name"
        elif not _EMAIL_RE.match(email):
            error = "malformed email"
        elif email in seen:
            error = "duplicate in file"
        else:
            seen.add(email)

        rows.append(ParsedRow(line_number, first, last, email, error))
        if len(rows) > MAX_INVITE_ROWS:
            raise InvalidCsvError(
                f"The CSV has more than {MAX_INVITE_ROWS} rows — split it into smaller files."
            )

    if not rows:
        raise InvalidCsvError("The CSV has a header but no data rows.")
    return rows


def build_preview(parsed: list[ParsedRow], existing_emails: set[str]) -> list[PreviewRow]:
    """Parser errors → 'invalid'; emails already in the system → 'duplicate';
    everything else → 'valid'. Pure — the router creates nothing here."""
    preview: list[PreviewRow] = []
    for r in parsed:
        if r.error is not None:
            preview.append(
                PreviewRow(r.row_number, r.first_name, r.last_name, r.email, "invalid", r.error)
            )
        elif r.email in existing_emails:
            preview.append(
                PreviewRow(
                    r.row_number,
                    r.first_name,
                    r.last_name,
                    r.email,
                    "duplicate",
                    "already registered",
                )
            )
        else:
            preview.append(
                PreviewRow(r.row_number, r.first_name, r.last_name, r.email, "valid", None)
            )
    return preview
