"""The one trustworthy client IP for per-IP rate-limit keys.

Why not `request.client.host`: `startup.py` runs uvicorn with `proxy_headers=True,
forwarded_allow_ips="*"`, and uvicorn then rewrites the peer to the LEFTMOST
X-Forwarded-For entry, which is whatever the client typed. Verified on production
2026-09-25: a request sent with `X-Forwarded-For: 203.0.113.77` was logged by uvicorn
as client 203.0.113.77, while normal requests log the real public IP. So Azure
Container Apps' Envoy ingress APPENDS the real peer to the header rather than
overwriting it. The rightmost entry is the only one the client cannot forge; keying on
anything else lets an attacker rotate the header to escape every per-IP limit, mint a
fresh limiter key per request, or send the delaware office NAT IP to lock the office
out on purpose.

`startup.py` is deliberately left alone: its proxy settings only decide what the
uvicorn access-log line shows (still spoofable there; don't trust that column for
forensics). Nothing security-relevant may read `request.client.host`.

Assumption this rests on: exactly ONE trusted hop (ACA ingress) sits in front of the
app. If a second trusted proxy is ever added (Front Door, App Gateway, an APIM in
front of ACA), the rightmost entry becomes THAT proxy's address, every learner shares
one key and a single limit locks everyone out. The fix then is to skip N trusted hops
from the right (take the entry N-from-the-end) — re-verify with a forged header first.
"""

from __future__ import annotations

from starlette.requests import Request

__all__ = ["client_ip"]


def client_ip(request: Request) -> str:
    """Rightmost non-empty X-Forwarded-For entry (the hop ACA ingress appended);
    falls back to the socket peer, then "unknown", when the header is absent."""
    # getlist: a client may send its own X-Forwarded-For line(s); read them all as
    # one list so the rightmost value is still the one ingress added.
    hops = [
        hop.strip()
        for line in request.headers.getlist("x-forwarded-for")
        for hop in line.split(",")
    ]
    # Entries are used verbatim, with no port stripping or IPv6 normalisation: the
    # rightmost entry is written by Envoy, which records the bare peer address with
    # no port (prod logs the plain public IP), and IPv6 stays one entry because we
    # split on commas only. If a hop ever appended `ip:port`, every ephemeral port
    # would become a fresh key and the limits would stop biting, so re-verify on
    # any ingress change.
    for hop in reversed(hops):
        if hop:
            return hop
    return request.client.host if request.client is not None else "unknown"
