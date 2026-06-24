# Review round-trip for the meetinginsights report

**Date:** 2026-06-24
**Status:** Approved design, pre-implementation

## Problem

The meetinginsights skill produces a single self-contained HTML review tool. Today the
report is **read-only** except for one control — the per-card "keep" checkbox that feeds
the "Export kept" downstream output (for Notion). There is no way for the reviewer to
correct an insight, comment on what they're seeing, or drop a bad card and have those
changes flow back to Claude for a rebuild.

The tool's own "How this works" diagram already advertises this loop as *future, not yet
built*: **You — Review, edit & classify** → **Claude — Folds in your changes**. This spec
builds exactly that step.

## Goal

After Claude generates the first report, the user can, in the browser:

1. **Edit** any insight card's fields in place.
2. **Comment** on cards, repair-log entries, the repair-log section, transcript turns, and
   the report as a whole.
3. **Cut** insight cards they want removed.

Then ship all of that back to Claude as one packet, and Claude **rebuilds** the report with
the changes folded in — using the same drift-free build method the skill already relies on.

## Non-goals

- No server, no auto-save to disk. The page stays a single self-contained `file://` HTML.
- No touch/mobile affordance for editing (this is a desktop review tool).
- The existing "Export kept" Markdown/JSON output is unchanged — it still feeds Notion
  downstream and is a *separate* concern from the review packet.

## Interaction model — hover-reveal

The report's default character is calm and read-first. Nothing new is visible until the
user expresses intent by hovering. Hovering an editable/commentable area surfaces small
ghost action buttons in its corner:

| Area | Buttons revealed on hover |
|------|---------------------------|
| Insight card | `✎ Edit` · `💬 Comment` · `✕ Cut` |
| Repair-log entry | `💬 Comment` |
| Repair-log section header | `💬 Comment` |
| Transcript turn | `💬 Comment` |
| Masthead | `💬 Comment on the whole report` |

There is **no global "review mode" toggle** — hover is the discovery mechanism, and an
untouched report is byte-for-byte the experience it is today.

### Actions

- **`✎ Edit`** flips that card's fields to editable in place:
  - `title`, `detail`, `quote` → editable text (`contenteditable`, styled read-only until
    focused, subtle dashed underline on focus).
  - `category`, `confidence` → dropdowns (the fixed enum sets).
  - `topics` → editable chips (add/remove/rename).
  - Re-clicking `✎` (or clicking away) commits the edit back into the in-memory model.
- **`💬 Comment`** opens a small note box attached to the area; typing + blur stores the
  comment.
- **`✕ Cut`** marks the card for removal: it stays visible but struck-through and dimmed,
  and toggles back off on a second click.

### Keeping state visible (hover-reveal safety)

Because affordances are hover-only, the tool must not lose track of what the user touched:

- **Persistent markers.** Any area with an edit or comment keeps a quiet always-visible
  mark (a small dot / an "edited" tag). Cut cards stay struck-through + dimmed.
- **Standing toolbar tally + send.** The toolbar always shows a live count
  (`3 edits · 2 comments · 1 cut`) and a **`Send to Claude ↑`** button. This is the one
  always-on new element; without it, hover-only work would be invisible and un-shippable.

The existing per-card "keep" checkbox and "Export kept" button are left exactly as they are.
Cut (round-trip removal, back to Claude) and keep (downstream selection, to Notion) are
distinct intents and stay separate controls.

## The review packet

`Send to Claude ↑` produces a single JSON blob the user copies or downloads and pastes into
chat. It captures **only what changed**, plus enough identity to apply cold:

```json
{
  "session": "kb-export-2026-06-17",
  "report_note": "too many naming cards — consider merging",
  "cards": [
    { "id": "idea-04", "cut": false,
      "edits": { "title": "Rename “Delete” → “Delete content”", "confidence": "high" },
      "note": "merge with idea-05" },
    { "id": "idea-11", "cut": true, "note": "EMEL was a transcription error, drop it" }
  ],
  "repairs": [ { "bucket": "query", "orig": "zona asta de EMEL", "comment": "leave as-is" } ],
  "repair_section_note": "buckets look right",
  "turns": [ { "i": 9, "comment": "this is Bogdan, not the participant" } ]
}
```

