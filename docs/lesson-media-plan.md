# Embedded Images & Videos in Lessons — Implementation Plan

Status: PLANNED (approved plan, not started) — 2026-07-10

## Context

Lessons currently support text/quiz/interactive blocks only — no media. This plan adds embedded
images and videos to lesson content. Decisions made with Matthias (2026-07-10):

- **Images:** uploaded to Azure Blob Storage via a new admin-only endpoint.
- **Videos:** BOTH third-party embeds (YouTube / MS Stream / Vimeo → iframe) AND uploaded files
  (mp4/webm → `<video>`).
- **Access model:** PRIVATE blob container + read-only SAS URLs. `content_blocks` persist only
  `blob_path`; the backend stamps a fresh `url` into responses at read time. Account-key SAS from
  a `STORAGE__CONNECTION_STRING` setting (mirrors the `EMAIL__*` optional-config pattern).
  SAS chosen over a backend proxy because video seeking needs HTTP Range support (blob storage
  does it natively) and the single-replica Container App shouldn't relay video bandwidth.
- **Rights verified:** Matthias is Owner on RG `imaginemore-playground`; Microsoft.Storage
  registered; no restricting policies. No IT dependency.

Why this is cheap: `Lesson.content_blocks` is pass-through JSONB
(`backend/src/db/models/learning.py:123-125`, `schemas/admin_content.py:91`) — **no DB migration**.
The frontend block system is compile-enforced (union + RENDERERS/EDITORS/FACTORIES/blocksToMdx
maps), so adding types produces a compiler checklist.

**Hosting-move note:** IT will eventually move the app off the playground. Storing only relative
`blob_path` + a swappable connection string means the future move is: new storage account, copy
blobs (`azcopy`), swap the secret. No content rewrite.

## Critical correctness invariant

`GET /api/lessons/{id}` responses carry stamped `url` fields, and the admin editor PATCHes the
same block objects back verbatim (`LessonEditor.tsx:103-106`). **Server-side strip on write is
mandatory** or SAS URLs leak into JSONB: in `ContentService.update_lesson`
(`backend/src/services/content_service.py:97-101`), pass `content_blocks` through
`strip_ephemeral()` before the repo call. Stamping must be response-only (copy blocks, never
mutate the ORM attribute).

Ephemeral-`url` rules: `image` blocks and `video` blocks with `source:'blob'` get `url` stamped
at read / stripped at write. A `video` with `source:'embed'` has `url` as its PERSISTED
author-entered value — never strip it.

## 1. Azure provisioning — ASK MATTHIAS FIRST (standing rule)

Storage account `aienablementhubmedia`, RG `imaginemore-playground`, Sweden Central,
Standard_LRS, `--allow-blob-public-access false`; private container `lesson-media`.
Use the old az CLI (`C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd`):

```powershell
& $az storage account create --name aienablementhubmedia --resource-group imaginemore-playground `
    --location swedencentral --sku Standard_LRS --kind StorageV2 `
    --min-tls-version TLS1_2 --allow-blob-public-access false
$conn = & $az storage account show-connection-string --name aienablementhubmedia `
    --resource-group imaginemore-playground --query connectionString -o tsv
