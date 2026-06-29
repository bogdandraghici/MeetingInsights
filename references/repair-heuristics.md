# Repair heuristics (RO-primary, EN technical terms)

The transcriber is set to Romanian, so English domain words come back phonetically
Romanianised or fragmented. The repair restores the intended term while keeping the
sentence in Romanian.

## How to repair

1. **Restore EN domain terms verbatim.** When a garble maps to a known product/UX term,
   replace it with the proper English spelling (`MZP` → `MCP`, `oligbeis` → `knowledge
   base`, `pefuri` → `path-uri`, `InstraKilo` → `instrucțiune`). The glossary
   (`assets/glossary.txt`) is the anchor list.
2. **Keep code-switching natural.** Romanian connective grammar around the English term
   stays (`chunk-uri`, `build-uri`, `knowledge base-uri`).
3. **Hallucinations → meaning.** ASR sometimes invents real words ("Jessica", "Superman").
   If context gives the intent, reconstruct it and put the entry in the **confirm**
   bucket with the reasoning, never **auto**.
4. **Don't invent confidence.** If a token is meaningful but unrecoverable, it goes in
   **query** with the question to ask — do not paper over it.
5. **Drop artifacts.** Repetition loops ("Corect. Corect. …"), unintelligible
   one-word interjections, non-Latin script noise → `__DROP__` in auto.
6. **Other languages = almost always an ASR error.** These sessions are Romanian-primary
   with English technical terms — those are the only two languages anyone actually speaks.
   So a span the transcriber renders as some *other* language (French, Italian, Spanish,
   German, etc.) is almost never a real language switch; it's the ASR mis-decoding mangled
   Romanian or a phonetically-Romanianised English term into a similar-sounding foreign
   word. Treat it as garble: recover the intended Romanian/English from context and the
   surrounding sentence. If the intent is clear, fix it (**auto** for an obvious domain
   term, **confirm** for a reconstruction with the reasoning noted); if it's meaningful but
   unrecoverable, **query** it. Don't leave foreign-language text standing as if the
   participant said it.

## Speaker / diarization reconciliation

The ASR separates voices imperfectly — it invents extra speakers and staples lines to the
wrong one. Fix attribution while you repair the text; Phase 2 trusts the per-turn speaker,
so errors here cascade into every card.

1. **Anchor to the real cast.** The session description tells you how many people were
   actually in the room and who the subject is. More ASR speaker labels than real voices
   means the extras are fragments — one person split by the diarizer. Merge them onto the
   right canonical code (`P`/`F`/`B`/`O`); the masthead speaker count is the *reconciled*
   number, never the ASR's inflated one.
2. **Role tells you who.** Facilitators prompt — questions, tasks, "ce te-ai aștepta să
   se întâmple aici?", "hai să încercăm". The participant reacts — first-person intent,
   judgments, narrating what they see ("eu m-aș aștepta…", "nu-mi dau seama unde…"). A
   turn whose content is a clear prompt but is labeled participant (or a first-person
   reaction labeled facilitator) is misattributed — flip it.
3. **Adjacency logic.** A question and its answer are two different speakers. Two
   consecutive turns under one label where the role plainly shifts (ask → answer) is a
   boundary error — split and re-attribute.
4. **Backchannels are the worst offenders.** "Mhm", "da", "aha", "ok", "corect" get
   stapled to whoever the diarizer was tracking, often wrongly. Attribute them by what's
   happening around them (the listener acknowledges the speaker), or `__DROP__` them if
   they carry nothing (heuristic 5).
5. **Listen to settle it.** If the recording is on disk, a doubtful attribution is
   resolved exactly like a `confirm`/`query` text repair — play the timestamp and hear who
   spoke. Prefer this over guessing.
6. **Surface what you can't settle.** A confidently-wrong label: fix it silently (it's
   mechanical). A genuinely ambiguous one: keep your best-guess speaker and log it as
   **confirm**/**query** with the question phrased as *who said this?*
   (`["@04:12 „nu merge ușor”", "the participant or a facilitator?"]`) so it reaches the user in
   the clarification pass; if an insight leans on that turn, mark the idea `needs:true`.

### Peer meetings — when there is no facilitator/subject asymmetry

Heuristic 2 (facilitator asks, participant reacts) is the strongest cue in a user test and
**useless in a meeting/sync/workshop**: everyone proposes, pushes back, and reflects in the
first person, so reflective and proposing turns get stapled to the wrong peer (e.g. one
person's *"asumpția mea… it's wrong"* lands on another). Same-gender voices with similar
speech defeat acoustic diarization, so lean on *content*:

a. **Role-knowledge — who would say this?** Each person owns a domain. The PM states
   product facts, plans, and priorities; the designer narrates the UI they built and walks
   the prototype ("pe tab-ul ăsta", "am pus aici"); the engineer/researcher explains
   internals and constraints (architecture, training, scores). A turn whose *content* sits
   squarely in one person's domain is theirs, whatever the ASR label says.
b. **Self-reference & ownership.** First-person ownership ties a turn to its owner:
   "prototipul meu", "am făcut", "din discuția mea cu Claude", "asumpția mea". Follow the
   thread — the person who *held* an assumption is the one who later says it was wrong.
c. **Name-mention logic.** A speaker doesn't name themselves in the third person.
   "L-am sunat pe Bogdan / oare mai e la birou?" ⇒ the speaker is **not** Bogdan.
   "Mersi mult, Bogdan" ⇒ Bogdan is the *addressee*, so the speaker is someone else.
   Two people can share a name — disambiguate by role (e.g. `Bogdan-D` / `Bogdan-R`).
d. **Stance continuity.** Positions persist across the back-and-forth: whoever raised a
   concern is usually still pressing it a few turns later, and whoever proposed an idea
   defends it. A label that suddenly flips its own stance mid-thread is two people merged.
e. **Voice-consistency re-read (do this once before extracting).** Read each speaker's
   turns in sequence as a single monologue. Any line that breaks the persona — wrong
   expertise, opposite stance, or addressing themselves — is a misattribution: flip it to
   the peer it fits. This pass catches what per-turn reading misses.

## Repair-log bucket format

`REPAIRS = { auto:[[orig,fix],…], confirm:[[orig,fix],…], query:[[orig,question],…] }`

- **Cluster** all ASR spellings of one term into a single `orig`, joined by ` · `:
  `["ceancuri · ceank-urile · chafk-urile", "chunk / chunk-uri"]`. One row per concept,
  not per occurrence.
- Annotate reconstructions in parentheses: `"comut la script  (switch to the script)"`.
- `__DROP__` renders as "[dropped — fragments]".

## Confirmed FlowX domain vocabulary (seed for clusters + keyterm prompt)

These are **product** terms — reusable across every session whatever the feature or
participant — mirroring `assets/glossary.txt`, the canonical list that **grows** as new
sessions surface new vocabulary (see SKILL.md → "Grow the glossary"). When a session
introduces a new confirmed term, add it to the glossary so the next session benefits.

Knowledge Base / KB · chunk / chunk-uri · entry / entry-uri · store (store → entries →
chunks) · build / builds · branch / branches · runtime · sandbox · UAT · workspace ·
query / queries · metadata fields (language, author, is_confidential, topic, locale,
region) · FlowX Database · Agent Builder · custom agent · REST node · identify intent ·
data transformation · script · condition · parallel · subflow · MCP / MCP Tool / MCP
server · knowledge base node · input / output · run · chat testing · workflow ·
node / noduri · Kiwi chatbot · Mortgage System / Mortgage Advisor.
