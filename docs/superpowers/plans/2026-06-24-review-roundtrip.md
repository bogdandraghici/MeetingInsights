# Review Round-Trip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a reviewer edit insight-card fields, comment on any section, and cut cards directly in the generated HTML report, then ship those changes back to Claude as one JSON packet that Claude folds into a rebuilt report.

**Architecture:** All UI lives in the golden template `assets/template.html`. A single in-memory `REVIEW` state object tracks edits/cuts/comments. Hover reveals per-area action buttons (`✎ Edit` / `💬 Comment` / `✕ Cut`); a standing toolbar tally + `Send to Claude ↑` button serializes `REVIEW` into a review packet (JSON default, Markdown mirror). Claude's ingestion side is documented prose in `SKILL.md` (no code).

**Tech Stack:** Vanilla HTML/CSS/JS in one self-contained file. No framework, no build step, no bundler.

## Global Constraints

- **One self-contained HTML file.** No external assets, no server dependency at runtime. (`assets/template.html`)
- **Drift rule:** everything outside the three sanctioned data/masthead/note regions is preserved byte-for-byte across runs. This feature *adds* protected template machinery; once merged it is part of the protected surface and must not regress. (`SKILL.md`)
- **No JS test framework exists in this repo and none is added.** The test cycle for every task is **browser verification** via the preview MCP tools, against a static server (see "Verification harness"). Each task's "test" step defines an exact, observable outcome and first confirms it currently fails (the affordance is absent), then implements until it passes.
- **Visual language:** match the existing paper/ink CSS variables (`--paper`, `--ink`, `--rule`, `--mark`, `--green`, `--amber`, `--ink-soft`). No new color identities; reuse the existing restraint (same bar as the sanctioned "frames" addition).
- **Editing is desktop-only;** no touch/hover fallback is required.
- **The existing "keep" checkbox + "Export kept" output are untouched.** Cut (round-trip removal) is a separate control from keep (downstream Notion selection).

## Verification harness (used by every task's test steps)

From the skill assets dir, serve the template and drive it with the preview tools:

```bash
cd /Users/bogdandraghici/.claude/skills/meetinginsights/assets
python3 -m http.server 8765
```

Then in the preview tools: `preview_start` (or navigate) to `http://localhost:8765/template.html`. The template ships with a worked example (the KB-export session) baked into `TURNS`/`IDEAS`/`REPAIRS`, so it renders fully standalone — no data substitution needed to test. Use `preview_eval` to read DOM/JS state, `preview_click`/`preview_fill` to drive affordances, `preview_snapshot`/`preview_screenshot` to confirm outcomes. Kill the server when done.

## File structure

- **Modify `assets/template.html`** — all CSS, markup hooks, and JS for the feature. One file by design (self-contained HTML).
- **Modify `SKILL.md`** — drift-rule + regions update, new "Phase 3 — Fold in review" section.
- **Modify the "How this works" diagram** — lives inside `assets/template.html` (`<section id="view-how">`); the two `future` review lanes move to the solid "Now" phase.

There is no logical split across files: the template is intentionally monolithic. Tasks below slice the work by *feature surface*, each independently demoable in the browser.

---

### Task 1: Review state model, toolbar tally, and the Send-to-Claude packet panel

Establishes the `REVIEW` state, the always-on toolbar tally + button, the second export panel, and the `buildPacket()` serializer. No per-area affordances yet — so the tally reads all zeros and the packet is empty. This is the spine everything else writes into.

**Files:**
- Modify: `assets/template.html` (CSS block ~line 161 near `.export`; toolbar markup ~line 218; JS near the export functions ~line 683–705)

**Interfaces:**
- Produces (consumed by Tasks 2–5):
  - Global `const REVIEW = { edits:{}, cuts:{}, notes:{}, repairComments:{}, repairSectionNote:"", turnComments:{}, reportNote:"" }`
  - Global `const ORIG = {}` mapping `idea.id → original IDEA object`
  - `function effective(it)` → `{...it, ...(REVIEW.edits[it.id]||{})}`
  - `function renderTally()` → recomputes and writes the toolbar counts
  - `function commitReviewChange()` → call after any REVIEW mutation; runs `renderTally()` and, if the review panel is open, `renderReview()`
  - `function buildPacket()` → packet object per spec
  - DOM ids: `#review-tally`, `#reviewPanel`, `#reviewBox`, `#rfmt-json`, `#rfmt-md`

- [ ] **Step 1: Write the failing test (define expected outcome, confirm absent)**

Serve and load the template (see harness). In the preview, run:
```js
preview_eval: (function(){ return { hasTally: !!document.getElementById('review-tally'), hasBtn: !!document.querySelector('[data-act="send-review"]'), hasBuild: typeof buildPacket }; })()
```
Expected NOW (fails): `{ hasTally:false, hasBtn:false, hasBuild:"undefined" }`.

- [ ] **Step 2: Add the packet panel CSS**

In `assets/template.html`, immediately after the `.export textarea{...}` rule (~line 164), add:
```css
  /* review round-trip */
  .review{display:none;border:1px solid var(--mark);border-radius:12px;background:#fff;padding:16px;margin:0 0 20px}
  .review.show{display:block}
  .review .row{display:flex;gap:8px;align-items:center;margin-bottom:10px}
  .review .lead{font-size:13px;color:var(--ink-soft);margin:0 0 10px}
  .review textarea{width:100%;height:220px;border:1px solid var(--rule);border-radius:8px;padding:12px;font-family:ui-monospace,Menlo,monospace;font-size:12px;background:var(--paper);resize:vertical}
  .review-tally{font-size:12px;color:var(--ink-soft)}
  .review-tally em{color:var(--mark);font-style:normal;font-weight:700}
  button.send{background:var(--mark);color:#fff;border:none;border-radius:8px;padding:8px 13px;font:inherit;font-size:13px;cursor:pointer}
  button.send[disabled]{opacity:.45;cursor:default}
```

- [ ] **Step 3: Add the toolbar tally + Send button**

In the toolbar (`<div class="toolbar">` ~line 218), insert immediately before `<span class="spacer"></span>`:
```html
          <span class="review-tally" id="review-tally" data-tip=""></span>
```
And immediately after the existing `<button class="act" onclick="openExport()">Export kept ↓</button>` (~line 226), add:
```html
          <button class="send" data-act="send-review" id="sendReview" onclick="openReview()" disabled>Send to Claude ↑</button>
```

- [ ] **Step 4: Add the review panel markup**