& $az storage container create --name lesson-media --connection-string $conn
```

Connection string → `backend/.env` (`STORAGE__CONNECTION_STRING=...`). No storage CORS needed
(uploads proxied through backend; `<img>`/`<video>` SAS loads aren't CORS-gated).

**Conscious punts (decided 2026-07-10):**
- **Orphaned blobs:** deleting a block / abandoning an edit leaves its blob forever. Accepted —
  admin-only uploads, Standard_LRS pennies. Future cleanup = script that diffs container blob
  names against `blob_path` values in lesson JSONB; don't build now.
- **Account-key SAS:** long-lived credential, accepted for the playground (mirrors `EMAIL__*`
  secret pattern, keeps the hosting move a secret-swap). Rotating the storage key invalidates
  the conn string → one `containerapp secret set` + revision restart. The eventual IT move to a
  permanent environment is the natural point to switch to managed identity + user-delegation SAS.

## 2. Block shapes (frontend/src/types/contentBlocks.ts)

One `video` type with a `source` discriminator (precedent: `interactive.mode`) — one entry per
compile-enforced map, embed↔upload is an editor toggle.

```ts
export type ImageBlock = {
  id: string; type: 'image'
  blob_path: string          // ONLY persisted locator, e.g. "images/6f0c….png"
  alt: string; caption?: string
  width?: number             // % of content column, 25–100; absent = 100
  url?: string               // EPHEMERAL — backend-stamped SAS, stripped on write
}
export type VideoBlock = { id: string; type: 'video'; caption?: string } & (
  | { source: 'embed'; url: string }                     // persisted embed URL
  | { source: 'blob'; blob_path: string; url?: string }  // url EPHEMERAL
)
```

## 3. Backend (follow python-be-architecture.md layering)

- **Deps** (`backend/pyproject.toml`): `azure-storage-blob~=12.24`, `python-multipart~=0.0.20`.
  Run `uv sync` so `uv.lock` updates (Docker build is `--frozen`).
- **Config** `src/core/configs/storage.py` (new, mirror `email.py`): `StorageSettings` —
  `connection_string: SecretStr`, `container: str = "lesson-media"`, `sas_ttl_hours: int = 48`;
  parse account_name/account_key/blob_endpoint once (fail startup loudly on bad string).
  Compose `storage: StorageSettings | None = None` in `settings.py`.
- **Pure helpers** `src/services/media_blocks.py` (new; precedent `email_templates.py`):
  `strip_ephemeral(blocks)` and `stamp_urls(blocks, url_for)` — both return NEW lists, copy
  stampable block dicts, tolerate unknown/malformed blocks.
- **Service** `src/services/media_service.py` (new): `BlobUploader` Protocol seam (mirror
  `EmailSender`). Validation: images `{png,jpeg,webp,gif}` max 10 MiB (NO svg — script-bearing);
  video `{mp4,webm}` max 300 MiB. Blob name `{kind}s/{uuid4().hex}{ext}` (ext from content-type
  map, never client filename). Upload via sync BlobClient in `run_in_threadpool`,
  `overwrite=False`, `ContentSettings(content_type=…)`. `sas_url(blob_path)`: read-only SAS with
  a QUANTIZED validity window so URLs are stable and browser-cacheable within a window (a
  `start = now−15min` design yields a byte-different signature per request — images re-download
  on every lesson visit and a 300 MB video never caches): start = most recent midnight UTC,
  expiry = start + 48 h (default `sas_ttl_hours: int = 48`, min 25 so a fetch just before
  midnight stays valid ≥ 24 h; clock skew covered because start is always in the past). Same
  security posture, one signature per blob per day. New `UnsupportedMediaTypeError` /
  `PayloadTooLargeError` in `services/exceptions.py` → 415/413 handlers + `_ERROR_CODES` entries
  in `main.py`.
- **DI** `src/core/dependencies/storage.py` (new): `get_media_service → MediaService | None`
  (email pattern; `@lru_cache`d BlobServiceClient) + `require_media_service` → 404 when
  unconfigured (Entra pattern). Runtime imports (FastAPI deferred-annotation gotcha).
- **Upload endpoint** `src/routers/admin_media.py` + `schemas/admin_media.py` (new):
  `POST /api/admin/media` (multipart field `file`, `Depends(require_admin)`), 201 →
  `{blob_path, url, content_type, size_bytes}`. Content-Length precheck in router (fast 413)
  + authoritative spooled-size check in service. Register router in `main.py`; add to the
  authz-matrix tests (with media configured via DI override).
- **Stamp on read:** `routers/learning.py::get_lesson` (line ~51) — optional
  `get_media_service` dep; after `lesson_detail(...)`, replace `payload["content_blocks"]`
  with `media.stamp_blocks(...)` when media is configured. Also stamp the
  `PATCH /api/admin/lessons/{id}` response in `routers/admin_content.py` for contract
  consistency. Stamping lives in routers (response mapping) — no service→service import.
- **Strip on write:** `ContentService.update_lesson` — the linchpin (see invariant above).
  Covers both block-editor and MDX save paths.
- **CSP** (`main.py:117-122`): build from settings — append blob endpoint to `img-src`; add
  `media-src 'self' {blob_endpoint}`; add `frame-src https://www.youtube-nocookie.com
  https://player.vimeo.com https://*.sharepoint.com` (always — embeds don't need storage).
  Tighten sharepoint to the delaware tenant host once a real Stream embed URL confirms it.
- **Tests** (≥80% rule; 865 currently green): `tests/fixtures/media.py` (stub uploader +
  fake-but-valid connection string — SAS gen is offline HMAC); strip/stamp matrix incl.
  embed-url-untouched + no-input-mutation; upload 415/413/happy; authz rows; integration:
  GET stamps + DB row stays clean, PATCH with url-bearing blocks → JSONB has no `url`;
  storage-unset behavior (upload 404, GET passes through). Pin `storage=None` in
  `test_settings` (same hermeticity as `email=None`).

## 4. Frontend

- **Types/factories:** union members (§2); `BLOCK_TYPES/BLOCK_LABELS/BLOCK_FACTORIES` in
  `lib/contentBlocks.ts` (`createImage`, `createVideo` defaulting `{source:'embed', url:''}`);
  TYPE_ORDER in `LessonEditor.tsx`. Compiler flags every remaining touch-point.
- **Embed normalization** `lib/videoEmbeds.ts` (new): `normalizeEmbedUrl(input)` — accepts bare
  URL or pasted `<iframe>` snippet; YouTube watch/youtu.be/shorts/embed →
  `youtube-nocookie.com/embed/{id}`; Vimeo → `player.vimeo.com/video/{id}`; Stream/SharePoint
  `*.sharepoint.com/...embed.aspx` as-is; else `null`. Allowlist mirrors CSP `frame-src` exactly.
