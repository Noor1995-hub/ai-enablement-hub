"""strip_ephemeral / stamp_urls: pure content_blocks transforms (no I/O).
Covers the image/video-blob/video-embed matrix, unknown/malformed passthrough,
and the no-input-mutation guarantee (AAA, no DB)."""

from __future__ import annotations

import copy
from typing import Any

from src.services.media_blocks import stamp_urls, strip_ephemeral

_IMAGE: dict[str, Any] = {
    "id": "b1",
    "type": "image",
    "blob_path": "images/abc.png",
    "alt": "A picture",
    "url": "https://example.blob.core.windows.net/lesson-media/images/abc.png?sig=x",
}
_VIDEO_BLOB: dict[str, Any] = {
    "id": "b2",
    "type": "video",
    "source": "blob",
    "blob_path": "videos/def.mp4",
    "url": "https://example.blob.core.windows.net/lesson-media/videos/def.mp4?sig=y",
}
_VIDEO_EMBED: dict[str, Any] = {
    "id": "b3",
    "type": "video",
    "source": "embed",
    "url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
}


class TestStripEphemeral:
    def test_strips_url_from_image_block(self) -> None:
        [result] = strip_ephemeral([_IMAGE])
        assert "url" not in result
        assert result["blob_path"] == "images/abc.png"

    def test_strips_url_from_blob_video_block(self) -> None:
        [result] = strip_ephemeral([_VIDEO_BLOB])
        assert "url" not in result
        assert result["blob_path"] == "videos/def.mp4"

    def test_never_touches_url_on_embed_video_block(self) -> None:
        [result] = strip_ephemeral([_VIDEO_EMBED])
        assert result["url"] == _VIDEO_EMBED["url"]

    def test_unknown_block_type_passes_through_unchanged(self) -> None:
        block = {"id": "b4", "type": "quiz", "question": "?"}
        [result] = strip_ephemeral([block])
        assert result == block

    def test_missing_type_key_passes_through_unchanged(self) -> None:
        block = {"id": "b5", "blob_path": "images/x.png", "url": "https://x"}
        [result] = strip_ephemeral([block])
        assert result == block

    def test_non_dict_entry_passes_through_unchanged(self) -> None:
        assert strip_ephemeral(["not-a-block", 42, None]) == ["not-a-block", 42, None]

    def test_image_without_url_key_is_untouched(self) -> None:
        block = {"id": "b6", "type": "image", "blob_path": "images/x.png", "alt": "x"}
        [result] = strip_ephemeral([block])
        assert result == block

    def test_returns_new_list_and_does_not_mutate_input(self) -> None:
        original = [copy.deepcopy(_IMAGE), copy.deepcopy(_VIDEO_BLOB), copy.deepcopy(_VIDEO_EMBED)]
        snapshot = copy.deepcopy(original)

        result = strip_ephemeral(original)

        assert result is not original
        assert original == snapshot
        assert "url" not in result[0]

    def test_mixed_batch_only_strips_the_expected_entries(self) -> None:
        results = strip_ephemeral([_IMAGE, _VIDEO_BLOB, _VIDEO_EMBED])
        assert "url" not in results[0]
        assert "url" not in results[1]
        assert results[2]["url"] == _VIDEO_EMBED["url"]


class TestStampUrls:
    def test_stamps_url_on_image_with_blob_path(self) -> None:
        block = {"id": "b1", "type": "image", "blob_path": "images/abc.png", "alt": "A picture"}
        [result] = stamp_urls([block], lambda path: f"https://cdn.test/{path}?sig=fresh")
        assert result["url"] == "https://cdn.test/images/abc.png?sig=fresh"

    def test_stamps_url_on_blob_video_with_blob_path(self) -> None:
        block = {"id": "b2", "type": "video", "source": "blob", "blob_path": "videos/def.mp4"}
        [result] = stamp_urls([block], lambda path: f"https://cdn.test/{path}?sig=fresh")
        assert result["url"] == "https://cdn.test/videos/def.mp4?sig=fresh"

    def test_skips_embed_video_even_with_url_present(self) -> None:
        [result] = stamp_urls([_VIDEO_EMBED], lambda path: "SHOULD_NOT_BE_CALLED")
        assert result["url"] == _VIDEO_EMBED["url"]

    def test_skips_block_without_blob_path(self) -> None:
        block = {"id": "b7", "type": "image", "alt": "no path yet"}
        [result] = stamp_urls([block], lambda path: "SHOULD_NOT_BE_CALLED")
        assert "url" not in result

    def test_skips_video_blob_without_blob_path(self) -> None:
        block = {"id": "b8", "type": "video", "source": "blob"}
        [result] = stamp_urls([block], lambda path: "SHOULD_NOT_BE_CALLED")
        assert "url" not in result

    def test_unknown_block_type_passes_through_unchanged(self) -> None:
        block = {"id": "b9", "type": "quiz", "question": "?"}
        [result] = stamp_urls([block], lambda path: "SHOULD_NOT_BE_CALLED")
        assert result == block

    def test_non_dict_entry_passes_through_unchanged(self) -> None:
        assert stamp_urls(["not-a-block", None], lambda path: "x") == ["not-a-block", None]

    def test_missing_type_key_passes_through_unchanged(self) -> None:
        block = {"id": "b10", "blob_path": "images/x.png"}
        [result] = stamp_urls([block], lambda path: "SHOULD_NOT_BE_CALLED")
        assert result == block

    def test_returns_new_list_and_does_not_mutate_input(self) -> None:
        block = {"id": "b1", "type": "image", "blob_path": "images/abc.png"}
        original = [block]
        snapshot = copy.deepcopy(original)

        result = stamp_urls(original, lambda path: "https://cdn.test/fresh")

        assert result is not original
        assert original == snapshot
        assert "url" not in block
        assert result[0]["url"] == "https://cdn.test/fresh"

    def test_calls_url_for_with_the_blob_path(self) -> None:
        seen: list[str] = []

        def url_for(path: str) -> str:
            seen.append(path)
            return f"https://cdn.test/{path}"

        stamp_urls(
            [{"id": "b1", "type": "image", "blob_path": "images/abc.png"}],
            url_for,
        )
        assert seen == ["images/abc.png"]