Immediately after the existing `<div class="export" id="exportPanel">…</div>` block (closes ~line 241), add:
```html
        <div class="review" id="reviewPanel">
          <p class="lead">Your edits, comments, and cuts — paste this back into Claude to rebuild the report. Untouched items are omitted.</p>
          <div class="row">
            <div class="seg">
              <button id="rfmt-json" aria-pressed="true" onclick="setReviewFmt('json')">JSON</button>
              <button id="rfmt-md" aria-pressed="false" onclick="setReviewFmt('md')">Markdown</button>
            </div>
            <span class="spacer"></span>
            <button class="ghost act" onclick="copyReview()">Copy</button>
            <button class="act" onclick="downloadReview()">Download</button>
            <button class="ghost act" onclick="closeReview()">Close</button>
          </div>
          <textarea id="reviewBox" readonly></textarea>
        </div>
```

- [ ] **Step 5: Add the JS — state, tally, builder, panel**

In the `<script>`, immediately after the line `IDEAS.forEach(it=>it.anchors.forEach(...));` that builds `turnToIdeas` (~line 538), add:
```js
const ORIG={};IDEAS.forEach(it=>{ORIG[it.id]=it;});
const REVIEW={edits:{},cuts:{},notes:{},repairComments:{},repairSectionNote:"",turnComments:{},reportNote:""};
function effective(it){return Object.assign({},it,REVIEW.edits[it.id]||{});}
```

Then, immediately after the existing `downloadOut()` function (~line 704), add:
```js
// ---- Review round-trip ----
const CATS=['pain_point','feature_request','naming_copy','design_decision','design_insight','open_question','context'];
const CONFS=['high','medium','low'];
function nonEmpty(s){return typeof s==='string'&&s.trim().length>0;}
function changedFields(id){
  const e=REVIEW.edits[id];if(!e)return{};const o=ORIG[id],out={};
  for(const k in e){const a=k==='topics'?(o.topics||[]):o[k];
    if(JSON.stringify(a)!==JSON.stringify(e[k]))out[k]=e[k];}
  return out;
}
function buildPacket(){
  const cards=[];
  IDEAS.forEach(it=>{
    const ch=changedFields(it.id),note=REVIEW.notes[it.id],cut=!!REVIEW.cuts[it.id];
    const hasEdit=Object.keys(ch).length>0;
    if(hasEdit||cut||nonEmpty(note)){const c={id:it.id};
      if(cut)c.cut=true;if(hasEdit)c.edits=ch;if(nonEmpty(note))c.note=note.trim();cards.push(c);}
  });
  const repairs=[];
  Object.keys(REVIEW.repairComments).forEach(key=>{const cm=REVIEW.repairComments[key];
    if(!nonEmpty(cm))return;const ix=key.indexOf(' ');
    repairs.push({bucket:key.slice(0,ix),orig:key.slice(ix+1),comment:cm.trim()});});
  const turns=[];
  Object.keys(REVIEW.turnComments).forEach(i=>{const cm=REVIEW.turnComments[i];
    if(nonEmpty(cm))turns.push({i:+i,comment:cm.trim()});});
  const p={session:SESSION.id};
  if(nonEmpty(REVIEW.reportNote))p.report_note=REVIEW.reportNote.trim();
  if(cards.length)p.cards=cards;
  if(repairs.length)p.repairs=repairs;
  if(nonEmpty(REVIEW.repairSectionNote))p.repair_section_note=REVIEW.repairSectionNote.trim();
  if(turns.length)p.turns=turns;
  return p;
}
function packetCounts(){
  let edits=0,comments=0,cuts=0;
  IDEAS.forEach(it=>{if(Object.keys(changedFields(it.id)).length)edits++;
    if(REVIEW.cuts[it.id])cuts++;if(nonEmpty(REVIEW.notes[it.id]))comments++;});
  Object.values(REVIEW.repairComments).forEach(c=>{if(nonEmpty(c))comments++;});
  Object.values(REVIEW.turnComments).forEach(c=>{if(nonEmpty(c))comments++;});
  if(nonEmpty(REVIEW.repairSectionNote))comments++;
  if(nonEmpty(REVIEW.reportNote))comments++;
  return {edits,comments,cuts};
}
function renderTally(){
  const {edits,comments,cuts}=packetCounts();
  const parts=[];
  parts.push(`<em>${edits}</em> edit${edits===1?'':'s'}`);
  parts.push(`<em>${comments}</em> comment${comments===1?'':'s'}`);
  parts.push(`<em>${cuts}</em> cut`);
  document.getElementById('review-tally').innerHTML=parts.join(' · ');
  document.getElementById('sendReview').disabled=(edits+comments+cuts===0);
}
function commitReviewChange(){renderTally();
  if(document.getElementById('reviewPanel').classList.contains('show'))renderReview();}
let rfmt='json';
function packetToMd(p){
  let o=`# Review for ${p.session}\n`;
  if(p.report_note)o+=`\n**Report note:** ${p.report_note}\n`;
  (p.cards||[]).forEach(c=>{o+=`\n## ${c.id}${c.cut?' — CUT':''}\n`;
    if(c.edits)for(const k in c.edits)o+=`- edit \`${k}\` → ${JSON.stringify(c.edits[k])}\n`;
    if(c.note)o+=`- note: ${c.note}\n`;});
  if(p.repairs&&p.repairs.length){o+=`\n## Repairs\n`;
    p.repairs.forEach(r=>{o+=`- [${r.bucket}] \`${r.orig}\` — ${r.comment}\n`;});}
  if(p.repair_section_note)o+=`\n**Repair-log note:** ${p.repair_section_note}\n`;
  if(p.turns&&p.turns.length){o+=`\n## Transcript\n`;
    p.turns.forEach(t=>{o+=`- turn ${t.i} (${TURNS[t.i]?TURNS[t.i][1]:'?'}): ${t.comment}\n`;});}
  return o;
}
function renderReview(){const p=buildPacket();
  document.getElementById('reviewBox').value=rfmt==='json'?JSON.stringify(p,null,2):packetToMd(p);}
function openReview(){document.getElementById('reviewPanel').classList.add('show');renderReview();
  document.getElementById('reviewPanel').scrollIntoView({behavior:'smooth',block:'nearest'});}
function closeReview(){document.getElementById('reviewPanel').classList.remove('show');}
function setReviewFmt(f){rfmt=f;document.getElementById('rfmt-json').setAttribute('aria-pressed',f==='json');
  document.getElementById('rfmt-md').setAttribute('aria-pressed',f==='md');renderReview();}
