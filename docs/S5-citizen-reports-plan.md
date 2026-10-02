# S5 — Citizen reports and gamification: implementation plan

Status: phase 1 built (branch `S5-p1-foundation`), waiting on a Neon project for the first real end-to-end check. This file is the plan; CHECKPOINT.md tracks progress.

## Goal

Let citizens report what they see at a stream (checklist, note, optional photo), earn points and badges for useful contributions, and see how they compare. Reports enrich the map; they **never change the model's scores** and are always shown as unverified.

Covers hackathon Tracks 1 (citizen UX), 3 (AI with a human in the loop), 5 (community and gamification), and 7 (each report is exported as FHIR).

## Decisions taken (override any of these)

| # | Decision | Why |
|---|---|---|
| 1 | Storage: **Neon Postgres** (free plan: 0.5 GB, scale-to-zero) | Render's disk is wiped on redeploy; Neon is one free hosted database |
| 2 | Sign-in: **Neon Auth** (managed Better Auth): email + password and Google | Users live in our own database; tokens are EdDSA JWTs our API verifies with a public key list |
| 3 | Leaderboard shows **nicknames only**. Neon Auth keeps each user's email and name in our own Neon project (`neon_auth` schema); our tables never copy them, and other people only ever see the nickname | Privacy. Because we hold email addresses for users in the EU, we also owe them a short privacy note and a way to delete their data (phase 5) |
| 4 | Photos: **Cloudinary** free plan (25 credits/month), browser uploads straight to it with a permission slip signed by our API | Neon's 0.5 GB is too small for photos; keeps photo bytes off Render |
| 5 | AI: `gpt-5-mini` (already configured) for note proofreading and a photo sanity check | Existing key, existing rate limits |
| 6 | Report location: a **pin on a stream**, linked to the nearest of the 105 sites if within 1 km, else stored as "outside coverage" | The 105 sites are synthetic placements, not real stations |
| 7 | Moderator: the admin emails in `ADMIN_EMAILS`, and the token's email must be verified | Single-person moderation for a prototype |
| 8 | Points are **derived from an append-only ledger**, awarded only for approved reports, and reversed if a report is hidden | Simple to audit, hard to game |

## Architecture

```
Browser (React, Vercel)
  ├─ Neon Auth client ──sign in/up──▶ Neon Auth (users + sessions in our Neon DB)
  ├─ Authorization: Bearer <JWT> ───▶ FastAPI (Render) ──▶ Neon Postgres (pooled connection)
  │                                       ├─ verifies JWT against {AUTH_URL}/.well-known/jwks.json
  │                                       ├─ OpenAI (proofread, photo check)
  │                                       └─ signs Cloudinary upload params
  └─ photo file ────────────────────▶ Cloudinary (direct, signed upload)
```

The API keeps working with no database or auth configured: community endpoints answer 503 and the UI hides the feature.

## Data model (created phase by phase, one migration file each)

```sql
-- phase 1
profiles(user_id text pk, nickname text, nickname_key text unique generated lower(nickname),
         show_on_leaderboard bool default true, home_city text null, created_at timestamptz)

-- phase 2
reports(id uuid pk, user_id text, lat numeric, lon numeric, site_id text null, city text null,
        observed_at timestamptz, checklist jsonb, note_raw text, note_clean text,
        status text check in ('pending','approved','hidden'), created_at timestamptz)

-- phase 3
report_photos(id uuid pk, report_id uuid, cloudinary_public_id text, url text, width int, height int,
              ai_flags jsonb, ai_ok bool, created_at timestamptz)

-- phase 4
points_events(id bigserial pk, user_id text, report_id uuid null, points int, reason text, created_at timestamptz)
badges_awarded(user_id text, badge text, awarded_at timestamptz, primary key(user_id, badge))

-- phase 5
report_flags(id bigserial pk, report_id uuid, flagged_by text, reason text, created_at timestamptz)
moderation_actions(id bigserial pk, report_id uuid, admin_user_id text, action text, note text, created_at timestamptz)
```

## Rules

**Checklist** (all optional except at least one answer): water colour, smell, foam, litter, animals seen, flow, weather in the last 24 h. Free-text note up to 500 characters.

**Points** (v1, numbers live in one config so they are easy to tune):
- approved report +10; photo that passed the AI check (or was approved by a moderator) +5
- first report by you at a site +5; a site with no approved report in the previous 30 days +10
- weekly streak bonus +5 per consecutive week with a rewarded report, capped at +20
- weekly challenge completed +20
- caps: at most 3 rewarded reports per UTC day, and one rewarded report per site per user per 7 days (extra reports are still saved, just not rewarded)
- a report hidden by a moderator reverses its points with negative ledger entries

