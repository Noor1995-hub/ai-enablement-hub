from __future__ import annotations

from starlette.requests import Request

from src.core.client_ip import client_ip


def _request(
    *headers: tuple[str, str], peer: tuple[str, int] | None = ("10.0.0.9", 51234)
) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(name.lower().encode(), value.encode()) for name, value in headers],
        "client": peer,
    }
    return Request(scope)


class TestClientIp:
    def test_forged_multi_hop_header_yields_the_hop_ingress_appended(self) -> None:
        """The client controls everything left of the last entry; ACA's Envoy
        appends the real peer on the right."""
        request = _request(("X-Forwarded-For", "203.0.113.77, 198.51.100.1, 192.0.2.44"))
        assert client_ip(request) == "192.0.2.44"

    def test_single_entry(self) -> None:
        assert client_ip(_request(("X-Forwarded-For", "192.0.2.44"))) == "192.0.2.44"

    def test_ipv6_entry_is_kept_verbatim(self) -> None:
        """Colons inside an entry are not split and nothing is normalised."""
        request = _request(("X-Forwarded-For", "203.0.113.77, 2001:db8::1"))
        assert client_ip(request) == "2001:db8::1"

    def test_whitespace_and_empty_segments_are_ignored(self) -> None:
        request = _request(("X-Forwarded-For", "  203.0.113.77 ,  192.0.2.44  , ,"))
        assert client_ip(request) == "192.0.2.44"

    def test_repeated_headers_are_read_as_one_list(self) -> None:
        """A client can send its own X-Forwarded-For line; the rightmost value
        across all lines is still the one ingress added."""
        request = _request(("X-Forwarded-For", "203.0.113.77"), ("X-Forwarded-For", "192.0.2.44"))
        assert client_ip(request) == "192.0.2.44"

    def test_empty_header_falls_back_to_the_peer(self) -> None:
        assert client_ip(_request(("X-Forwarded-For", " , "))) == "10.0.0.9"

    def test_no_header_falls_back_to_the_peer(self) -> None:
        assert client_ip(_request()) == "10.0.0.9"

    def test_no_header_and_no_peer_is_unknown(self) -> None:
        assert client_ip(_request(peer=None)) == "unknown"
