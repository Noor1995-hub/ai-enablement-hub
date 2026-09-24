# State log, 2026 — moved out of CLAUDE.md on 2026-09-24

Historical. These are the dated "current state" notes that used to open the root `CLAUDE.md`,
kept verbatim for the record. **Do not treat any of it as current** — ask the live system
(`/api/health` → `build_sha`, `cd backend && uv run alembic current`) and read `CLAUDE.md`.
From 2026-09-24 the backlog lives in GitHub Issues and each change's record is its PR.

## Deploy notes before CI deploys (as of 2026-09-17)

Historical only: image `ai-enablement-hub:20260917-085533`, revision `--0000038`, `main` @ `87a81a7`
(pre-rewrite SHA `8da7f12` for the `1b7546a`-era note this superseded — **git history was
rewritten 2026-08-10 to purge learner PII**, so SHAs in older notes/transcripts don't resolve;
the pre-rewrite mirror lives in `..\_archive\ai-hub-pre-purge-mirror-2026-08-10.git`). `main` ==
deployed as of this note, no known undeployed behavior changes. The two most recent deploys
both fix admin-panel bugs found while trying to delete a user through the People screen:
`1ea39a3` adds `GET /admin/users/{user_id}` — the People detail page used to resolve its
participant by scanning page 1 (50 users, unfiltered) of the same paginated list PeoplePage
shows, so anyone past the first page 404'd as "could not be found" and was unreachable for
edit/delete/role changes (SAP SCM alone had ~68 unreachable users); `87a81a7` adds the missing
`multiplier` entry to the admin Maturity badge palette, which was keyed on only the 3
scoring-engine-assignable levels and silently rendered a blank cell for anyone whose
`effective_maturity` resolved to `multiplier`.

Recovering what a pre-CI deploy shipped: compare the image tag's timestamp with
`git log --format=%ci`. Pre-CI images carry timestamp tags, not SHAs, so rolling back to one needs
`az containerapp update -n ai-enablement-hub -g imaginemore-playground --image
ca530fc7463eacr.azurecr.io/ai-enablement-hub:<timestamp tag>` (Azure-mutating — ask first).

## Way of working, Tier 0 (2026-09-22)

Tier 0 guardrails shipped as PR #1 (squash `dfa936f`) — protected `main` (rulesets `main-ci`
23822345 + `main-review` 23822348 applied 2026-09-22), `CI` workflow (backend job ≈ 2.5 min on a
`postgres:18` service container, frontend ≈ 40 s), PR template, `CONTRIBUTING.md`, committed
`.claude/settings.json` hooks, the interim deploy guard (script since retired to
`infra/deploy-legacy.ps1` by the Tier 1 CI deploy, 2026-09-22). Direct pushes to `main` are
rejected for everyone (probe-verified).

## Way of working, Tier 1 CI deploy (2026-09-23)

Tier 1 CI deploy live (PR #4 `a0b35d8`, fixes #5/#6). **First CI deploy 2026-09-23, run
`35854398270`, sha `7cd9cab`, revision `--0000039`** — build 58 s, migration job 88 s
(`Succeeded` at 11:27:49, before the revision at 11:28:05), roll 16 s, health poll 39 s;
container log shows uvicorn only, no Alembic. Rollback drill (run `35855219249`) skipped build
**and** migration, rolled to `--0000040`, same `build_sha`, fresh `build_time`. Two traps found
by running it, both fixed: a PowerShell case-insensitive `$job`/`$JOB` collision blanked the job
name, and GitHub now presents the **immutable** OIDC subject
(`repo:<org>@<orgId>/<repo>@<repoId>:ref:...`) so the identity carries both subject forms —
**`bta-portal-cicd` has only the plain form and will hit the same failure; tell Michael.**

## Tier 1 status and the first Tier 2 deploy (2026-09-24)

1.1–1.4 and 1.6–1.9 done (PRs #4–#16); 1.5 (dev database) cancelled by decision. Prompts
git-only (#16) deployed 2026-09-24 together with the first Tier 2 batch (#18–#38: anthropic 1.x,
bcrypt 5, coverage floor, `ty` on `src/`) — Deploy run `35990005311` built `main` @ `f483cc1`;
verified live — login, an AI call, read-only prompts page (`PUT` → 405). The same day #39–#41
(staged ratchet, SHA-pinned actions, docs-drift test) deployed as `2b9ab05`.

## Other facts dropped from CLAUDE.md on 2026-09-24

- Pending work queue note: the July review's fix programme was "unexecuted as of 2026-08-10";
  it is now tracked as issues #52–#56.
- The custom-domain recipe (DNS CNAME + TXT `asuid`, `az containerapp hostname add`/`bind`,
  `APP__URL` update) lives in the git history of `CLAUDE.md` @ `516e40c`, "Open for cutover".
