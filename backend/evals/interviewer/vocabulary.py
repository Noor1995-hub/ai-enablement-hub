"""Word lists for the hard rules (spec §5.1). Editable in one place; every rule is
case-insensitive whole-word/phrase matching except the tier tokens (capitals only)."""

from __future__ import annotations

__all__ = [
    "GENDERED_PRONOUNS",
    "INTERNAL_TIER_TOKENS",
    "INTERNAL_WORDS",
    "NO_JUDGING_PHRASES",
    "POSSIBLE_SYSTEM_STOPWORDS",
    "VENDOR_WORDS",
]

_LEVEL_NAMES = ("practitioner", "integrator", "multiplier")
_EXPLORE_PHRASES = ("explore level", "explorer")
_MATURITY_WORDS = ("maturity", "your level", "your score")
_COMPARISON_PHRASES = (
    "most people",
    "a lot of people",
    "many people",
    "your peers",
    "than most",
    "ahead of most",
    "ahead of others",
    "ahead of your peers",
    "ahead of colleagues",
    "ahead of the curve",
    "ahead of the pack",
    "compared to others",
)
_CHARACTERISATION_PHRASES = (
    "you're sceptical",
    "you are sceptical",
    "skeptical",
    "reluctant",
    "resistant",
    "defensive",
)
_INPUT_QUALITY_PHRASES = (
    "you didn't share",
    "you did not share",
    "limited information",
    "not much detail",
)

# Known limit (recorded in the learning guide, spec §5.5): this misses paraphrases
# ("further along than colleagues") and can flag innocent text using a listed word in an
# unrelated sense ("the supplier was reluctant"). Every hit shows its evidence text so
# Aaron can tune this list at the pilot review.
# Tuned at the baseline review (2026-09-27): dropped the bare "other people" (too broad -
# it flagged ordinary statements about data affecting other people) and the bare "ahead
# of" (flagged plain scheduling language like "ahead of Friday"), replacing the latter
# with the specific comparison phrases below.
NO_JUDGING_PHRASES = (
    _LEVEL_NAMES
    + _EXPLORE_PHRASES
    + _MATURITY_WORDS
    + _COMPARISON_PHRASES
    + _CHARACTERISATION_PHRASES
    + _INPUT_QUALITY_PHRASES
)

# Tuned at the baseline review (2026-09-27): the bare "intake" flagged ordinary industry
# language ("intake data from call centre", "a single intake point for subcontractor
# quotes"), so it is replaced with the specific phrases that actually name the tool.
INTERNAL_WORDS = (
    "your intake",
    "the intake",
    "intake form",
    "intake answers",
    "intake questionnaire",
    "intake responses",
    "input quality",
    "input-quality",
    "maturity tier",
    "champion potential",
)
# Whole-word, capitals only: lowercase "rich"/"partial"/"thin" are plain English words used
# constantly in these industries ("a rich data set", "a partial shipment").
INTERNAL_TIER_TOKENS = ("RICH", "PARTIAL", "THIN")

GENDERED_PRONOUNS = ("he", "she", "him", "her", "his", "hers", "himself", "herself")

# `no_invented_systems` (checks.py) strips one of these off the front of a system name
# before comparing it to `ground_truth.named_systems`, so "Microsoft Excel" ~ "Excel" and
# "SAP S/4HANA" ~ "SAP" count as the same system rather than a hallucinated one. Longest
# first, so "microsoft 365 copilot" strips to "copilot" in one pass rather than "365
# copilot" (spec 2026-09-27 review, F2).
VENDOR_WORDS = ("microsoft 365", "microsoft", "ms", "sap", "google", "oracle")

# Known limit, `_phrase_pattern` (checks.py, own-words match for `no_invented_systems`):
# a system name only tolerates a trailing plural "s" on either side ("paper checklists" ~
# "paper checklist") when it is a multi-word phrase, or a single word whose singular form
# is 7+ letters. A short single word (e.g. "SAP", "Excel", "Teams") is matched exactly
# instead - tolerating its plural would let it be misread out of an unrelated longer word
# ("SAP" in "saps", "Excel" in "excels") or match its own bare singular ("Teams" in "my
# team"). Fixed 2026-09-27 (critical bug found in code review, day of the baseline
# tuning).

# `_possible_systems` (simulate.py) uses this to keep the "possible systems" review-page
# hint from drowning in ordinary capitalised words (pronouns, weekdays, months,
# greetings, common sentence words, Dutch function words). It is a noisy heuristic for a
# human, not a hard rule, so this list is deliberately small - it only needs to cut the
# obvious non-system hits, not every one.
POSSIBLE_SYSTEM_STOPWORDS = (
    # pronouns
    "i",
    "you",
    "he",
    "she",
    "we",
    "they",
    "it",
    "me",
    "him",
    "her",
    "us",
    "them",
    "his",
    "hers",
    "their",
    "our",
    "your",
    "my",
    # weekdays
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    # months
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    # greetings
    "hi",
    "hello",
    "hey",
    "thanks",
    "thank",
    # common sentence words
    "the",
    "a",
    "an",
    "and",
    "but",
    "so",
    "yeah",
    "yes",
    "no",
    "ok",
    "okay",
    "well",
    "honestly",
    "actually",
    "basically",
    "really",
    "just",
    "now",
    "then",
    "this",
    "that",
    "these",
    "those",
    "there",
    "here",
    "when",
    "what",
    "where",
    "why",
    "how",
    "if",
    "because",
    "since",
    "once",
    "alright",
    "sure",
    "right",
    # Dutch function words
    "ja",
    "nee",
    "dat",
    "het",
    "de",
    "een",
    "en",
    "maar",
    "dus",
    "ik",
)
