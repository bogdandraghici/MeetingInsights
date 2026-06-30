# Data schema (matches assets/template.html exactly)

## TURNS — `[code, "MM:SS" | "HH:MM:SS", htmlText]`
- `code`: P (participant) · F / B (two facilitators) · O (team/observer)
- Indexed by array position; ideas anchor to these indices (`t-<index>` in the DOM).
- `htmlText` may contain `<span class="unsure" title="…">…</span>` for in-context
  uncertain markers (the transcript click-handler skips clicks on `.unsure`).

## IDEAS — object per insight
```
{
  id:        "i1",                 // stable, also the FRAMES key
  title:     "Short imperative headline",
  title_ro:  "Same headline in Romanian", // for the EN/RO toggle — analysis only (see below)
  category:  pain_point | feature_request | naming_copy |
             design_decision | design_insight | open_question | context,
  topics:    ["Export / import", "Validation & usage"], // 1+ from the session's controlled set
  detail:    "1–3 sentences, plain English",
  detail_ro: "Same 1–3 sentences in Romanian", // for the EN/RO toggle
  quote:     "verbatim REPAIRED Romanian",
  speaker:   "P" | "F" | "B" | "O", // default "P"; use F/B/O only for their OWN decision/fact, never a probe
  confidence:"high" | "medium" | "low",
  needs:     false,                // true only if the idea rides on an uncertain repair
  q:         "question to confirm" // present only when needs:true; feeds open-queries metric
  anchors:   [12, 14],             // ALL turns that develop the idea; first = primary (the participant's line)
  conflictsWith:["i7"],            // optional; ids of insights this one is in tension with
  frame:     true                  // optional; renders the embedded FRAMES[id] toggle
}
```

`conflictsWith` links insights that contradict each other (same subject, opposing
stance) — e.g. "flag removed content as a breaking change" vs "only warn when it's
actually used". When you spot such a pair during extraction, list each one's id in the
other's `conflictsWith` (keep it **bidirectional** so the link shows on both cards). The
template renders a red `⚡ In tension with <title>` link on the card that jumps to the
opposing card, and a toolbar **⚡ Conflicts** toggle filters to just the insights in
tension. Within a single session true conflicts are uncommon — only link genuine
contradictions, not merely related or differently-scoped points. (Cross-session conflicts
are the bigger pool, but those are reconciled downstream, not here.)

`topics` is a controlled per-session vocabulary: derive a small set (~4–8) of the
themes the session actually covered (e.g. "Export / import", "Naming & labels",
"Replace vs append") and tag each idea with one or more. Reuse the exact same label
strings across ideas so the topic filter groups them — don't invent a near-duplicate
phrasing per card. The template builds the topic-filter dropdown from the union of all
`topics`, so consistency is what makes it useful. Quotes are Romanian-only now (no
English gloss is shown or stored).

