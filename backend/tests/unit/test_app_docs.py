"""Swagger/ReDoc/OpenAPI exposure is env-dependent. The app object is built once
at import time from the real environment, so this is tested through the pure
helper rather than by rebuilding the app (main.py deliberately avoids an app
factory / module reimport)."""

from __future__ import annotations

from src.main import _doc_urls


def test_prod_serves_no_api_documentation() -> None:
    assert _doc_urls("prod") == {"docs_url": None, "redoc_url": None, "openapi_url": None}


def test_dev_keeps_the_default_documentation_urls() -> None:
    assert _doc_urls("dev") == {
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json",
    }
