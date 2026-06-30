---
name: meetinginsights
description: >
  Repair Romanian-primary, English-sprinkled user-testing transcripts and extract
  reviewable insights into a fixed HTML review tool. Use whenever the user has a
  transcript from a user-testing / usability / research session (or meeting) that is
  mostly Romanian with some English technical terms and wants it cleaned up and/or
  turned into triageable insight cards. Trigger on phrases like "use the meetinginsights
  skill", "meeting insights", "use meeting insights on this", "clean up this transcript",
  "extract ideas from this session", "user testing transcript", "the transcriber broke
  the words", or any time a raw session/meeting transcript (often with a recording) is
  provided for analysis. Also use when the user complains that mixed-language
  transcription mangled words, or that the transcript alone is too vague to act on.
---

# Meeting Insights

## Intake — gather inputs before doing anything

The moment this skill is invoked, **stop and collect three things** before any repair or
extraction. Don't start cleaning a transcript until you have them (or the user has
explicitly said an item isn't available). Ask for whatever the user hasn't already
provided:

1. **Session transcript** — the raw transcript text (or a path/file). This is required;
   without it there is nothing to repair. **If only a recording exists (a video/audio file
   on disk) and no transcript, do not stop — first invoke the `transcribe-video` skill on
   that recording to produce the raw transcript**, then proceed with the phases below
   using that generated transcript *together with* the original recording (the recording
   is still needed for frame extraction and audio repairs in steps 2 and Phase 3). The
   transcribe-video output is already in the diarized, timestamped `[HH:MM:SS] Speaker N:`
   format this skill ingests; treat it as raw — Phase 1 still repairs the Romanian and
   Phase 1b still reconciles speakers. Only stop if there is neither a transcript nor a
   readable recording on disk.
2. **Session recording** — the video/audio file, if available. Used only for screen
   context (frame extraction) and to resolve `query`/`confirm` repairs by listening.
   It must be a real file **on disk** to be usable for frames (a Drive/cloud link can't
   be read as video). Optional — note that without it, screen-dependent insights stay
   unresolved and some repairs remain best-guesses.