**Badges:** First report, Regular (5 reports), Explorer (5 different sites), Photographer (5 photo-verified reports), Three-week streak, Neglected-stream hero (3 neglected-site bonuses), Challenger (a weekly challenge). Awarded by rules after each rewarded report.

**Weekly challenge:** chosen deterministically from a small list by ISO week number (no table needed), for example "report a site you have not visited" or "include a photo".

**Auto-approval:** a report with no AI flags and no rate-limit warnings is approved on submit; otherwise it waits in the moderation queue. The reporter always confirms the AI-cleaned note before submitting, and both versions are stored.

## API surface

| Phase | Endpoints |
|---|---|
| 1 | `GET /api/community/status`, `GET /api/me`, `PUT /api/me/profile` |
| 2 | `POST /api/reports`, `GET /api/reports?site_id=&bbox=`, `GET /api/me/reports` |
| 3 | `POST /api/uploads/sign`, `POST /api/ai/proofread`, `POST /api/ai/photo-check` |
| 4 | `GET /api/leaderboard?scope=&city=`, `GET /api/me/progress`, `GET /api/challenge` |
| 5 | `POST /api/reports/{id}/flag`, `GET/POST /api/admin/reports`, `GET /api/fhir/citizen-observations`, `DELETE /api/me` |

All write endpoints need a valid token. AI endpoints share the existing per-client and daily limits, plus a per-user limit.

## Abuse and privacy

Sign-in required to report; per-user rate limits; nicknames are unique and checked against a reserved list; photos are resized in the browser (which also strips location metadata) and checked by AI for people, number plates and "is this a stream"; the UI warns not to photograph people; flagged content goes to the queue; hidden photos are deleted from Cloudinary (the CDN takes about 10 minutes to stop serving them). Our own tables hold no email and no real name (Neon Auth keeps them in its own schema), and phase 5 adds "delete my account", which removes the profile, reports, photos and the sign-in user.

## FHIR

Each approved report becomes an `Observation` with category `citizen-observation` (added to our category CodeSystem), one component per checklist answer, `performer` = an Organization for citizen reports (the nickname is not exported), and `subject` = the linked site Location when there is one. It is validated by the same `scripts/validate_fhir.py` run.

## Frontend

New in citizen view: **Report** (a four-step wizard: place, checklist, photo, review with the AI-cleaned note), **My streams** (points, badges, streak, my reports), **Leaderboard**. A sign-in dialog and account chip in the top bar. The map gets a toggle for a separate "citizen reports (unverified)" layer with ring markers; a site's page shows recent reports. Expert view gets the same layer and a read-only list.

## Phases (each its own PR; nothing half-finished is ever live)

| Phase | Scope | Done when |
|---|---|---|
| **1 Foundation** | Migrations, DB pool, JWT verification, profiles, `/api/community/status`, `/api/me`, sign-in and nickname UI behind a flag | Tests pass against a real local Postgres; with a Neon project connected, a person can sign up, choose a nickname, and reload still signed in |
| **2 Reports** | Reports table and API, the wizard without photo and AI, map layer, site page list, seeded sample reports (labelled as samples) | A signed-in user can file a report and see it on the map and on the site page |
| **3 Photos and AI** | Cloudinary signed upload, browser resize, photo check, proofreading, moderation queue for flagged photos | A photo report round-trips; a non-stream photo is flagged, not rejected |
| **4 Points** | Ledger, rules, caps, streaks, badges, challenge, leaderboard, My streams | Rule tests pass, including caps and reversal |
| **5 Moderation, FHIR, privacy** | Flag button, admin queue, hide with point reversal, FHIR export validated, privacy note, delete-my-account, docs | Validator reports 0 errors on the citizen bundle; deleting an account removes its data |

## Manual setup only the owner can do

1. **Neon:** create a free project; note the pooled connection string (`DATABASE_URL`).
2. **Neon Auth:** enable it on the project; note the Auth URL (`NEON_AUTH_BASE_URL`). Optionally enable Google sign-in.
3. **Render env vars:** `DATABASE_URL`, `NEON_AUTH_BASE_URL`, `ADMIN_EMAILS` (phase 5), Cloudinary keys (phase 3).
4. **Vercel env var:** `VITE_NEON_AUTH_URL` (the same Auth URL).
5. **Cloudinary:** free account (phase 3).

## Risks

- Neon Auth is new: phase 1 includes a real end-to-end check, and the fallback is Google-only sign-in or Supabase.
- Cold starts: the free database sleeps after 5 minutes idle, so the first request after a pause is slower.
- Neon's free limits: 0.5 GB storage and 100 compute-hours a month. Storage full means writes fail (no data lost).
- A demo with no reports looks empty, so phase 2 seeds sample reports clearly labelled "sample".
- Public sign-in invites spam; the mitigations above are part of the plan, not extras.
