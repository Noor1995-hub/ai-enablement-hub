# Interviewer eval

Turns the frozen test set into playbooks through the real hub code (`InterviewService`,
`ChatService`, `InterviewContextService`, `AnthropicLlmClient`) and grades them with
checks that make no model call. Design: `docs/superpowers/specs/2026-09-27-interviewer-eval-tranche-2-design.md`.
Plain-language walkthrough: `docs/guides/interviewer-evals-learning-guide.md`.

## Running

All commands run from `backend/`:

```bash
export UV_PROJECT_ENVIRONMENT="C:/Users/neuvillea/.venvs/ai-hub-backend"
uv run --extra dev python -m evals.interviewer <command>
```

The key lives in `backend/.env` (git-ignored, never commit it):

```
LLM__PROVIDER=anthropic
LLM__MODEL=claude-sonnet-5
LLM__API_KEY=...
```

| Command | Does | Needs a key? |
|---|---|---|
| `simulate --case <id> [--force]` | Runs one interview: the real interviewer against a persona. Writes `cases/<id>.json` (`status: draft`) and `review/<id>.md`. | Yes |
| `simulate --variant <name> [--cases a,b] [--reps 1] [--max-usd 10] [--hard-stop]` | Runs the same interview loop as `simulate --case`, once per (case, rep), over every case on disk (or just `--cases`) - but writes each result to `runs/<name>/sims/<case>_rep<k>.json` and never touches `cases/` or `review/`. For iterating on the prompt/chat behaviour without disturbing the frozen, reviewed set. `--hard-stop` ends each interviewer chat turn at its first question, the way `LLM__INTERVIEW_HARD_STOP=true` does in the hub (#96); the opener is never cut, and each turn that really lost text is marked `"stopped": true` with the removed text in `"removed"`. Resumable (skips a `(case, rep)` file that already exists); bills every model call made during a simulation (interviewer and persona both) and stops starting new sims once the running total - including sims already on disk for this variant - reaches `--max-usd` (default 10.0 USD). | Yes |
| `review --case <id>` / `review --all` | Rewrites `review/<id>.md` (or every review page) straight from the case file(s) on disk - e.g. after hand-editing `ground_truth`. Makes no model call. | No |
| `approve --case <id>` | Marks a reviewed draft `approved`. Only approved cases are used by `run`. | No |
| `run --variant <baseline\|vN> [--reps 3] [--cases a,b] [--model <id>] [--max-usd 10]` | Turns approved cases into playbooks and grades them. Resumable; up to 4 attempts in flight; stops starting new work once billed spend reaches `--max-usd` (default 10.0 USD). This key lives in a shared workspace with no separate spend limit, so the default is not unlimited. | Yes |
| `report --variant <name>` | Builds `runs/report.html` (covers every variant directory present on disk). | No |
| `chat-report --variant <name>` | Writes `runs/<name>/chat.md`: the chat-level checks (`chat_checks.py` - do the interviewer's own turns write the person's reply for it, name an injected instruction out loud, stack questions, use dashes) computed over that variant's sims, next to the same checks computed over the frozen `cases/` transcripts ("frozen set (current prompt)"), plus every hard-check failure and self-answer suspect with its excerpt, and every turn the hard stop cut, with what it removed and the learner's next reply (read these: a cut that kept only a very short question such as "Really?" is marked SHORT QUESTION). Makes no model call. | No |
| `compare --variant <vN>` | Writes `runs/<vN>/compare.md`: per-check baseline vs. variant rate, with the noise margin. | No |
| `regrade --variant <name>` | Recomputes every check against each row's already-recorded trace (no model calls) and rewrites `results.jsonl` + each trace's evidence in place - use after tuning `checks.py`/`vocabulary.py` to re-score an existing run without re-spending. | No |

## Layout

```
cases/<id>.json          the frozen test set (committed)
review/<id>.md            generated review pages (committed)
runs/baseline/...         results, traces, errors, report for the baseline (committed)
runs/v*/                  later variants (git-ignored unless deliberately committed)
runs/<name>/sims/         `simulate --variant` output: one case-shaped file per (case, rep)
runs/<name>/chat.md       `chat-report --variant` output
runs/_state.json          metric declarations for the report builder
```

## Unit tests

`uv run --extra dev pytest tests/unit/evals -v` — no key, no spend, no network. These run
in the normal `poe test`.

## Safety

The key lives only in the local, git-ignored `backend/.env` (`LLM__*`). `simulate` and
`run` refuse to start without it and never log it. Nothing here touches the database or
any deployed service. Every case is invented; review pages are checked for real names
before a case is approved.