- **Upload helper** `api/upload.ts` (new): XHR-based (fetch can't report upload progress) —
  FormData POST to `/api/admin/media`, Bearer from `api/tokens.ts`, on 401 await the exported
  single-flight `refreshAccessToken()` (`api/client.ts:32`) and retry once.
- **Renderers** (`components/lesson/blocks/`): `ImageBlock.tsx` — `<figure>`/`<img>` with
  skeleton until `onLoad`, placeholder when `url` absent/error, `width` %; `VideoBlock.tsx` —
  embed: 16:9 `aspectRatio` wrapper + iframe (`allowFullScreen`, re-normalize defensively);
  blob: `<video controls preload="metadata">`. Register in `LessonView.tsx` RENDERERS.
- **Editors** (`components/lesson/editors/`): `ImageEditor.tsx` — file picker → upload w/
  progress bar → `onChange({...block, blob_path, url})` (response url = instant live preview);
  alt/caption/width inputs. `VideoEditor.tsx` — Embed/Upload toggle (InteractiveEditor mode-switch
  pattern); embed: URL paste + live normalize validation; upload: picker + progress (matters at
  300 MB). Register in EDITORS.
- **MDX round-trip:** `blocksToMdx.ts` exhaustive switch → `<Image data="{base64}"/>` /
  `<Video data="{base64}"/>` (Interactive `encodeBlock` precedent), **strip ephemeral url before
  encoding**; `mdxParser.ts` split regex + decode branches.
- **Schema regen:** `npm run gen:api` against a locally running backend (touches the real dev DB
  on startup — flag first, per 2026-07-07 precedent). Checks: `npm run typecheck && npm run lint
  && npm run build`; backend `uv run poe format && uv run poe lint && uv run poe test`.

## 5. Size limits / ingress

App-level limits are the only limits (Container Apps ingress has no documented body cap; the
4 MB figure is Dapr-only, unused). 10 MiB image / 300 MiB video. Starlette spools >1 MB to disk
so 1 Gi RAM is safe; 0.5 vCPU single replica is fine for admin-only uploads. **Unverified:**
real ingress behavior at ~300 MB → prod verification step. Fallback if it fails: direct-to-blob
write SAS + storage CORS (don't build pre-emptively).

## 6. Deploy wiring — Azure steps ASK FIRST

1. `backend/.env` + `.env.local.example`: `STORAGE__CONNECTION_STRING` (+ optional
   `STORAGE__CONTAINER`, `STORAGE__SAS_TTL_HOURS`).
2. Live app (safe pre-deploy — running image ignores unknown env, ACS precedent):
   `az containerapp secret set … storage-connection-string=…` then
   `az containerapp update … --set-env-vars STORAGE__CONNECTION_STRING=secretref:storage-connection-string`.
3. DR parity: `infra/containerapp.yaml` placeholder + `infra/deploy-initial.ps1` fill (keep yaml
   pure ASCII).
4. Ship via `.\deploy.ps1` (ask first).

## 7. Verification

Local (real conn string in `.env`): upload PNG via ImageEditor → progress → SAS preview
(`sig`/`se` in network tab) → save → **prove DB clean** by commenting out STORAGE__ and
re-fetching (blocks have `blob_path`, no `url`, placeholder renders). YouTube/Vimeo/Stream embed
paste → normalize → save → plays. 50 MB mp4 → seeking works (Range+SAS). Oversize → 413, .txt →
415. MDX round-trip → DB still clean. **CSP is invisible in dev (Vite serves without headers)** —
embeds/media MUST be re-checked on prod. Prod: extended CSP in response headers; image + embed +
uploaded video render live; ~100-300 MB upload through real ingress; non-admin → 403 on upload;
clean up scratch lesson.

## 8. Order & effort (~2-3 focused days)

A provisioning (ask-first, 15 min) → B1 config/DI (1-2 h) → B2 service+router+tests (3-4 h) →
B3 stamp/strip+tests (2-3 h) → B4 CSP (1 h) ∥ C1 types+regen (1-2 h) → C2 renderers+embeds lib
(3 h) ∥ C3 upload helper+editors (3-4 h) ∥ C4 MDX (1-2 h) → D deploy wiring (ask-first, 1 h) →
E verification (2 h). The embed-video slice (C1/C2/C4 + frame-src) needs no storage and could
ship alone if provisioning stalls.

## Key files

- `backend/src/services/content_service.py` — strip on write (correctness linchpin)
- `backend/src/routers/learning.py` — SAS stamping on the lesson read aggregate
- `backend/src/main.py` — CSP, error codes, router registration
- `frontend/src/types/contentBlocks.ts` — block shapes; every map keys off this
- `frontend/src/components/lesson/LessonEditor.tsx` — EDITORS, TYPE_ORDER, upload entry
- Patterns to copy: `core/configs/email.py`, `core/dependencies/entra.py`,
  `services/email_service.py` (threadpool+Protocol), `tests/fixtures/email.py`