Rules:

- **`edits`** holds only the fields actually changed — read live from the DOM at export time
  and diffed against the original baked-in `IDEAS` data, so the packet stays small and
  unambiguous.
- Untouched cards, repairs, and turns do **not** appear.
- An empty packet (no edits/comments/cuts anywhere) means "no changes"; Claude says so
  rather than rebuilding.
- A **Markdown mirror** is available via the same format toggle the existing export uses,
  but **JSON is the default** since Claude is the consumer.
- `repairs[]` entries are keyed by `orig` (the garbled source string, which is unique within
  a bucket) so they survive the rebuild even though repairs have no stable id.
- `turns[]` entries are keyed by transcript index `i`.

This is a **second, separate** export from "Export kept" — different intent, different
button, different payload.

## Files changed

### `assets/template.html` (the golden template)

- **CSS:** hover action buttons; edit-mode field styling; comment boxes; cut/dimmed state;
  persistent edit/comment markers; toolbar tally + send button. All in the existing
  paper/ink visual language — same restraint as the sanctioned "frames" addition.
- **Markup:** hooks on cards, repair rows, the repair section header, transcript turns, and
  the masthead so the JS can attach affordances.
- **JS:** a self-contained module that tracks edits/comments/cuts in memory, renders the
  hover buttons and comment boxes, maintains the tally, and builds the packet (JSON + MD).
  Pure presentation/serialization — no change to the existing data-render or locate/export
  plumbing beyond what's needed to attach the new affordances.

### `SKILL.md`

- Extend **"The one rule that prevents drift"** and the regions list: the review
  affordances are now part of the protected template and must be preserved byte-for-byte
  across runs (like the tabs, transcript pane, filters, etc.).
- Add a **"Phase 3 — Fold in review"** section documenting how Claude ingests a pasted
  packet and rebuilds (see below). Position it after the existing "Clarification pass"
  section, since clarification (open queries) and review (edits/comments/cuts) are both
  post-first-report loops.

### "How this works" diagram (inside the template)

- The two `future`/dashed lanes — **You — Review, edit & classify** and
  **Claude — Folds in your changes** — become **present/solid** (move under the "Now" phase),
  since they are now built.
- The **Claude — Publishes to Notion** lane stays in the dashed "Next" phase.

## Phase 3 — Fold in review (Claude's side)

When the user pastes a review packet, Claude:

1. Parses it; validates `session` matches the current report.
2. Applies `cards[].edits` onto the matching `IDEAS` entries; removes `cut:true` cards; acts
   on `cards[].note`, `report_note`, repair comments, repair-section note, and turn comments
   as instructions (these may trigger re-wording, re-attribution, merges, repair fixes, etc.).
3. Rebuilds the HTML via the **existing drift-free Build method** — recopy
   `assets/template.html`, re-emit the data blocks, re-run validation.
4. Summarizes what changed (e.g. "applied 3 edits, dropped idea-11, re-attributed turn 9 to
   B, merged idea-05 into idea-04").
5. If the packet is empty, says so and leaves the report as-is rather than rebuilding.

The user's in-browser edits are never silently lost: they live in the packet, and the
rebuilt report reflects them.

## Approaches considered

- **Round-trip mechanism:** review-packet export (chosen) vs. download-edited-HTML vs.
  auto-save-to-disk. Packet export is the only option that preserves the
  single-self-contained-HTML guarantee the skill is built on.
- **Affordance discovery:** hover-reveal per area (chosen) vs. a global "review mode" toggle
  vs. always-editable fields. Hover keeps the default read exactly as today while making the
  affordance local to what the user points at.
- **Edit model:** directly-editable fields **and** a freeform per-card note (chosen) — field
  edits for precise changes, the note for higher-level intent (merge, re-scope) that field
  edits can't express.
- **Cut signal:** a separate cut/drop control (chosen) vs. reusing/flipping the keep
  checkbox — keeps the round-trip "remove" intent distinct from the downstream "select for
  Notion" intent.
```
