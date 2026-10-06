from __future__ import annotations

import pytest

from src.core.media_paths import media_path
from src.core.media_usage import blob_paths

HEX = "0123456789abcdef0123456789abcdef"


@pytest.mark.parametrize(
    ("kind", "name", "expected"),
    [
        ("images", f"{HEX}.png", f"images/{HEX}.png"),
        ("videos", f"{HEX}.mp4", f"videos/{HEX}.mp4"),
        ("docs", f"{HEX}.png", None),
        ("images", "../secret.png", None),
        ("images", f"{HEX}.PNG", None),
        ("images", f"{HEX[:-1]}.png", None),
        ("images", f"{HEX}.png/x", None),
    ],
)
def test_media_path_accepts_only_upload_shaped_names(
    kind: str, name: str, expected: str | None
) -> None:
    assert media_path(kind, name) == expected


def test_blob_paths_finds_images_and_blob_videos_only() -> None:
    blocks = [
        {"id": "i", "type": "image", "blob_path": "images/a.png", "alt": "x"},
        {"id": "e", "type": "image", "blob_path": "", "alt": "placeholder"},
        {"id": "v", "type": "video", "source": "blob", "blob_path": "videos/b.mp4"},
        {"id": "y", "type": "video", "source": "embed", "url": "https://youtube.com/embed/x"},
        {"id": "p", "type": "paragraph", "text": "images/c.png in prose is not a reference"},
        "garbage",
    ]
    assert blob_paths(blocks) == {"images/a.png", "videos/b.mp4"}
    assert blob_paths(None) == set()
