# Branch rulesets for `main`

These two files are the source of truth for how `main` is protected. Apply or re-apply them
with the GitHub CLI (repo admin required). They mirror the delaware house pattern
(`bta-agents-portal`, `sb-accelerator`).

| File | What it enforces | Bypass |
|---|---|---|
| `main-ci.json` | changes reach `main` only via a pull request; the two `CI` checks `backend (format + lint + tests)` and `frontend (typecheck + lint + build)` must be green; squash merge only; no force-push, no deletion | **nobody** — admins included |
| `main-review.json` | one approving review | repository admins |

## Apply (first time)

```bash
gh api repos/DLW-INT-BTA-BELUX/ai-enablement-hub/rulesets -X POST --input .github/rulesets/main-ci.json
gh api repos/DLW-INT-BTA-BELUX/ai-enablement-hub/rulesets -X POST --input .github/rulesets/main-review.json
```

## Update an existing ruleset

```bash
gh api repos/DLW-INT-BTA-BELUX/ai-enablement-hub/rulesets --jq '.[] | "\(.id) \(.name)"'
gh api repos/DLW-INT-BTA-BELUX/ai-enablement-hub/rulesets/<id> -X PUT --input .github/rulesets/<name>.json
```

## Verify

```bash
gh api repos/DLW-INT-BTA-BELUX/ai-enablement-hub/rulesets --jq '.[] | "\(.name) \(.enforcement)"'
```

**If you rename a CI job** in `.github/workflows/ci.yml`, update the `context` strings in
`main-ci.json` in the same PR and re-apply with `PUT` right after merging — otherwise every
merge is blocked waiting for a check that no longer exists.

## Repository merge settings (apply once, alongside the rulesets)

```bash
gh api -X PATCH repos/DLW-INT-BTA-BELUX/ai-enablement-hub -F allow_squash_merge=true -F allow_merge_commit=false -F allow_rebase_merge=false -F delete_branch_on_merge=true -F squash_merge_commit_title=PR_TITLE -F squash_merge_commit_message=PR_BODY
```

Squash-only and auto-delete of merged branches are repository settings, not ruleset rules; CONTRIBUTING.md describes their effect.