function copyReview(){const t=document.getElementById('reviewBox');t.select();
  navigator.clipboard.writeText(t.value).then(()=>toast('Copied'));}
function downloadReview(){const ext=rfmt==='json'?'json':'md';
  const blob=new Blob([document.getElementById('reviewBox').value],
    {type:rfmt==='json'?'application/json':'text/markdown'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);
  a.download='review-'+SESSION.id+'.'+ext;a.click();URL.revokeObjectURL(a.href);toast('Downloaded');}
renderTally();
```

- [ ] **Step 6: Run the test to verify it passes**

Reload the page. Run:
```js
preview_eval: (function(){ const p=buildPacket(); return { tally: document.getElementById('review-tally').textContent, btnDisabled: document.getElementById('sendReview').disabled, packet: p }; })()
```
Expected: `tally:"0 edits · 0 comments · 0 cut"`, `btnDisabled:true`, `packet:{session:"kb-export-2026-06-17"}`.
Then `preview_click` the (now forced-enabled for test) panel by running `preview_eval: openReview()` and confirm `#reviewBox` shows `{ "session": "kb-export-2026-06-17" }`. Screenshot the toolbar to confirm the tally + greyed button render in the paper/ink style.

- [ ] **Step 7: Commit**

```bash
cd /Users/bogdandraghici/.claude/skills/meetinginsights
git add assets/template.html
git commit -m "feat(review): review state, toolbar tally, and Send-to-Claude packet panel"
```

---

### Task 2: Card hover tools + Edit mode (fields → packet edits)

Adds the hover action cluster to each card and the `✎ Edit` flow that flips title/detail/quote to editable, category/confidence to dropdowns, and topics to editable chips, writing changes live into `REVIEW.edits`.

**Files:**
- Modify: `assets/template.html` (CSS after the review block from Task 1; the IDEAS render loop ~line 583–591; new JS after the Task-1 review JS)

**Interfaces:**
- Consumes (from Task 1): `REVIEW`, `ORIG`, `effective`, `commitReviewChange`, `CATS`, `CONFS`, `changedFields`
- Produces (consumed by Tasks 3–4):
  - `function rerenderCard(id)` — rebuilds a card's body from `effective()` + re-attaches tools + re-applies state classes
  - `function attachCardTools(card,it)` — appends the `.cardtools` cluster
  - `function applyCardState(card,id)` — toggles `has-edit`/`has-note`/`has-cut` classes
  - CSS classes `.cardtools`, `.card.editing`, `.card.has-edit`

- [ ] **Step 1: Write the failing test**

Load template. Run:
```js
preview_eval: (function(){ const c=document.getElementById('c-idea-04'); return { hasTools: !!c.querySelector('.cardtools'), hasRerender: typeof rerenderCard }; })()
```
Expected NOW (fails): `{ hasTools:false, hasRerender:"undefined" }`.

- [ ] **Step 2: Add card-tools + edit-mode CSS**

After the review CSS block (from Task 1), add:
```css
  .card{position:relative}
  .cardtools{position:absolute;top:8px;right:8px;display:flex;gap:4px;z-index:3;
    background:var(--paper);border:1px solid var(--rule);border-radius:8px;padding:3px;
    opacity:0;transition:opacity .12s;box-shadow:0 2px 8px var(--shadow)}
  .card:hover .cardtools{opacity:1}
  .cardtools button{font:inherit;font-size:11px;line-height:1;border:none;background:none;
    color:var(--ink-soft);border-radius:5px;padding:5px 7px;cursor:pointer;white-space:nowrap}
  .cardtools button:hover{background:var(--paper-2);color:var(--ink)}
  .cardtools button.on{background:var(--mark);color:#fff}
  .card.editing{box-shadow:0 0 0 2px var(--blue),0 1px 0 var(--shadow)}
  .card.editing .cardtools{opacity:1}
  .flags{display:flex;gap:6px;margin-top:9px}
  .flag{font-size:10px;letter-spacing:.07em;text-transform:uppercase;font-weight:700;
    border-radius:5px;padding:2px 7px}
  .flag.edit{background:#E2EBF1;color:#33536F}
  .flag.note{background:#EDE6D6;color:#7A6320}
  .flag.cut{background:#F6E3DF;color:#9A352A}
  .efield[contenteditable="true"]{outline:none;border-bottom:1px dashed var(--blue);
    background:#F7FAFD;border-radius:3px;padding:0 2px}
  .card.editing .quote.efield[contenteditable="true"]{background:#F7FAFD}
  .esel{font:inherit;font-size:12px;border:1px solid var(--rule);border-radius:6px;padding:3px 6px;background:#fff}
  .echip{display:inline-flex;align-items:center;gap:5px}
  .echip button{border:none;background:none;color:var(--mark);cursor:pointer;font-size:12px;padding:0 2px}
  .topic-add{font:inherit;font-size:10.5px;border:1px dashed var(--rule);border-radius:999px;
    padding:2px 8px;width:120px}
```

- [ ] **Step 3: Refactor the card render to be re-renderable + attach tools**

Replace the existing IDEAS render loop (~line 583–591):
```js
IDEAS.forEach(it=>{
  const card=document.createElement('div');
  card.className='card';card.id='c-'+it.id;card.dataset.cat=it.category;
  card.dataset.topics=(it.topics||[]).join('|');
  card.dataset.conflict=conflictIds.has(it.id)?'1':'';
  card.innerHTML=cardHTML(it);
  card.addEventListener('click',()=>locate(it.id,false));
  ideasEl.appendChild(card);
});
```
with:
```js
IDEAS.forEach(it=>{
  const card=document.createElement('div');
  card.className='card';card.id='c-'+it.id;card.dataset.cat=it.category;
  card.dataset.topics=(it.topics||[]).join('|');
  card.dataset.conflict=conflictIds.has(it.id)?'1':'';
  card.addEventListener('click',()=>{if(card.classList.contains('editing'))return;locate(it.id,false);});
  ideasEl.appendChild(card);
  rerenderCard(it.id);
});
```
(`rerenderCard` is defined in Step 4; it fills `innerHTML` from `effective()` and attaches tools/state.)

- [ ] **Step 4: Add the edit-mode JS**

After the Task-1 review JS (after `renderTally();`), add:
```js
function rerenderCard(id){
  const it=IDEAS.find(x=>x.id===id);const card=document.getElementById('c-'+id);
  card.classList.remove('editing');
  card.innerHTML=cardHTML(effective(it));
  attachCardTools(card,it);applyCardState(card,id);
}
function applyCardState(card,id){
  const edited=Object.keys(changedFields(id)).length>0;
  card.classList.toggle('has-edit',edited);
  card.classList.toggle('has-note',nonEmpty(REVIEW.notes[id]));
  card.classList.toggle('has-cut',!!REVIEW.cuts[id]);
  const body=card.lastElementChild; // the <div> from cardHTML
  let flags=card.querySelector('.flags');if(flags)flags.remove();
  const tags=[];
  if(edited)tags.push('<span class="flag edit">edited</span>');
  if(nonEmpty(REVIEW.notes[id]))tags.push('<span class="flag note">comment</span>');
  if(REVIEW.cuts[id])tags.push('<span class="flag cut">cut</span>');
  if(tags.length){const f=document.createElement('div');f.className='flags';
    f.innerHTML=tags.join('');body.appendChild(f);}
}
function attachCardTools(card,it){
  const t=document.createElement('div');t.className='cardtools';
  t.innerHTML=`<button data-t="edit">✎ Edit</button><button data-t="comment">💬 Comment</button><button data-t="cut">✕ Cut</button>`;
  t.querySelectorAll('button').forEach(b=>b.addEventListener('click',e=>{
    e.stopPropagation();const k=b.dataset.t;
    if(k==='edit')enterEdit(it.id);}));
  card.appendChild(t);
}
function enterEdit(id){
  const it=IDEAS.find(x=>x.id===id);const card=document.getElementById('c-'+id);
  const e=REVIEW.edits[id]=Object.assign({title:undefined,detail:undefined,quote:undefined,
    category:undefined,confidence:undefined,topics:undefined},REVIEW.edits[id]||{});
  // seed from effective values
  const eff=effective(it);
  ['title','detail','quote','category','confidence'].forEach(k=>{if(e[k]===undefined)e[k]=eff[k];});
  if(e.topics===undefined)e.topics=(eff.topics||[]).slice();
  card.classList.add('editing');
  card.innerHTML=cardEditHTML(it,e);
  // tool cluster shows Done
  const t=document.createElement('div');t.className='cardtools';
  t.innerHTML=`<button data-t="done" class="on">✓ Done</button>`;
  t.querySelector('button').addEventListener('click',ev=>{ev.stopPropagation();commitEdit(id);});
  card.appendChild(t);
  wireEdit(card,id);
}
function cardEditHTML(it,e){
  const src=TURNS[it.anchors[0]][1];
  const catOpts=CATS.map(c=>`<option value="${c}"${c===e.category?' selected':''}>${c.replace('_',' ')}</option>`).join('');
  const confOpts=CONFS.map(c=>`<option value="${c}"${c===e.confidence?' selected':''}>${c}</option>`).join('');
  const chips=(e.topics||[]).map((tp,i)=>`<span class="topic echip" data-i="${i}">${tp}<button data-rm="${i}">×</button></span>`).join('');
  return `<input type="checkbox" class="keep" disabled aria-label="keep">
    <div>
      <div class="tagrow">
        <select class="esel" data-f="category">${catOpts}</select>
        <select class="esel" data-f="confidence">${confOpts}</select>
        <span class="src">⌖ ${src}</span>
      </div>
      <h3 class="efield" contenteditable="true" data-f="title">${e.title}</h3>
      <p class="detail efield" contenteditable="true" data-f="detail">${e.detail}</p>
      <blockquote class="quote efield" contenteditable="true" data-f="quote">${e.quote}</blockquote>
      <div class="topics" data-topics-edit>${chips}<input class="topic-add" placeholder="+ topic" /></div>
    </div>`;
}
function wireEdit(card,id){
  const e=REVIEW.edits[id];
  card.querySelectorAll('.efield').forEach(el=>{
    el.addEventListener('click',ev=>ev.stopPropagation());
    el.addEventListener('input',()=>{e[el.dataset.f]=el.textContent;commitReviewChange();});});
  card.querySelectorAll('.esel').forEach(sel=>{
    sel.addEventListener('click',ev=>ev.stopPropagation());
    sel.addEventListener('change',()=>{e[sel.dataset.f]=sel.value;commitReviewChange();});});
  const tw=card.querySelector('[data-topics-edit]');
  tw.addEventListener('click',ev=>{ev.stopPropagation();
    const rm=ev.target.getAttribute('data-rm');
    if(rm!==null){e.topics.splice(+rm,1);redrawTopics(card,id);commitReviewChange();}});
  const add=tw.querySelector('.topic-add');
  add.addEventListener('keydown',ev=>{ev.stopPropagation();
    if(ev.key==='Enter'&&nonEmpty(add.value)){e.topics.push(add.value.trim());add.value='';
      redrawTopics(card,id);commitReviewChange();}});
}
function redrawTopics(card,id){
  const e=REVIEW.edits[id],tw=card.querySelector('[data-topics-edit]');
  const chips=(e.topics||[]).map((tp,i)=>`<span class="topic echip" data-i="${i}">${tp}<button data-rm="${i}">×</button></span>`).join('');
  tw.innerHTML=chips+'<input class="topic-add" placeholder="+ topic" />';
  const add=tw.querySelector('.topic-add');
  add.addEventListener('keydown',ev=>{ev.stopPropagation();
    if(ev.key==='Enter'&&nonEmpty(add.value)){e.topics.push(add.value.trim());add.value='';
      redrawTopics(card,id);commitReviewChange();}});
}
function commitEdit(id){
  // prune unchanged fields so the packet only carries real edits
  const ch=changedFields(id);
  if(Object.keys(ch).length===0)delete REVIEW.edits[id];else REVIEW.edits[id]=ch;
  rerenderCard(id);commitReviewChange();
}
```

- [ ] **Step 5: Run the test to verify it passes**

Reload. Confirm tools attach and editing round-trips:
```js
preview_eval: (function(){ const c=document.getElementById('c-idea-04'); return {hasTools:!!c.querySelector('.cardtools'), hasRerender:typeof rerenderCard}; })()
```
Expected: `{hasTools:true, hasRerender:"function"}`.
Then drive an edit: `preview_eval: enterEdit('idea-04')`, then
```js
preview_eval: (function(){ const h=document.querySelector('#c-idea-04 h3'); h.textContent='Rename Delete → Delete content (edited)'; h.dispatchEvent(new Event('input')); commitEdit('idea-04'); const p=buildPacket(); return {tally:document.getElementById('review-tally').textContent, card:p.cards&&p.cards[0]}; })()
```
Expected: `tally` starts with `1 edits`, and `p.cards[0]` = `{id:"idea-04", edits:{title:"Rename Delete → Delete content (edited)"}}`. `preview_screenshot` a card mid-edit to confirm the dashed-underline fields + dropdowns + `✓ Done` match the paper/ink style.

- [ ] **Step 6: Commit**

```bash
git add assets/template.html
git commit -m "feat(review): hover card tools + in-place field editing"
```

---

### Task 3: Cut card → packet `cut`

Wires the `✕ Cut` tool button to toggle a card's cut state (struck-through + dimmed, persistent `cut` flag), reflected in the tally and packet.

**Files:**
- Modify: `assets/template.html` (CSS after Task-2 block; `attachCardTools` click handler from Task 2; new `toggleCut` JS)

**Interfaces:**
- Consumes (from Task 2): `attachCardTools`, `applyCardState`, `rerenderCard`, `REVIEW`, `commitReviewChange`
- Produces: `function toggleCut(id)`; CSS class `.card.cut`

- [ ] **Step 1: Write the failing test**

Load template. Run:
```js
preview_eval: (function(){ toggleCut('idea-11'); const c=document.getElementById('c-idea-11'); return {fn:typeof toggleCut, cut:c.classList.contains('cut'), packet:buildPacket().cards}; })()
```
Expected NOW (fails): `toggleCut` is `"undefined"` (ReferenceError) — i.e. the function does not exist.

- [ ] **Step 2: Add cut CSS**

After the Task-2 CSS, add:
```css
  .card.cut{opacity:.5}
  .card.cut h3,.card.cut .detail,.card.cut .quote{text-decoration:line-through;
    text-decoration-color:var(--mark)}
```

- [ ] **Step 3: Wire the Cut button + add toggleCut**

In `attachCardTools` (Task 2), change the button click handler block:
```js
    if(k==='edit')enterEdit(it.id);}));
```
to:
```js
    if(k==='edit')enterEdit(it.id);
    else if(k==='cut')toggleCut(it.id);}));
```

Then add this function after `commitEdit` (Task 2):
```js
function toggleCut(id){
  if(REVIEW.cuts[id])delete REVIEW.cuts[id];else REVIEW.cuts[id]=true;
  const card=document.getElementById('c-'+id);
  card.classList.toggle('cut',!!REVIEW.cuts[id]);
  applyCardState(card,id);commitReviewChange();}
```

- [ ] **Step 4: Run the test to verify it passes**

Reload. Run the Step-1 snippet again. Expected: `{fn:"function", cut:true, packet:[{id:"idea-11", cut:true}]}`. Run it once more to confirm toggling off removes it from the packet (`packet` becomes `undefined`). `preview_screenshot` the cut card to confirm struck-through + dimmed + the `cut` flag chip.

- [ ] **Step 5: Commit**

```bash
git add assets/template.html
git commit -m "feat(review): cut card → packet removal signal"
```

---

### Task 4: Card comment + report-wide (masthead) comment

Adds the `💬 Comment` flow on cards (writes `REVIEW.notes[id]`) and a single report-wide comment attached to the masthead (`REVIEW.reportNote`), both with persistent markers.

**Files:**
- Modify: `assets/template.html` (CSS after Task-3 block; masthead markup ~line 181–197; `attachCardTools` handler; new comment JS)

**Interfaces:**
- Consumes: `attachCardTools`, `applyCardState`, `REVIEW`, `commitReviewChange`, `nonEmpty`
- Produces:
  - `function commentField(initial,onChange,placeholder)` → returns a wired textarea wrapper `<div class="cmt">`
  - `function toggleCardComment(id)`
  - CSS classes `.cmt`, `.cmt-in`, `.mast-cmt`

- [ ] **Step 1: Write the failing test**

Load template. Run:
```js
preview_eval: (function(){ return {fn:typeof commentField, mastBtn: !!document.querySelector('[data-act="report-note"]')}; })()
```
Expected NOW (fails): `{fn:"undefined", mastBtn:false}`.

- [ ] **Step 2: Add comment CSS**

After the Task-3 CSS, add:
```css
  .cmt{margin-top:10px}
  .cmt-in{width:100%;min-height:54px;border:1px solid var(--amber);border-radius:8px;
    padding:8px 10px;font:inherit;font-size:13px;background:#FBF7EC;resize:vertical;color:var(--ink)}
  .cmt-in::placeholder{color:var(--ink-soft)}
  .mast-cmt{margin:10px 0 0}
  .mast-note-btn{background:none;border:1px solid var(--rule);border-radius:7px;
    font:inherit;font-size:12px;padding:4px 10px;cursor:pointer;color:var(--ink-soft)}
  .mast-note-btn:hover{border-color:var(--ink);color:var(--ink)}
  .mast-note-btn.on{background:var(--mark);color:#fff;border-color:var(--mark)}
```

- [ ] **Step 3: Add the shared comment-field helper + card comment**

After `toggleCut` (Task 3), add:
```js
function commentField(initial,onChange,placeholder){
  const wrap=document.createElement('div');wrap.className='cmt';
  const ta=document.createElement('textarea');ta.className='cmt-in';
  ta.value=initial||'';ta.placeholder=placeholder||'Comment for Claude…';
  ta.addEventListener('click',e=>e.stopPropagation());
  ta.addEventListener('input',()=>onChange(ta.value));
  wrap.appendChild(ta);return wrap;
}
function toggleCardComment(id){
  const card=document.getElementById('c-'+id);
  const host=card.querySelector(':scope > div'); // the card body <div> from cardHTML
  let box=host.querySelector(':scope > .cmt');
  if(box){const ta=box.querySelector('.cmt-in');ta.focus();return;}
  box=commentField(REVIEW.notes[id]||'',v=>{REVIEW.notes[id]=v;applyCardState(card,id);commitReviewChange();},'What should change about this insight? (merge, re-scope, wrong speaker…)');
  host.appendChild(box);box.querySelector('.cmt-in').focus();
}
```
And extend the `attachCardTools` handler (Task 2/3) to handle comment:
```js
    if(k==='edit')enterEdit(it.id);
    else if(k==='cut')toggleCut(it.id);
    else if(k==='comment')toggleCardComment(it.id);}));
```
Note: `applyCardState` already re-creates the `.flags` row; when a card has a saved note its `comment` flag shows even after the box is closed/reopened on rerender. Because `rerenderCard` wipes the body, persist by re-opening the box in `applyCardState` is **not** wanted — instead the saved note survives in `REVIEW.notes` and the `💬 Comment` button re-opens it pre-filled. The `comment` flag chip is the persistent marker.

- [ ] **Step 4: Add the masthead report-wide comment**

In the masthead, immediately after the `.meta` div (closes ~line 196), before `</header>`, add:
```html
    <div class="mast-cmt">
      <button class="mast-note-btn" data-act="report-note" onclick="toggleReportNote(this)">💬 Comment on the whole report</button>
    </div>
```
And add the JS after `toggleCardComment`:
```js
function toggleReportNote(btn){
  const host=btn.parentElement;let box=host.querySelector('.cmt');
  if(box){box.querySelector('.cmt-in').focus();return;}
  box=commentField(REVIEW.reportNote,v=>{REVIEW.reportNote=v;
    btn.classList.toggle('on',nonEmpty(v));commitReviewChange();},
    'Overall direction: too many cards, wrong framing, merge these two…');
  host.appendChild(box);box.querySelector('.cmt-in').focus();
}
```

- [ ] **Step 5: Run the test to verify it passes**

Reload. Run:
```js
preview_eval: (function(){ toggleCardComment('idea-01'); const ta=document.querySelector('#c-idea-01 .cmt-in'); ta.value='merge with idea-05'; ta.dispatchEvent(new Event('input')); toggleReportNote(document.querySelector('[data-act="report-note"]')); const rta=document.querySelector('.mast-cmt .cmt-in'); rta.value='too many naming cards'; rta.dispatchEvent(new Event('input')); return {tally:document.getElementById('review-tally').textContent, p:buildPacket()}; })()
```
Expected: tally shows `2 comments`; packet has `report_note:"too many naming cards"` and `cards:[{id:"idea-01", note:"merge with idea-05"}]`. Confirm the `comment` flag chip stays on `idea-01` after `preview_eval: rerenderCard('idea-01')`. Screenshot a card with an open comment box.

- [ ] **Step 6: Commit**

```bash
git add assets/template.html
git commit -m "feat(review): card comments + report-wide note"
```

---

### Task 5: Repair-entry, repair-section, and transcript-turn comments

Adds `💬 Comment` hover affordances to repair-log rows, the repair-section headers, and transcript turns, each writing into the matching `REVIEW` bucket.

**Files:**
- Modify: `assets/template.html` (CSS after Task-4 block; `repSection` render ~line 613–621; the transcript render loop ~line 546–553; new JS)

**Interfaces:**
- Consumes: `commentField`, `REVIEW`, `commitReviewChange`, `nonEmpty`, `SPK`, `TURNS`
- Produces: `function toggleRepairComment(bucket,orig,hostRow)`, `function toggleSectionComment(bucket,host)`, `function toggleTurnComment(i,hostTurn)`; CSS `.rep`/`.turn` hover-tool styles

- [ ] **Step 1: Write the failing test**

Load template, switch to the Repair log tab (`preview_eval: showTab('rep')`). Run:
```js
preview_eval: (function(){ return {repTool: !!document.querySelector('.rep .rowtool'), turnTool: typeof toggleTurnComment}; })()
```
Expected NOW (fails): `{repTool:false, turnTool:"undefined"}`.

- [ ] **Step 2: Add hover-tool CSS for rows/turns/sections**

After the Task-4 CSS, add:
```css
  .rep{position:relative} .turn{position:relative}
  .rowtool{position:absolute;top:4px;right:4px;opacity:0;transition:opacity .12s;
    background:var(--paper);border:1px solid var(--rule);border-radius:6px;
    font:inherit;font-size:10.5px;color:var(--ink-soft);padding:3px 7px;cursor:pointer;z-index:2}
  .rep:hover .rowtool,.turn:hover .rowtool{opacity:1}
  .rowtool.on{background:var(--mark);color:#fff;border-color:var(--mark);opacity:1}
  .repsec h2{position:relative}
  .sectool{margin-left:10px;font:inherit;font-size:11px;border:1px solid var(--rule);
    border-radius:6px;color:var(--ink-soft);padding:2px 8px;cursor:pointer;text-transform:none;letter-spacing:0}
  .sectool.on{background:var(--mark);color:#fff;border-color:var(--mark)}
  .cmt.inline{margin:6px 0 2px}
```

- [ ] **Step 3: Render repair rows + section headers with comment affordances**

Replace the existing `repSection` function (~line 613–621):
```js
function repSection(title,arr,bucket){
  const sec=document.createElement('div');sec.className='repsec';
  const rows=arr.map(([o,f])=>{
    if(bucket==='query')return `<div class="rep"><span class="b query">query</span><span class="orig mono">${o}</span><span class="arrow">→</span><span class="qtext">${f}</span></div>`;
    const fix=f==='__DROP__'?`<span class="fix drop mono">[dropped — fragments]</span>`:`<span class="fix mono">${f}</span>`;
    return `<div class="rep"><span class="b ${bucket}">${bucket}</span><span class="orig mono">${o}</span><span class="arrow">→</span>${fix}</div>`;
  }).join('');
  sec.innerHTML=`<h2>${title} <button class="sectool" data-bucket="${bucket}">💬 comment on this section</button></h2>${rows}`;
  repEl.appendChild(sec);
  // section comment
  sec.querySelector('.sectool').addEventListener('click',e=>toggleSectionComment(bucket,sec));
  // per-row comment tools
  sec.querySelectorAll('.rep').forEach((row,i)=>{
    const orig=arr[i][0];
    const btn=document.createElement('button');btn.className='rowtool';btn.textContent='💬';
    btn.title='Comment on this repair';
    btn.addEventListener('click',()=>toggleRepairComment(bucket,orig,row));
    row.appendChild(btn);
  });
}
```

- [ ] **Step 4: Add repair + section comment JS**

After the Task-4 JS (`toggleReportNote`), add:
```js
function repairKey(bucket,orig){return bucket+' '+orig;}
function toggleRepairComment(bucket,orig,row){
  let box=row.querySelector(':scope > .cmt');
  if(box){box.querySelector('.cmt-in').focus();return;}
  const key=repairKey(bucket,orig);const btn=row.querySelector('.rowtool');
  box=commentField(REVIEW.repairComments[key]||'',v=>{REVIEW.repairComments[key]=v;
    btn.classList.toggle('on',nonEmpty(v));commitReviewChange();},'Comment on this repair (e.g. leave as-is, wrong fix)…');
  box.classList.add('inline');row.appendChild(box);box.querySelector('.cmt-in').focus();
  btn.classList.toggle('on',nonEmpty(REVIEW.repairComments[key]));
}
function toggleSectionComment(bucket,sec){
  let box=sec.querySelector(':scope > .cmt');const btn=sec.querySelector('.sectool');
  if(box){box.querySelector('.cmt-in').focus();return;}
  // section note is keyed by a sentinel orig so it rides the same repairs bucket logic? No —
  // repair_section_note in the packet is a single field; we store the *query* section note there.
  // The spec ties "repair-log section as a whole" to one note: REVIEW.repairSectionNote.
  box=commentField(REVIEW.repairSectionNote,v=>{REVIEW.repairSectionNote=v;
    btn.classList.toggle('on',nonEmpty(v));commitReviewChange();},'Comment on the repair log as a whole…');
  box.classList.add('inline');sec.appendChild(box);box.querySelector('.cmt-in').focus();
}
```

Note on scope: the spec's packet carries exactly one `repair_section_note`. All three section headers share it (whichever you type in is the section-wide note); the per-row comments are independent and keyed per `bucket+orig`. Keep one shared section note rather than three — the packet field is singular.

- [ ] **Step 5: Render transcript turns with a comment tool**

Replace the existing transcript render loop (~line 546–553):
```js
TURNS.forEach((t,i)=>{
  const d=document.createElement('div');
  d.className='turn '+t[0]+(turnToIdeas[i]?' anchored':'');
  d.id='t-'+i;
  d.innerHTML=`<div class="meta-r"><span class="spk">${SPK[t[0]]}</span><span class="ts mono">${t[1]}</span></div><span class="txt">${t[2]}</span>`;
  if(turnToIdeas[i]) d.addEventListener('click',e=>{ if(e.target.classList.contains('unsure'))return; locate(turnToIdeas[i][0],true); });
  const btn=document.createElement('button');btn.className='rowtool';btn.textContent='💬';
  btn.title='Comment on this line';
  btn.addEventListener('click',e=>{e.stopPropagation();toggleTurnComment(i,d);});
  d.appendChild(btn);
  scriptEl.appendChild(d);
});
```
And add the JS after `toggleSectionComment`:
```js
function toggleTurnComment(i,turn){
  let box=turn.querySelector(':scope > .cmt');const btn=turn.querySelector('.rowtool');
  if(box){box.querySelector('.cmt-in').focus();return;}
  box=commentField(REVIEW.turnComments[i]||'',v=>{REVIEW.turnComments[i]=v;
    btn.classList.toggle('on',nonEmpty(v));commitReviewChange();},'Comment on this line (e.g. wrong speaker, misattributed)…');
  box.classList.add('inline');turn.appendChild(box);box.querySelector('.cmt-in').focus();
}
```

- [ ] **Step 6: Run the test to verify it passes**

Reload. Switch to Repair log (`preview_eval: showTab('rep')`), then:
```js
preview_eval: (function(){ const row=document.querySelector('.repsec .rep'); toggleRepairComment(row.querySelector('.b').textContent, row.querySelector('.orig').textContent, row); const ta=row.querySelector('.cmt-in'); ta.value='leave as-is'; ta.dispatchEvent(new Event('input')); return {p:buildPacket().repairs}; })()
```
Expected: `p[0]` = `{bucket:"auto", orig:"<that row's orig text>", comment:"leave as-is"}`.
Then test a turn comment (switch to ideas tab is not required; turns exist in DOM):
```js
preview_eval: (function(){ const turn=document.getElementById('t-9'); toggleTurnComment(9,turn); const ta=turn.querySelector('.cmt-in'); ta.value='this is Bogdan, not the participant'; ta.dispatchEvent(new Event('input')); return buildPacket().turns; })()
```
Expected: `[{i:9, comment:"this is Bogdan, not the participant"}]`. Screenshot a repair row and a transcript turn with the hover `💬` and an open comment box.

- [ ] **Step 7: Commit**

```bash
git add assets/template.html
git commit -m "feat(review): repair-entry, repair-section, and transcript-turn comments"
```

---

### Task 6: SKILL.md + "How this works" diagram

Documents the protected new surface and the ingestion side (Phase 3), and promotes the two review lanes in the diagram from `future` (dashed) to `Now` (solid).

**Files:**
- Modify: `SKILL.md` (the "one rule that prevents drift" region list ~line 84–116; add "Phase 3 — Fold in review" after the "Clarification pass" section ~line 235)
- Modify: `assets/template.html` (`<section id="view-how">` ~line 311–344)

**Interfaces:** none (docs + static markup).

- [ ] **Step 1: Write the failing check**

```bash
grep -c "Phase 3 — Fold in review" /Users/bogdandraghici/.claude/skills/meetinginsights/SKILL.md
grep -c "lane-row future" /Users/bogdandraghici/.claude/skills/meetinginsights/assets/template.html
```
Expected NOW: first prints `0`; second prints `3` (the three current `future` lanes).

- [ ] **Step 2: Extend the drift-rule region list in SKILL.md**

In the paragraph beginning "Everything else — the three pill tabs …" (~line 85), append to the protected-surface list a sentence:
```
Also protected now: the **review round-trip** machinery — the hover action
buttons on cards/repairs/turns/masthead (`✎ Edit` / `💬 Comment` / `✕ Cut`), the
in-place edit fields, the comment boxes, the cut state, the toolbar
edits/comments/cut tally, and the `Send to Claude ↑` packet panel (`#reviewPanel`,
`buildPacket`). These are part of the template; preserve them byte-for-byte like
the tabs and filters. They are pure presentation/serialization — never session data.
```

- [ ] **Step 3: Add the "Phase 3 — Fold in review" section to SKILL.md**

Immediately after the "Clarification pass — one question at a time" section (ends ~line 235, before "## Asset paths"), insert:
```markdown
## Phase 3 — Fold in review