## EN / RO language toggle (analysis only)
The report has an `EN | RO` switch in the masthead (default **EN**, choice remembered in
`localStorage['mi-lang']`). It switches **the analysis** to Romanian and leaves everything
else as-is. Switched: card `title`/`detail` (via `title_ro`/`detail_ro`), topic chips and
the topic-filter labels (via `TOPICS_RO`), category badges + the category-filter labels
(via the template's fixed `CAT_RO`), confidence badges (via `CONF_RO`), the masthead, and
the repair-view note. **Not** switched: quotes (always verbatim Romanian), speaker names,
the repair-log terms, and all UI chrome (tabs, toolbar buttons, export/review panels,
"How this works", footer, transcript-pane header). RO falls back to EN wherever a `*_ro`
value is missing, so a report with no Romanian still works.

What the **build** must emit per session (Phase 2):
- `title_ro` + `detail_ro` on every idea (Romanian of the headline + detail).
- `const TOPICS_RO = { "<EN topic>": "<RO topic>", … }` — one entry per topic in the
  controlled set. The EN string stays the canonical filter key; RO is display-only.
- The masthead (eyebrow / title / sub / each legend `<i>`’s inner `<span>`) and the
  repair-view `.note` each carry a `data-ro="…"` attribute with the Romanian rendering
  (HTML allowed; entity-encode `<`/`>` as `&lt;`/`&gt;` in the attribute). EN stays the
  element’s normal content.

`CAT_RO` (the 7 categories) and `CONF_RO` (high/medium/low) are **fixed constants shipped
in the template** — don’t emit them per session.

**Review packet & language:** editing a card while viewing RO writes to `title_ro` /
`detail_ro` (the edit field’s `data-f` resolves per language). So a packet `edits` object
with a `title_ro`/`detail_ro` key *is* a Romanian edit — the field name encodes the
language; there is no separate `lang` flag. On fold-in, update that language’s field and
regenerate the counterpart translation so EN and RO stay in sync. Quotes always edit
`quote` (Romanian); category/confidence are language-neutral enums; topic editing always
edits the canonical EN `topics` list (the filter keys), so add a `TOPICS_RO` entry for any
newly-added topic.

## SUMMARY — collapsed session summary (top of the Ideas tab)
A short, scannable bullet recap shown in a `<details>` box above the insight cards
(collapsed by default). A list of sections; each section's `kind` picks a fixed bilingual
heading from the template (`SUM_LABELS`), and the items are succinct one-line bullets.
```
const SUMMARY = [
  { kind:"strengths",  items:["…", "…"], items_ro:["…", "…"] },
  { kind:"weaknesses", items:["…"],       items_ro:["…"] }
];
```
- `kind`: `strengths` (green) · `weaknesses` (red) · `points` (neutral). Headings come from
  the template — don't emit them.
- **User-testing** → two sections, `strengths` vs `weaknesses` (the weak/strong split).
- **Meeting / workshop** → a single `points` section (key points + where things landed).
- `items` is English; `items_ro` is the Romanian for the EN/RO toggle (falls back to
  `items` when absent). Keep bullets short — one line each, a handful per section.
- Empty or absent `SUMMARY` → the box isn't rendered. It is **not** exported and **not**
  part of the review packet — it's a derived recap of the cards, regenerate it on rebuild.

## REPAIRS — `{ auto:[[o,f]], confirm:[[o,f]], query:[[o,question]] }`
See references/repair-heuristics.md. Cluster ASR spellings; `"__DROP__"` to drop.

## FRAMES — `{ "i2": "data:image/jpeg;base64,…", … }`
One entry per idea with `frame:true`. Produced by assets/extract-frames.sh, base64-embedded.

## SPK — `{ P:"…", F:"…", B:"…", O:"…" }`  readable display names.

## SESSION — provenance, flattened onto every exported insight
```
{
  id:          "kb-export-cristi-2026-06-17", // slug <feature>-<participant>-<date>; the pool namespace
  feature:     "Knowledge Base export/import",
  date:        "2026-06-17",
  participant: "Cristi"
}
```
These insights get pooled with other sessions/features in a downstream database, so the
**JSON export is the unit that travels and must be self-describing**. The "Export kept"
JSON does not emit the raw `IDEAS`; it emits flat, pool-ready rows — each one namespaced
and carrying its own provenance:
```
{ id:"<SESSION.id>:<idea.id>", session, feature, date, participant,
  title, category, topics, detail, evidence_quote, speaker, confidence,
  needs_confirmation, question, timestamps,
  title_ro, detail_ro, topics_ro }   // bilingual fields, emitted when present (pool reads either language)
```
So one insight row is meaningful standalone in the pool. The in-page `idea-NN` ids stay
session-local in the DOM (anchors, highlights) — only the *export* id is namespaced.
Because `SESSION.id` is also the publish key (`sessions/<id>.html`, manifest keyed by
`id`), it **must be unique per session** so publishing *adds* rather than overwriting
another session — include the participant in the slug. See `references/publishing.md`.
`topics` stay free-form per session (no shared taxonomy); near-duplicate labels are
reconciled in the downstream pooling/dedup step, not here.

## Metrics (auto-computed by template JS; do not hardcode)
- ideas = IDEAS.length
- kept  = live count of checked cards
- repairs = auto + confirm + query lengths
- open queries = REPAIRS.query.length + IDEAS.filter(needs).length
