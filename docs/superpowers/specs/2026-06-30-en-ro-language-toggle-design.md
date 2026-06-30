# EN/RO language toggle for meetinginsights reports

## Goal
Add an **EN | RO** switch to the report so the analysis can be read in Romanian as well
as English. Default **EN**, choice remembered per-report via `localStorage`.

## Scope (decided with the user)
**Switches to Romanian (analysis):** card titles, card details, topic chips + topic-filter
labels, category badges + category-filter labels, confidence badges, the masthead
(eyebrow / title / sub / legend), and the repair-view note box.

**Stays as-is:** quotes (already Romanian-only, verbatim), speaker names, repair-log
terms, and all UI chrome — the three pill tabs, toolbar buttons (All / Clear / ⚡ Conflicts
/ Send to Claude), export & review panels, the "How this works" diagram, the transcript
pane header, and the footer.

## Design — purely additive (same philosophy as frames)
EN mode behaves byte-for-byte as today; RO is layered on top via fallback, so a report
with no `_ro` data still works (RO falls back to EN).

### Data (per-session, emitted by the build)
- Each `IDEAS` entry gains optional `title_ro` and `detail_ro`.
- One top-level `TOPICS_RO = { "<EN topic>": "<RO topic>" }` map. EN topic strings stay the
  canonical filter keys; RO is display-only.
- Masthead + note box carry RO via `data-ro="..."` attributes on each translatable element
  (EN stays the element's normal content; captured into `data-en` on first run).

### Constants (shipped in the template, fixed — not per session)
- `CAT_RO` — the 7 categories → Romanian labels.
- `CONF_RO` — high/medium/low → Romanian labels.

### Machinery (added to the template JS — this is the new golden template)
- `lang` state (`'en'|'ro'`), seeded from `localStorage['mi-lang']`, default `'en'`.
- An `EN | RO` segmented control (reuses existing `.seg` styling) in the masthead
  `.mast-cmt` row, so it's visible on every tab.
- Display helpers: `disp(it,key)` (RO field with EN fallback for title/detail),
  `localized(it)` (returns an idea with display title/detail/topics), `catLabel`,
  `confLabel`, `localizeTopic`. EN-mode results are identical to today's output.
- `setLang(l)`: persists, re-renders non-editing cards, relabels the two filter dropdowns
  (values unchanged → active filter is preserved), swaps masthead/note text, re-applies
  filters.
- `cardHTML` routes title/detail/topics/category/confidence through the helpers. The
  `⚡ In tension with <title>` link localizes the linked title too.

### Review round-trip (the one subtlety)
Editing a card while in RO writes to the RO field: the edit field's `data-f` resolves to
`title_ro` / `detail_ro` in RO mode (quote always edits `quote`; category/confidence are
language-neutral enums; **topic editing always edits the canonical EN topic list**, so
filter keys stay stable). The review packet therefore carries `edits:{title_ro:…}` when the
edit was made in RO — the field name itself encodes the language, so no separate `lang`
flag is needed. On fold-in, Claude updates that language's field and regenerates the
counterpart translation to keep the two in sync.

### Export
The JSON export rows additionally carry `title_ro`, `detail_ro`, and `topics_ro` when
present (bilingual, language-independent of the current view) so the downstream pool can
read either language. Markdown export stays EN-primary.

## Docs to update
- `references/idea-schema.md` — `title_ro`/`detail_ro`, `TOPICS_RO`, `CAT_RO`/`CONF_RO`,
  masthead `data-ro`, export ro fields, packet `*_ro` semantics.
- `SKILL.md` — Phase 2 also produces RO title/detail + `TOPICS_RO` + RO masthead/note;
  the editable-regions list now includes the `data-ro` attributes; quotes stay RO-only.
- The golden `assets/template.html` worked example is fully translated (all 15 example
  ideas + masthead + note + topics) so the toggle is coherent in the template itself.

## Out of scope
Translating quotes, speaker names, UI chrome, or the "How this works" diagram.