After the report is delivered, the user can edit insight-card fields, comment on
any section, and cut cards directly in the HTML, then hit **`Send to Claude ↑`** to
produce a **review packet** (JSON by default; Markdown mirror). When the user pastes
one back:

1. Parse it. Confirm `session` matches the report you built. The packet carries only
   what changed — untouched cards/repairs/turns are omitted. An **empty packet**
   (just `{session}`) means no changes: say so and leave the report as-is.
2. Apply it onto the working data:
   - `cards[].edits` — overwrite those exact fields on the matching `IDEAS` entry
     (`title`, `detail`, `quote`, `category`, `confidence`, `topics`).
   - `cards[].cut:true` — drop that idea entirely.
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
```

- [ ] **Step 4: Promote the review lanes in the diagram (template)**

In `assets/template.html`, the diagram has, in order: a `<div class="next-rule">…Next · planned…</div>` separator (~line 311) followed by three `<div class="lane-row future">` blocks (Review/edit, Folds-in, Publishes-to-Notion). Restructure so the first two become solid "Now" lanes and only Notion stays under "Next":

1. **Delete** the `<div class="next-rule">…</div>` element at ~line 311 (it will be re-inserted lower).
2. On the **"Review, edit & classify"** lane (~line 313) and the **"Folds in your changes"** lane (~line 324), remove the ` future` class so each is just `<div class="lane-row">`.
3. **Insert** the `next-rule` separator *immediately before* the **"Publishes to Notion"** lane (~line 335):
```html
      <div class="next-rule"><div class="line"></div><span class="lbl">Next · planned, not yet built</span><div class="line"></div></div>
