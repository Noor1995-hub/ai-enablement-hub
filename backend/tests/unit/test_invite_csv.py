from __future__ import annotations

import pytest

from src.services.exceptions import InvalidCsvError
from src.services.invite_csv import (
    MAX_INVITE_ROWS,
    build_preview,
    parse_invite_csv,
)


def _b(text: str) -> bytes:
    return text.encode("utf-8")


class TestParse:
    def test_comma_happy_path_normalizes_email(self) -> None:
        rows = parse_invite_csv(_b("first_name,last_name,email\nJan,Peeters,Jan.Peeters@Acme.be\n"))
        assert len(rows) == 1
        r = rows[0]
        assert (r.first_name, r.last_name, r.email, r.error) == (
            "Jan",
            "Peeters",
            "jan.peeters@acme.be",
            None,
        )
        assert r.row_number == 2  # header is line 1

    def test_semicolon_delimiter(self) -> None:
        rows = parse_invite_csv(_b("first_name;last_name;email\nSofie;Maes;sofie@acme.be\n"))
        assert rows[0].error is None
        assert rows[0].email == "sofie@acme.be"

    def test_utf8_bom_is_stripped(self) -> None:
        raw = "﻿first_name,last_name,email\nAn,Van,an@acme.be\n".encode()
        rows = parse_invite_csv(raw)
        assert rows[0].first_name == "An"
        assert rows[0].error is None

    def test_headers_reordered_and_extra_columns_ignored(self) -> None:
        rows = parse_invite_csv(
            _b("email,department,last_name,first_name\na@b.co,Sales,Doe,Jane\n")
        )
        assert (rows[0].first_name, rows[0].last_name, rows[0].email) == ("Jane", "Doe", "a@b.co")

    def test_crlf_and_quoted_name_with_comma(self) -> None:
        rows = parse_invite_csv(b'first_name,last_name,email\r\n"De, Jan",Peeters,jan@acme.be\r\n')
        assert rows[0].first_name == "De, Jan"
        assert rows[0].error is None

    def test_blank_name_is_invalid(self) -> None:
        rows = parse_invite_csv(_b("first_name,last_name,email\n,Peeters,jan@acme.be\n"))
        assert rows[0].error == "missing first or last name"

    def test_malformed_email_is_invalid(self) -> None:
        rows = parse_invite_csv(_b("first_name,last_name,email\nJan,Peeters,not-an-email\n"))
        assert rows[0].error == "malformed email"

    def test_in_file_duplicate_flagged_case_insensitively(self) -> None:
        rows = parse_invite_csv(
            _b("first_name,last_name,email\nA,B,dup@acme.be\nC,D,DUP@acme.be\n")
        )
        assert rows[0].error is None
        assert rows[1].error == "duplicate in file"

    def test_fully_blank_rows_skipped(self) -> None:
        rows = parse_invite_csv(_b("first_name,last_name,email\nJan,Peeters,jan@acme.be\n,,\n"))
        assert len(rows) == 1

    def test_missing_required_column_raises(self) -> None:
        with pytest.raises(InvalidCsvError):
            parse_invite_csv(_b("first_name,email\nJan,jan@acme.be\n"))

    def test_empty_file_raises(self) -> None:
        with pytest.raises(InvalidCsvError):
            parse_invite_csv(b"")

    def test_header_only_raises(self) -> None:
        with pytest.raises(InvalidCsvError):
            parse_invite_csv(_b("first_name,last_name,email\n"))

    def test_too_many_rows_raises(self) -> None:
        body = "first_name,last_name,email\n" + "".join(
            f"F{i},L{i},user{i}@acme.be\n" for i in range(MAX_INVITE_ROWS + 1)
        )
        with pytest.raises(InvalidCsvError):
            parse_invite_csv(_b(body))

    def test_undecodable_bytes_raise(self) -> None:
        with pytest.raises(InvalidCsvError):
            parse_invite_csv(b"first_name,last_name,email\n\xff\xfe not utf8\n")

    def test_xlsx_workbook_gives_a_friendly_error(self) -> None:
        # An .xlsx is a ZIP archive (PK magic); the message must guide, not confuse.
        with pytest.raises(InvalidCsvError, match="Excel workbook"):
            parse_invite_csv(b"PK\x03\x04 fake xlsx bytes")


class TestBuildPreview:
    def test_categorizes_invalid_duplicate_valid(self) -> None:
        parsed = parse_invite_csv(
            _b(
                "first_name,last_name,email\n"
                "Jan,Peeters,jan@acme.be\n"
                "Sofie,Maes,sofie@acme.be\n"
                ",Bad,bad@acme.be\n"
            )
        )
        preview = build_preview(parsed, existing_emails={"sofie@acme.be"})
        by_email = {p.email: p.status for p in preview}
        assert by_email["jan@acme.be"] == "valid"
        assert by_email["sofie@acme.be"] == "duplicate"
        assert by_email["bad@acme.be"] == "invalid"
        dup = next(p for p in preview if p.email == "sofie@acme.be")
        assert dup.detail == "already registered"
