from __future__ import annotations

import re

from src.services.interview_marker import READY_MARKER

__all__ = ["QuestionCut"]

# A paragraph break: two line breaks, with nothing but spaces or tabs between them.
_PARAGRAPH_BREAK_RE = re.compile(r"\n[ \t]*\n")


class QuestionCut:
    """The interviewer's hard stop (#96): shows a streamed turn up to the first question
    that ends a paragraph, and removes everything after it when real text follows.

    Done in our code, not with an API stop sequence, because Sonnet 5 writes "?\\n\\n"
    just before it ends almost every turn: an API stop fires on every turn and can't tell
    a real cut apart from a normal ending (v5 eval, 29 Sept). Here a blank line at the
    very end is not a cut, and `removed` holds exactly what the learner was spared.

    Feed it the streamed chunks in order, show what `feed` returns, then show what
    `finish` returns. Whitespace right after a "?" is held back until the next real
    character shows whether a new paragraph starts. A question mark inside a sentence
    or a single line break never cuts. A build marker on its own after the question (the
    pre-#96 offer shape) is kept, so the Build button still appears; a marker that comes
    after removed text is dropped with it, because the learner never saw that offer.
    """

    def __init__(self) -> None:
        self._held = ""
        self._after_question = False
        self._cutting = False
        self._removed: list[str] = []
        self.cut = False

    @property
    def removed(self) -> str:
        return "".join(self._removed)

    def feed(self, chunk: str) -> str:
        if self._cutting:
            self._removed.append(chunk)
            return ""
        out: list[str] = []
        for i, ch in enumerate(chunk):
            if self._after_question and ch.isspace():
                self._held += ch
                continue
            if self._after_question and _PARAGRAPH_BREAK_RE.search(self._held):
                self._cutting = True
                self._removed.append(self._held + chunk[i:])
                self._held = ""
                return "".join(out)
            out.append(self._held + ch)
            self._held = ""
            self._after_question = ch == "?"
        return "".join(out)

    def finish(self) -> str:
        """Call once the stream is done. Returns the last text to show (the build marker,
        when it was all that followed the question) and settles `cut`: True only when
        real text, not just the marker, was removed."""
        self._held = ""  # trailing whitespace after the final question: never shown
        if not self._cutting:
            return ""
        removed = self.removed
        self.cut = bool(removed.replace(READY_MARKER, "").strip())
        return f"\n{READY_MARKER}" if not self.cut and READY_MARKER in removed else ""