```
4. Leave the "Publishes to Notion" lane as `<div class="lane-row future">`.
5. Update the intro `<p class="hint">` (~line 263) — change "The first steps run inside this tool today; the rest are planned and not yet built." to "The review loop now runs inside this tool too; only the final Notion publish is planned and not yet built."
6. On the **"Folds in your changes"** card, update its `<p>` copy to present tense: "Claude reads your edits, comments, and cuts from the packet you send back, then rebuilds the report with them folded in — resolving open queries and dropping cut cards."

- [ ] **Step 5: Run the checks to verify they pass**

```bash
grep -c "Phase 3 — Fold in review" /Users/bogdandraghici/.claude/skills/meetinginsights/SKILL.md
grep -c "lane-row future" /Users/bogdandraghici/.claude/skills/meetinginsights/assets/template.html
```
Expected: first prints `1`; second prints `1` (only the Notion lane remains `future`).
Then load the template, `preview_eval: showTab('how')`, and `preview_screenshot` to confirm two solid review lanes under "Now" and a single dashed Notion lane under "Next".

- [ ] **Step 6: Commit**

```bash
git add SKILL.md assets/template.html
git commit -m "docs(review): document Phase 3 fold-in + promote review lanes in diagram"
```

---

### Task 7: End-to-end packet validation + drift guard

A final integration pass: exercise every affordance in one session, confirm the assembled packet round-trips as valid JSON with every field type, and confirm an untouched report produces an empty packet (drift guard).

**Files:** none modified (verification only). If issues are found, fix in the relevant task's file.

- [ ] **Step 1: Full-session exercise**

Load the template. In one preview session: edit a card field, cut another card, add a card note, set the report note, comment a repair row, set the repair-section note, comment a transcript turn. Then:
```js
preview_eval: (function(){ const p=buildPacket(); return {valid: (JSON.parse(JSON.stringify(p)), true), keys:Object.keys(p), counts:packetCounts()}; })()
```
Expected: `valid:true`; `keys` includes `session, report_note, cards, repairs, repair_section_note, turns`; counts match what you entered.

- [ ] **Step 2: Empty-packet drift guard**

Reload (fresh state). Run:
```js
preview_eval: (function(){ return {p:buildPacket(), btn:document.getElementById('sendReview').disabled, tally:document.getElementById('review-tally').textContent}; })()
```
Expected: `p` equals `{session:"kb-export-2026-06-17"}`, `btn:true`, `tally:"0 edits · 0 comments · 0 cut"`.

- [ ] **Step 3: Existing behavior intact**

Confirm the original tool still works untouched: `preview_eval` to toggle a keep checkbox and `openExport()`, verifying the kept-ideas Markdown still renders; click a card to confirm `locate()` still highlights transcript lines; switch all three tabs. Screenshot the ideas view in its default (no-hover) state to confirm it is visually unchanged from before this feature.

- [ ] **Step 4: Markdown mirror**

`preview_eval: setReviewFmt('md'); openReview();` and confirm `#reviewBox` renders the human-readable Markdown form of the packet.