3. **A brief description of the session** — what was discussed or tested, who was in the
   room (and their roles), the product/feature area, and the goal of the session. This is the context that
   makes the repair and extraction sharp: it disambiguates domain terms the ASR mangled,
   tells you which insights matter, and seeds the masthead. Even one or two sentences
   helps a lot. Pin down four facts from it for the `SESSION` provenance block — **feature
   area, date, participant**, and a slug **id** — because these get flattened onto every
   exported insight so it stays self-describing once pooled with other sessions. If any are
   unstated, ask.

   **The `id` must be unique per session — it is the key that decides add-vs-replace when
   publishing.** Use `<feature>-<participant>-<date>` (e.g. `kb-export-cristi-2026-06-17`),
   *always including the participant*. The old `<feature>-<date>` form is **not collision-proof**:
   two people tested on the same feature on the same day produce the same id, and publishing the
   second one **overwrites the first on the sessions site** (the manifest upserts by `id`, and the
   page file is `sessions/<id>.html`). A new session must get a new id so it is **added, not
   replacing** an existing page. Re-using an id is reserved for *intentionally* updating that same
   session in place (iterating on one report). Before publishing, if there's any chance another
   session shares this feature+date, confirm the id is distinct (check the live index — see the
   publish step). If two participants were tested in one recording, give each its own id.

   **Establish the session type — it sets how every insight is attributed and what the
   report is *about*.** There are two shapes, and the skill is not biased toward either:

   - **User-testing / single-subject** (interview, usability test) — one **subject**, the
     tested person. Insights capture *their* stance, not the interviewer's (see Phase 2).
     Nail down which diarized speaker is the subject; mis-identifying them flips the
     attribution on every card.
   - **Meeting / sync / workshop** — *no single subject*; a peer discussion where everyone
     proposes, pushes back, and reflects. Here the report is about **what was discussed,
     how the topics evolved, and the conclusions reached** — and each insight is attributed
     to *whoever actually voiced it*, never centered on one person (see Phase 2). Because a
     point often changes mid-discussion, capture where it **landed**, and flag ideas that
     were intermediate or abandoned as such rather than presenting them as conclusions.

   Decide the type from the description. If the transcript doesn't make the format obvious
   (one subject being probed vs. peers talking as equals), **ask at the start** — don't
   guess. For a meeting, pin the **roster + roles** ("Bogdan — designer, presenting the
   prototype; Ana — PM; Bogdan — researcher, joins ~40 min"): role/expertise is the main
   lever for fixing diarization in Phase 1b, and two people can share a name. Reflect the
   outcome in `SPK` (readable name per code) and `SESSION.participant` (the subject for
   user-testing; the roster for a meeting). **When you invoke `transcribe-video` on a recording (intake step 1), pass that roster to
   it via `--speakers`; add `--voice-attrs` whenever the cast is cross-gender (it tags each
   line's perceived gender, pinning the woman's lines to her); and add `--diarize` whenever
   the cast is same-gender-suspect — i.e. two or more speakers who may share a gender (the
   classic two-men or Bogdan-designer/Bogdan-researcher case).** `--diarize` runs acoustic
   (pyannote) diarization and relabels speakers by voice, which is the one thing that
   actually separates **same-gender** speakers — exactly where `--voice-attrs` is powerless.
   The full-strength configuration is `--speakers` + `--voice-attrs` + `--diarize`.
   Prevention beats post-hoc reconciliation.

Use the session description to extend the working vocabulary beyond `assets/glossary.txt`
(product names, feature names, people) so Phase 1 repairs are grounded rather than
guessed. Only after you have the transcript (and have noted what's missing) proceed.

Two phases, always in this order: **Phase 1 — Repair**, then **Phase 2 — Extract**.
Never extract from a garbled transcript; ideas inherit the garble.

The output is a **single self-contained HTML review tool**. Its design is FIXED — it is
defined by `assets/template.html`, the canonical golden template. Do not redesign it,
re-derive its layout, or "improve" its structure on a whim. The skill exists to make
output *reproducible*; drift between runs is the failure mode this skill prevents.

## The one rule that prevents drift

**Build every output by copying `assets/template.html` and replacing ONLY the data and
three labelled regions. Keep all CSS, markup, and JS byte-for-byte otherwise.**

The reliable method is a small transform script (see "Build method" below), not
hand-writing HTML. Hand-authoring is how the layout, the metrics header, and the
three-bucket repair log silently regress.

The regions you may change:

1. **The data block** in `<script>` — replace `TURNS`, `IDEAS`, `REPAIRS`, `SPK`,
   `SESSION`, and `TOPICS_RO` (and `FRAMES`, if frames are extracted). Schema is in
   `references/idea-schema.md`. `SESSION` carries the provenance (id slug, feature, date,
   participant) that the JSON export flattens onto every insight so it survives pooling.
   Each idea carries `title_ro`/`detail_ro` and `TOPICS_RO` maps each topic to its Romanian
   label — these feed the **EN/RO toggle** (analysis only; see Phase 2 and idea-schema).
   `CAT_RO`/`CONF_RO` (category & confidence labels) are fixed template constants — leave them.
2. **The masthead** `<header class="mast">…</header>` — title, sub, eyebrow, speaker
   legend, and the four metric counters (leave the counter IDs untouched; JS fills them).
   Give the eyebrow / title / sub / each legend `<i>`’s inner `<span>` a `data-ro="…"`
   attribute with the Romanian rendering so the toggle can switch them (leave the
   `langtoggle` control and counter IDs alone).
3. **The note box** inside `<section id="view-rep">` — the "resolved by the audio"
   summary, rewritten for this session (or repurposed, e.g. to summarise frame
   resolution). If nothing was resolved, keep it short and factual. Give it a `data-ro="…"`
   (HTML allowed; entity-encode `<`/`>`) so it switches with the toggle.

Everything else — the three pill tabs (Ideas + transcript / Repair log / How this
works), the sticky transcript pane, card structure, the glossary-cluster repair log, the
category **and topic** filters, the **EN/RO language toggle** and its localization layer
(`setLang`, `disp`, `CAT_RO`/`CONF_RO`, the `data-ro` swap), export panel, footer,
responsive rules — is part of the template and stays. Also protected now: the **review round-trip** machinery — the hover action
buttons on cards/repairs/turns/masthead (`✎ Edit` / `💬 Comment`), the
in-place edit fields (revertible — `↺ Revert` in edit mode, or the clickable
`edited ✕` flag, discards the edit and restores the original), the comment boxes (each
has a `Remove comment` button, and a card's `comment ✕` flag removes it), the
**keep checkbox** (every card starts
**checked/included**; unchecking it excludes the card — the card fades out and is struck
through to make clear it won't be included, and it drops out of both the export and the
review packet), the toolbar edits/comments/excluded tally, and the `Send to Claude ↑`
packet panel (`#reviewPanel`, `buildPacket`). These are part of the template; preserve
them byte-for-byte like the tabs and filters. They are pure presentation/serialization —
never session data.
The **How this works** tab (`<section id="view-how">`) is a static
**two-lane handoff** diagram (imported from the "Human-Claude collaboration tool" Claude
Design project, Option A): **you** (blue person badge, left lane) and **Claude** (clay,
right lane, the real Claude glyph) in facing lanes, work crossing a central spine at each
handoff, so each step shows who acts — you hand over the session → Claude repairs →
Claude extracts (the steps this tool runs) → you review, edit & classify by destination
DB and answer open queries → Claude folds in the changes → Claude publishes to Notion via
the Notion MCP. The "Now" section uses solid spine/avatars; the "Next" section is dashed
and dimmed. Under 640px it collapses to a single-lane timeline. Icons are inline SVG
`<symbol>`s (`#ic-human` / `#ic-claude`); colors map to the template's CSS variables plus
a clay tone for Claude. It's not session data; leave it as-is unless the roadmap itself
changes. Two card features are
driven purely by the data, so they appear for free once `IDEAS` is filled — keep their
markup, CSS, and JS byte-for-byte:

- **Source-line navigation** (from each idea's `anchors`): the source chip shows the
  first timestamp plus a `· N lines` count when an idea spans more than one transcript
  line; clicking a card highlights every source line (red gutter bar on the first, green
  bars on the rest); and when highlighted lines sit outside the visible transcript,
  sticky "▲ N lines above / ▼ N lines below" pills appear at the pane edges and jump to
  the nearest off-screen one.
- **Topic chips + topic filter** (from each idea's `topics`): a quiet hairline-pill row
  at the bottom of each card lists the idea's topics, and the toolbar's second dropdown
  (built from the union of all `topics`) filters the card list by topic, ANDed with the
  category filter. Cards with no `topics` simply show no chip row.
- **Conflict links + filter** (from each idea's `conflictsWith`): cards in tension show a
  red `⚡ In tension with <title>` jump link (clicking activates/scrolls to the opposing
  card via the same `locate` plumbing), and the toolbar's **⚡ Conflicts** toggle filters
  to just the insights involved in a conflict. Cards with no `conflictsWith` show nothing.

## Phase 1 — Repair

Read the WHOLE transcript first. Then repair the Romanian, restoring the English domain
terms the ASR mangled. Heuristics and the glossary cluster format are in
`references/repair-heuristics.md`; the domain vocabulary is in `assets/glossary.txt`
(which doubles as the keyterm list to feed the transcriber upstream — prevention as
well as cure, and which you extend as new sessions surface new terms — see
**Grow the glossary**). Romanian and English are the only two languages anyone speaks in these
sessions, so any span the transcriber renders as a *third* language (French, Italian,
Spanish, etc.) is almost certainly an ASR error, not a real language switch — recover the
intended Romanian/English from context and repair it (see heuristic 6).

Record every fix in the three-bucket repair log:

- **auto** — applied confidently (domain terms, typos). Cluster every ASR spelling of
  one term into a single row: `["oladgebase · nowligebase · cube", "Knowledge Base / KB"]`.
  Use `"__DROP__"` as the fix to drop pure ASR artifacts (repetition loops, unintelligible interjections).
- **confirm** — best-guess reconstructions the user should verify (hallucinated words,
  heavily garbled phrases). Annotate the reasoning in parentheses.
- **query** — genuinely unrecoverable but meaningful tokens. The fix field holds the
  *question* to ask the user.

Mark in-transcript uncertain spans with `<span class="unsure" title="...">…</span>` so
they're visible in context (the template's transcript click-handler ignores them).

## Phase 1b — Reconcile speakers (diarization repair)

ASR diarization is frequently wrong in two ways: **phantom speakers** (one real person
split across several labels, so the transcript shows more voices than were in the room)
and **misattributed turns** (a line credited to the wrong voice — rife on backchannels,
crosstalk, and turn boundaries). Because Phase 2 attributes every insight *per turn*, a
bad diarization quietly poisons the whole extraction — so reconcile it before extracting,
as you read.

Anchor to the **known cast** you pinned at intake (how many real voices, who is the
subject). Collapse every ASR label onto the canonical `P`/`F`/`B`/`O` in `SPK` — a phantom
label must never reach `TURNS` — and re-attribute any turn whose *content* contradicts its
label (a clear facilitator prompt tagged as the participant, a first-person reaction
tagged as the facilitator, a question and its answer sharing one label). The decision
cues — role/content, adjacency logic, backchannels, and resolving by audio — are in
`references/repair-heuristics.md` ("Speaker / diarization reconciliation").

**In a meeting / peer session the "facilitator asks, participant reacts" asymmetry does
not exist** — everyone proposes and reflects in the first person, so that cue is useless
and misattributions persist (a peer's reflective line slides onto another peer). Lean
instead on the peer cues in the same reference: **role-knowledge** (each person owns a
domain — the PM states product facts/plans, the designer narrates the UI they built, the
engineer/researcher explains internals), **self-reference & ownership** ("prototipul meu",
"am făcut", "asumpția mea"), **name-mention logic** (a speaker never names themselves in
the third person — "l-am sunat pe Bogdan" ⇒ the speaker is *not* Bogdan; "mersi, Bogdan" ⇒
Bogdan is the addressee), and **stance continuity** (the person pressing a concern is
usually still pressing it two turns later). Then do a **voice-consistency re-read**: read
each speaker's lines as one monologue — any line that breaks the persona (wrong expertise,
opposite stance, self-address) is the misattribution to flip.

The peer failure mode is **silent guessing on a reflective line that fits either person**
equally ("cred că asumpția mea… e greșită" — a first-person reflection with no role,
ownership, or name tell). The cues above won't decide these, and that's exactly where ASR
errors hide. Don't pick silently: keep your best-guess speaker but log it as a
**confirm**/**query** (`["@33:49 „asumpția mea… e greșită”", "Bogdan or Ana?"]`), and set
`needs:true` on any card that leans on it, so the user settles it in the clarification pass
(or by audio). Flag the ambiguous ones rather than committing a coin-flip to a card.

**Acoustic diarization is the strongest speaker prior when present.** If the transcript was
produced with transcribe-video's `--diarize`, its `Speaker N` labels are acoustic voice
clusters — they separate **same-gender** speakers, which neither content cues nor gender
tags can do reliably. Trust the acoustic label above the gender tag and above content/role
cues. Two flags mark the lines that still need a human:
- `‹reattr gemini=Sx conf=c›` — the acoustic pass moved this line off the label Gemini's
  content-diarizer had given it. High `conf` that also agrees with the gender tag is safe to
  accept; treat a low-`conf` reattribution as a `confirm`.
- `‹mixed Sx/Sy›` — the turn's audio spans more than one speaker (Gemini merged two people
  into one line). Do **not** attribute it to a single person without splitting it by
  listening; log it `confirm`/`query` and mark dependent ideas `needs:true`.
This supersedes the old "same-gender voices defeat acoustic diarization" assumption: with
`--diarize` they don't. Reserve the content cues below for transcripts produced *without*
`--diarize`, and for resolving the flagged lines.

**Don't trust a re-transcription to settle same-voice peer lines** (tested). Re-running
`transcribe-video` on a stretch — even with `--speakers` — reliably fixes *phantom
speakers* and *role-clear* turns, but for two similar voices (e.g. two men) it is
**unstable at the line level**: successive runs disagree with each other and with the
original on who-said-what. So re-transcription is a *cross-check*, not ground truth. Trust
it only where it agrees with a **content anchor** (an English line being read from one
person's chat, UI narration, a name mention) or where two runs + the content all converge;
otherwise leave the line flagged and let the **person who was in the room** settle it via
the Phase 3 review (`Send to Claude ↑`). Audio you *listen to* still beats re-transcribing.
 (Acoustic `--diarize` is different — it *does* settle same-voice lines; this caveat is
about re-running Gemini's content-based diarization, not the pyannote pass.)

**Use voice-gender tags as a strong prior when present.** If the transcript carries per-line
gender tags (transcribe-video's `--voice-attrs` → `Speaker N (m/f/?)`), lean on them: in a
**cross-gender cast** the tag pins a line to the matching person — one woman in the room ⇒
every `(f)` line is hers — which collapses the most common confusion (her lines sliding onto
a male peer). Crucially the tag is judged *independently of the speaker label*, so a `(f)`
on a turn labeled as a male speaker is a **flagged slip — trust the gender over the label**.
This is the cheapest reliable separator because perceived gender is an easier call for the
model than fine speaker-ID. Limits: it **cannot** separate two same-gender speakers (fall
back to timing — who was even in the room then — plus the content cues above), and short
backchannels get shaky tags. So: request `--voice-attrs` whenever the cast is cross-gender;
it won't help an all-same-gender room.

Record it so it stays reviewable, don't silently rewrite:
- Set the masthead **"N speakers (diarized)"** sub to the **reconciled** count, not the
  ASR's inflated one, and say what you collapsed in your summary (e.g. "ASR's 5 labels →
  3 real speakers").
- A confidently-wrong label: just fix it. A **genuinely ambiguous** one: leave your
  best-guess speaker but log it as a **confirm**/**query** entry whose question is *who
  said this?* (e.g. `["@04:12 „nu merge ușor”", "the participant or a facilitator?"]`) so it
  rides the same clarification pass; if an insight leans on that turn, set the idea's
  `needs:true` + `q`.
- The user's Phase 3 **turn re-attribution** (transcript-line comments) is the correction
  channel for anything that still slips through — `turns[].comment` may say "this is
  Bogdan, not Cristi", and you apply it on rebuild.

## Phase 2 — Extract

Pull insights into `IDEAS`. Categories, confidence, anchors, topics: see
`references/idea-schema.md`. Every idea anchors to one or more transcript turn indices
for bidirectional click-to-trace. Every quote is the *repaired* Romanian — quotes are
shown Romanian-only, no English gloss (the card never translates the speaker).

**Attribute by session type** (decided at intake):

*User-testing / single-subject.* Frame insights from the **participant's perspective**.
The participant (`P`) is the research subject; facilitators (`F`/`B`) and observers (`O`)
*run* the session — their turns are usually **prompts, not findings**. When a facilitator
asks a question or floats a hypothesis, the insight is the participant's *response* to it:
attribute it to the participant (`speaker:"P"`), quote the participant's words, and title
their stance — not the interviewer's question. The most common failure is a card that
quotes/credits the facilitator and states their probe as if it were the finding (e.g.
"Bogdan's probe: should the warning be conditional?"); the real insight is what the
*participant* said back. Only attribute to `F`/`B`/`O` when it genuinely originates as
their own decision, constraint, or statement of fact — never for a question. A facilitator
prompt may be anchored as *context*, but put the participant's line first.

*Meeting / sync / workshop.* There is no privileged stance — **attribute each insight to
whoever actually voiced it** (the right code per the roster), quote that person, and title
*their* position. The report's job is to capture **the discussion and where it landed**,
so:
- **Track how topics evolve and record the conclusion, not the brainstorm.** When a point
  shifts during the talk (a tab structure is reshaped, an approach is dropped after a
  counter-argument), the card states where it **landed**; mention the earlier position only
  as context for *why*. Don't write a superseded mid-discussion idea up as if it were the
  outcome.
- **Mark unfinished and abandoned threads as such.** A question left open is `open_question`
  (say it wasn't resolved); an idea floated and discarded is either dropped or noted as
  rejected — not presented as a decision.
- **Genuine disagreement between two people** is a real `conflictsWith` pair (attribute
  each side to its speaker), even if they later converge — note the convergence in `detail`.

**Anchor the whole exchange, not just the trigger line.** A point usually spans several
turns — proposal → pushback → answer → elaboration. Anchor every turn that develops it
(quoting the most representative line of the attributed speaker), not just the first or
most quotable one. Under-anchoring hides the back-and-forth behind the card. Before
finalizing, re-scan each card: confirm the `speaker` and `quote` belong to the person the
insight truly originates with (in user-testing, that a facilitator line isn't standing in
for a misattributed participant reaction; in a meeting, that the quote passes the
voice-consistency check from Phase 1b), and check the turns just before and after each
anchor for lines by the same speaker that belong to the same idea.

Also
derive a small **controlled set of session topics** (~4–8 themes the session covered)
and tag each idea with one or more via `topics:[…]`, reusing the exact same label
strings across ideas so the topic-filter dropdown groups them. Set `needs:true` + `q`
only for ideas riding on an uncertain repair (these feed the "open queries" metric).

**Produce the Romanian analysis for the EN/RO toggle.** The report has an `EN | RO` switch
that flips **the analysis** to Romanian (UI chrome and quotes stay as they are). So for
every idea also emit `title_ro` and `detail_ro` (the Romanian of the headline and detail —
natural Romanian, keeping English domain terms as spoken, same as quotes), and emit a
`TOPICS_RO` map giving each topic label its Romanian display string. Write the masthead and
the repair-view note with `data-ro="…"` Romanian renderings (see the editable regions and
`references/idea-schema.md`). Category and confidence labels are translated by fixed
template constants — don't emit those. Quotes are **never** translated; they stay verbatim
repaired Romanian on both languages.
When two insights genuinely contradict each other (same subject, opposing stance), link
them **bidirectionally** via `conflictsWith:[id]` — the card shows a `⚡ In tension with`
jump link and a **⚡ Conflicts** toggle filters to them. Only link real contradictions,
not merely related points; true within-session conflicts are uncommon.

## Optional — Screen context (frames)

Sessions reference on-screen things the transcript can't resolve ("zona asta", "iconițele",
"cele 3 puncte"). If the recording is **on disk** (a real upload, not a Drive link —
`download_file_content` returns base64 into context and cannot handle a video), extract a
still at each screen-dependent insight's timestamp:

```
"${CLAUDE_SKILL_DIR}/assets/extract-frames.sh" VIDEO MANIFEST OUTDIR [scale_w]   # MANIFEST: id|HH:MM:SS|label
```

Base64-embed each frame into `FRAMES` keyed by idea id, set `frame:true` on those ideas,
and the template renders an inline "⌖ view frame" toggle on the card. This is the only
sanctioned *addition* to the template, because it's purely additive and styled to match.

## Optional — Publish to the sessions site

When the user wants to **share** a built report or collect sessions in one browsable
place ("publish this", "upload it to the Testing repo", "put it on the sessions site"),
publish the HTML to the GitHub repo `bogdandraghici/Testing` (served via GitHub Pages).
This is an **explicit opt-in step — never automatic** (like frames). It requires an
authenticated `gh` CLI; if `gh auth status` fails, tell the user to run `gh auth login`.

```
python3 "${CLAUDE_SKILL_DIR}/scripts/publish.py" <path-to-report.html> ["commit message"]
```

The script parses the report's `SESSION` + `IDEAS` (topics union, insight count, title),
shallow-clones the repo (initialising `main` if it's still empty), copies the report to
`sessions/<SESSION.id>.html`, **upserts** the session into `sessions.json` (keyed by
`id`), regenerates `index.html` from `assets/index-template.html`, commits all three,
pushes to `main`, enables Pages if needed, polls, and prints two URLs on its last stdout
lines:

> **Publishing ADDS — it must never silently replace another session.** Because the
> manifest is keyed by `id` and the page lives at `sessions/<id>.html`, publishing a
> report whose `id` matches an *existing, different* session overwrites that session's
> entry **and its HTML file**. So: a **new** session must have a **unique `id`** (include
> the participant — see Intake) so it lands *alongside* what's already there. Re-using an
> `id` is **only** for deliberately updating the *same* session in place (iterating on one
> report). **Before publishing a new session, check the live index
> (`https://bogdandraghici.github.io/Testing/`) — if the `id` you're about to publish is
> already listed for a different participant/session, change this session's `id` first.**
> If you discover you've already overwritten one, the previous version is recoverable from
> the repo's git history (`git show <prev-commit>:sessions/<id>.html`) — restore it under a
> distinct id.

- index:   `https://bogdandraghici.github.io/Testing/` — a session browser that filters
  and sorts **by feature area** (sessions grouped by feature, newest date first within each)
- session: `https://bogdandraghici.github.io/Testing/sessions/<id>.html`

Report both URLs to the user. First-time deploys can take ~30–90s; the script waits and
notes if the page isn't 200 yet. Don't hand-edit `index.html` / `sessions.json` in the
repo — the script regenerates them. See `references/publishing.md` for the manifest
schema and mechanics.

## Build method (reliable, drift-free)

1. `cp "${CLAUDE_SKILL_DIR}/assets/template.html" <out>.html`
2. Write a short Python transform that: builds `TURNS/IDEAS/REPAIRS/SPK/FRAMES` as data,
   `json.dumps` them, and does targeted `re.sub`/`str.replace` on the three regions only.
   (`json.dumps(..., ensure_ascii=False)` is valid JS and safely escapes the HTML in
   transcript text.)
3. Validate before delivering: each data block must `json.loads`; the card render still
   has its `${topics}` interpolation; no leftover content from the template's worked example.

## Clarification pass — one question at a time

The `confirm` and `query` repairs (and any idea with `needs:true`) are open items the
transcript alone couldn't settle. After the first report is built, walk the user through
them **interactively, one question at a time** — never dump them as a batch or a numbered
list to answer all at once.

For each open item:

- Ask a single, self-contained question: show the garbled span, your best-guess
  reconstruction (for `confirm`) or the specific unknown (for `query`), and enough
  repaired transcript context to judge it. Listen to the recording first if it's on disk
  and might resolve the item without asking.
- The user may **answer** or **skip** it. Wait for their response before asking the next
  one. Don't proceed in parallel.
- If **answered**: fold the resolution in — promote `confirm` → `auto`, resolve the
  `query`, fix the in-transcript span (drop its `unsure` mark), and update any affected
  idea quote, `topics`, or `needs`/`q` flag.
- If **skipped**: leave it untouched — it stays in its `confirm`/`query` bucket, the
  `unsure` span and any `needs:true` idea remain, and it still counts toward the open-queries
  metric. Skipping is always allowed; never push.

After every item has been answered or skipped, **rebuild the HTML report** with the
resolutions folded in (same drift-free Build method below — recopy the template, re-emit
the data blocks, re-run validation). Mention what changed (e.g. counts moved from
`query`/`confirm` into `auto`, open-queries metric dropped). If the user skipped
everything, say so and leave the report as-is rather than rebuilding needlessly.

## Phase 3 — Fold in review

After the report is delivered, the user can edit insight-card fields, comment on
any section, and exclude cards (by unchecking them) directly in the HTML, then hit **`Send to Claude ↑`** to
produce a **review packet** (JSON by default; Markdown mirror). When the user pastes
one back:

**Recognize the cue.** The user rarely says "here is the review packet." They say things
like *"I've left some comments"*, *"check the changes I made"*, *"I reviewed the cards"*,
*"see my edits"*, *"I dropped a few"*, or *"take a look at the updates in the report"*.
Treat any such phrasing as a request to fold in their `Send to Claude ↑` review — that
packet is the channel their in-browser edits/comments/exclusions travel through. If they
said this but pasted nothing, don't go hunting or guess: ask them to click **`Send to
Claude ↑`** in the report and paste the packet (JSON or Markdown), then proceed below.

1. Parse it. Confirm `session` matches the report you built. The packet carries only
   what changed — untouched cards/repairs/turns are omitted. An **empty packet**
   (just `{session}`) means no changes: say so and leave the report as-is.
2. Apply it onto the working data:
   - `cards[].edits` — overwrite those exact fields on the matching `IDEAS` entry
     (`title`, `detail`, `quote`, `category`, `confidence`, `topics`). A `title_ro` /
     `detail_ro` key means the user edited that card **while viewing Romanian** — apply it
     to the RO field and **regenerate the English counterpart** (and vice-versa) so the two
     languages stay in sync.
   - `cards[].excluded:true` — the user unchecked that card; drop the idea entirely.
   - `cards[].note`, `report_note` — treat as instructions; they may direct merges,
     re-scoping, re-attribution, or wording the raw field edits can't express.
   - `repairs[]` (keyed by `bucket` + the garbled `orig` string) — act on the repair
     comment (fix it, leave it, re-bucket it).
   - `repair_section_note`, `turns[].comment` (keyed by transcript index `i`) —
     fold in re-attributions and repair-log direction.
3. Rebuild the HTML with the **same drift-free Build method** below — recopy
   `assets/template.html`, re-emit the data blocks, re-run validation.
4. Summarize what changed (e.g. "applied 3 edits, dropped idea-11, re-attributed
   turn 9 to B, merged idea-05 into idea-04").

The user's in-browser work is never silently lost — it lives in the packet, and the
rebuilt report reflects it. This is the **You → Claude** review loop the "How this
works" diagram shows.

## Grow the glossary (compounding across sessions)

`assets/glossary.txt` is the canonical, **growing** keyterm list — it both anchors Phase 1
repairs and (fed upstream) primes the transcriber so the *next* session comes back
cleaner. Every session is a chance to enrich it. The names and sessions used throughout
these references (a participant called Cristi, the "KB export/import" session, etc.) are
**only examples** — this skill runs on other recordings, other people, other features, and
other products. Nothing in the glossary or heuristics is tied to one session; treat it all
as a reusable, accumulating base.

So, as a **closing step** after Phase 1 + the clarification pass have settled the terms:

- **Append newly-confirmed domain terms** that aren't already in `assets/glossary.txt` —
  product names, feature names, UI labels, recurring people — one canonical term per line
  (ordering doesn't matter; keep near-duplicates like `chunk` / `chunk-uri` as separate
  lines if both appear). Only add terms you're confident about (promoted out of
  `confirm`/`query`, or obvious product vocabulary), never raw garble.
- **Say what you added.** In your summary, list the terms appended to the glossary so the
  user knows the shared asset changed (it's the skill's own file — the edit persists for
  every future session).

This is a deliberate edit to the skill's shared asset, and it's the point: each run makes
transcription and repair a little better for the next.

## Asset paths

`${CLAUDE_SKILL_DIR}` resolves to this skill's own directory at runtime, regardless of
whether the skill is installed personally (`~/.claude/skills/`), per-project
(`.claude/skills/`), or as a plugin. Use it for `assets/template.html`,
`assets/extract-frames.sh`, `assets/glossary.txt`, `assets/index-template.html`,
`scripts/publish.py`, and the `references/` files. If the variable is unset (older
runtimes), fall back to paths relative to this SKILL.md.

## Speaker codes

`P` participant · `F`/`B` two facilitators (blue-ish / plum) · `O` team/observer. Map the
ASR's diarization labels onto these and set readable names in `SPK` — reconciling phantom
and misattributed labels first (see **Phase 1b**), so a label in `SPK`/`TURNS` always
corresponds to a real person.
