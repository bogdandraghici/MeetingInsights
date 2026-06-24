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

## Repair-log bucket format

`REPAIRS = { auto:[[orig,fix],…], confirm:[[orig,fix],…], query:[[orig,question],…] }`

- **Cluster** all ASR spellings of one term into a single `orig`, joined by ` · `:
  `["ceancuri · ceank-urile · chafk-urile", "chunk / chunk-uri"]`. One row per concept,
  not per occurrence.
- Annotate reconstructions in parentheses: `"comut la script  (switch to the script)"`.
- `__DROP__` renders as "[dropped — fragments]".

## Confirmed FlowX domain vocabulary (seed for clusters + keyterm prompt)

Knowledge Base / KB · chunk / chunk-uri · entry / entry-uri · store (store → entries →
chunks) · build / builds · branch / branches · runtime · sandbox · UAT · workspace ·
query / queries · metadata fields (language, author, is_confidential, topic, locale,
region) · FlowX Database · Agent Builder · custom agent · REST node · identify intent ·
data transformation · script · condition · parallel · subflow · MCP / MCP Tool / MCP
server · knowledge base node · input / output · run · chat testing · workflow ·
node / noduri · Kiwi chatbot · Mortgage System / Mortgage Advisor.

## Known un-resolved tokens (carry forward across sessions)

- **EMEL** — an area Cristi saw near KB export (2026-06-17 session). Never resolved.
  Does NOT appear in the Cata B workflow-editing session. Still open.
- **EOR** — a token in the Cata B custom-agent setup line (~11:27). Unrecoverable; in query.