- [ ] **Step 5: Commit (if any fixes were made)**

```bash
git add -A
git commit -m "test(review): end-to-end packet validation + drift guard"
```
(If no fixes were needed, skip the commit.)

---

## Self-review

**Spec coverage:**
- Hover-reveal buttons (card/repair/section/turn/masthead) → Tasks 2 (card), 4 (masthead), 5 (repair/section/turn). ✓
- Edit fields (title/detail/quote/category/confidence/topics) → Task 2. ✓
- Per-card note → Task 4. ✓
- Cut control (separate from keep) → Task 3. ✓
- Comment surfaces: report-wide, per-repair, repair-section, per-turn → Tasks 4 & 5. ✓
- Persistent markers + toolbar tally + Send button → Tasks 1 (tally/send), 2–5 (flags/on-state). ✓
- Review packet (JSON default + MD mirror; only-changed; empty = no-op) → Task 1 (`buildPacket`/`packetToMd`), Task 7 (validation). ✓
- Packet keying (repairs by bucket+orig, turns by index) → Tasks 1 & 5. ✓
- SKILL.md drift rule + regions + Phase 3 → Task 6. ✓
- "How this works" lanes promoted → Task 6. ✓
- "Export kept" / keep checkbox untouched → preserved (Task 7 Step 3 verifies). ✓

**Placeholder scan:** No TBD/TODO; every code step shows complete code; verification steps give exact expected output. ✓

**Type/name consistency:** `REVIEW`, `ORIG`, `effective`, `changedFields`, `buildPacket`, `packetCounts`, `renderTally`, `commitReviewChange`, `rerenderCard`, `attachCardTools`, `applyCardState`, `enterEdit`/`commitEdit`, `toggleCut`, `commentField`, `toggleCardComment`, `toggleReportNote`, `toggleRepairComment`, `toggleSectionComment`, `toggleTurnComment`, `repairKey` — each defined once and referenced consistently. Packet field names (`session`, `report_note`, `cards`, `edits`, `cut`, `note`, `repairs`, `bucket`, `orig`, `comment`, `repair_section_note`, `turns`, `i`) match the spec's example byte-for-byte. ✓
