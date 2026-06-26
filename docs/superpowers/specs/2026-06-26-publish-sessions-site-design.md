# Publish to the sessions site — design

**Date:** 2026-06-26
**Skill:** meetinginsights
**Status:** approved

## Goal

Add an optional step to the meetinginsights skill that publishes a built review-tool
HTML to the user's GitHub repo `bogdandraghici/Testing` and serves it via GitHub Pages.
Published sessions are listed on a generated **index page** that lets you filter by
**topic** (primary) and **feature area**, sorted by **date** (newest first).

This mirrors the existing `randomdocs` publish pattern (clone → copy → commit → push →
poll Pages → return URL) but adds a topic-aware index instead of a flat CI-rebuilt
listing.

## Non-goals

- No cross-session topic taxonomy reconciliation — topic labels are used verbatim;
  near-duplicate labels from different sessions appear as separate chips (YAGNI).
- No participant filter on the index (only topic + feature filter, date sort).
- No CI workflow — the index is regenerated locally by the publish script.
- Publishing is never automatic; it is an explicit opt-in step.

## Hosting & repo layout

`bogdandraghici/Testing` (public; currently **empty** — no branches). Pages serves the
`main` branch root.

```
index.html              ← generated; session browser
sessions.json           ← manifest (source of truth), array of session entries
sessions/<id>.html      ← published reports, one file per SESSION.id
```

- Index URL:   `https://bogdandraghici.github.io/Testing/`
- Session URL: `https://bogdandraghici.github.io/Testing/sessions/<id>.html`

## Manifest entry schema (`sessions.json[]`)

```json
{
  "id": "ml-doc-classification-2026-06-25",
  "title": "ML document classification — training & testing",
  "feature": "ML document classification — model training & testing",
  "date": "2026-06-25",
  "participant": "George",
  "file": "sessions/ml-doc-classification-2026-06-25.html",
  "topics": ["Testing & metrics", "Held-out pool & 80/20", "..."],
  "insights": 32,
  "published": "2026-06-26"
}
```

- `id`, `title?`, `feature`, `date`, `participant` come from the report's `SESSION`
  block (title falls back to the masthead `<h1>` / feature).
- `topics` = sorted union of every `IDEAS[].topics` value in the report.
- `insights` = `IDEAS.length`.
- Keyed by `id`: re-publishing the same session **upserts** (replaces) its entry and file.

## Components

### `scripts/publish.py` (new)
Single CLI: `python3 scripts/publish.py <path-to-report.html> ["commit message"]`.

Steps:
1. Read the report; extract `SESSION`, `IDEAS` (→ topics union, count), masthead `<h1>`
   via the same `json.loads` regexes the build uses. Fail clearly if blocks are missing.
2. Shallow-clone `bogdandraghici/Testing` to a temp dir via `gh repo clone`. If the repo
   is empty (no HEAD), create branch `main` and an initial state.
3. Copy report → `sessions/<id>.html`.
4. Load `sessions.json` (or `[]`), upsert this session by `id`, sort by `date` desc.
5. Regenerate `index.html` from `assets/index-template.html` with the manifest inlined.
6. `git add sessions/<id>.html sessions.json index.html`; commit (skip if no diff);
   push to `main` (use `-u origin main` on first push).
7. Ensure Pages is enabled: `GET repos/.../pages`; if 404, `POST` with
   `source.branch=main, source.path=/`.
8. Poll the session URL until HTTP 200 (bounded), print session URL + index URL on the
   last stdout lines.

Requires authenticated `gh`. On auth failure, instruct the user to run `gh auth login`.

### `assets/index-template.html` (new)
Static, self-contained session browser styled to match `template.html`'s editorial look
(same CSS variables, type, rules). Contains a `SESSIONS = [...]` placeholder the script
replaces with the manifest array. Renders:
- A masthead (title "User-testing sessions", count).
- A topic chip row (union of all `topics`) — click to filter to sessions containing it;
  multi-select ANDs are unnecessary, single-select toggle is enough (YAGNI).
- A feature-area dropdown filter.
- Session cards (title, date, participant, feature, insight count, topic chips), sorted
  by date desc, each linking to its `file`. Filtering by topic/feature hides
  non-matching cards. Empty state when no match.

### SKILL.md (edit)
- New section "**Optional — Publish to the sessions site**": when to use, the command,
  the URLs returned, the upsert-on-republish behavior, and that it's opt-in.
- The "How this works" roadmap lane already ends with "publish" — point it at this repo.

### `references/publishing.md` (new)
Mechanics: manifest schema, empty-repo init, Pages enablement, re-publish/upsert, the
URL shape, and the `gh` auth prerequisite.

## Data flow

```
built report.html ──parse──> {SESSION, topics, count}
                                   │
sessions.json (clone) ──upsert(id)─┤──> sessions.json'
                                   │
assets/index-template.html ──inline(sessions.json')──> index.html
                                   │
   git add sessions/<id>.html sessions.json index.html → commit → push main
                                   │
                          enable Pages (if needed) → poll → URLs
```

## Error handling

- Missing/!json data blocks in the report → abort with a clear message (don't publish a
  malformed report).
- `gh` not authenticated / clone fails → tell user to `gh auth login`.
- No diff after upsert (identical re-publish) → skip commit, still print URLs.
- Pages not yet 200 after polling → print the URL anyway with a "deploys shortly" note
  (first deploy can take ~30–90s), matching randomdocs.

## Verification

After implementation, publish the merged George report
(`george-ml-classification-review.html`) end-to-end: confirm the repo gets
`index.html`, `sessions.json`, `sessions/ml-doc-classification-2026-06-25.html`; Pages
turns on; the session URL serves 200; the index lists the session and its topic/feature
filters work.
