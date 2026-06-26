#!/usr/bin/env python3
"""Publish a meetinginsights review-tool HTML to bogdandraghici/Testing and serve it
via GitHub Pages, listed on a topic-filterable index.

Usage:
    python3 scripts/publish.py <path-to-report.html> ["commit message"]

- Parses SESSION / IDEAS from the report (topics union + insight count + title).
- Shallow-clones the repo (initialises `main` if the repo is empty).
- Copies the report to sessions/<SESSION.id>.html, upserts sessions.json (keyed by id),
  regenerates index.html from assets/index-template.html, commits all three, pushes main.
- Enables GitHub Pages (root of main) if not already on, polls the session URL, and prints
  the session + index URLs on the last two stdout lines.

Requires an authenticated `gh` CLI.
"""
import sys, os, re, json, subprocess, tempfile, shutil, time, urllib.request

REPO = "bogdandraghici/Testing"
OWNER, NAME = REPO.split("/")
PAGES_BASE = f"https://{OWNER}.github.io/{NAME}"
HERE = os.path.dirname(os.path.abspath(__file__))
INDEX_TEMPLATE = os.path.join(HERE, "..", "assets", "index-template.html")


def die(msg):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def run(args, cwd=None, capture=False, check=True, stdin=None):
    return subprocess.run(args, cwd=cwd, check=check,
                          text=True, input=stdin,
                          stdout=(subprocess.PIPE if capture else None),
                          stderr=(subprocess.PIPE if capture else None))


def parse_report(path):
    html = open(path, encoding="utf-8").read()

    def block(pat):
        m = re.search(pat, html, re.S)
        return m.group(1) if m else None

    sess_raw = block(r"const SESSION=(\{.*?\});")
    ideas_raw = block(r"const IDEAS = (\[.*?\n\]);")
    if not sess_raw or not ideas_raw:
        die(f"could not find SESSION / IDEAS data blocks in {path} — is this a built report?")
    try:
        session = json.loads(sess_raw)
        ideas = json.loads(ideas_raw)
    except json.JSONDecodeError as e:
        die(f"report data blocks are not valid JSON: {e}")
    if not session.get("id"):
        die("SESSION has no id")

    h1 = block(r"<h1>(.*?)</h1>")
    title = None
    if h1:
        title = (h1.replace("&amp;", "&").replace("&lt;", "<")
                    .replace("&gt;", ">").replace("&quot;", '"').strip())

    topics = sorted({t for it in ideas for t in (it.get("topics") or [])})
    return {
        "id": session["id"],
        "title": title or session.get("feature") or session["id"],
        "feature": session.get("feature", ""),
        "date": session.get("date", ""),
        "participant": session.get("participant", ""),
        "file": f"sessions/{session['id']}.html",
        "topics": topics,
        "insights": len(ideas),
    }


def today():
    # SOURCE_DATE_EPOCH or fallback to git; avoid importing datetime.now for determinism notes
    out = run(["date", "+%Y-%m-%d"], capture=True).stdout.strip()
    return out


def render_index(sessions):
    tpl = open(INDEX_TEMPLATE, encoding="utf-8").read()
    data = json.dumps(sessions, ensure_ascii=False, indent=1)
    tpl = tpl.replace("/*__SESSIONS__*/[]", data, 1)
    tpl = tpl.replace("/*__GENERATED__*/", today(), 1)
    if "/*__SESSIONS__*/" in tpl:
        die("index template placeholder /*__SESSIONS__*/[] not found — template changed?")
    return tpl


def main():
    if len(sys.argv) < 2:
        die('usage: publish.py <path-to-report.html> ["commit message"]')
    src = sys.argv[1]
    if not os.path.isfile(src):
        die(f"file not found: {src}")
    if not src.endswith((".html", ".htm")):
        die(f"expected an .html report, got: {src}")

    entry = parse_report(src)
    msg = sys.argv[2] if len(sys.argv) > 2 else f"Publish session {entry['id']}"

    # auth check
    if run(["gh", "auth", "status"], capture=True, check=False).returncode != 0:
        die("gh is not authenticated — run `gh auth login` and retry.")

    work = tempfile.mkdtemp()
    try:
        repo = os.path.join(work, "repo")
        print(f"Cloning {REPO} ...", file=sys.stderr)
        run(["gh", "repo", "clone", REPO, repo, "--", "--depth=1", "--quiet"])

        # empty repo? no HEAD -> create main
        empty = run(["git", "rev-parse", "--verify", "HEAD"], cwd=repo,
                    capture=True, check=False).returncode != 0
        if empty:
            print("Repo is empty — initialising main ...", file=sys.stderr)
            run(["git", "checkout", "-b", "main"], cwd=repo)

        # upsert manifest
        mpath = os.path.join(repo, "sessions.json")
        sessions = []
        if os.path.isfile(mpath):
            try:
                sessions = json.load(open(mpath, encoding="utf-8"))
            except json.JSONDecodeError:
                sessions = []
        entry["published"] = today()
        sessions = [s for s in sessions if s.get("id") != entry["id"]] + [entry]
        sessions.sort(key=lambda s: s.get("date", ""), reverse=True)

        # write files
        os.makedirs(os.path.join(repo, "sessions"), exist_ok=True)
        shutil.copyfile(src, os.path.join(repo, "sessions", f"{entry['id']}.html"))
        json.dump(sessions, open(mpath, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        open(os.path.join(repo, "index.html"), "w", encoding="utf-8").write(
            render_index(sessions))

        run(["git", "add", "index.html", "sessions.json",
             f"sessions/{entry['id']}.html"], cwd=repo)
        staged = run(["git", "diff", "--cached", "--quiet"], cwd=repo, check=False).returncode
        if staged == 0:
            print("No changes — this session is already published and identical.", file=sys.stderr)
        else:
            run(["git", "commit", "--quiet", "-m", msg, "-m",
                 "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"], cwd=repo)
            push = ["git", "push", "--quiet"] + (
                ["-u", "origin", "main"] if empty else ["origin", "HEAD:main"])
            run(push, cwd=repo)
            print(f"Pushed to {REPO}@main.", file=sys.stderr)

        # ensure Pages enabled (root of main)
        pg = run(["gh", "api", f"repos/{REPO}/pages"], capture=True, check=False)
        if pg.returncode != 0:
            print("Enabling GitHub Pages (main /) ...", file=sys.stderr)
            run(["gh", "api", "-X", "POST", f"repos/{REPO}/pages", "--input", "-"],
                stdin=json.dumps({"source": {"branch": "main", "path": "/"}}),
                capture=True, check=False)

        session_url = f"{PAGES_BASE}/{entry['file']}"
        index_url = f"{PAGES_BASE}/"
        print("Waiting for GitHub Pages to serve the session ...", file=sys.stderr)
        code = 0
        for _ in range(15):
            try:
                with urllib.request.urlopen(session_url, timeout=10) as r:
                    code = r.status
                if code == 200:
                    break
            except Exception:
                code = 0
            time.sleep(8)

        print(f"{index_url}")
        print(f"{session_url}  (HTTP {code or 'pending'})")
        if code != 200:
            print("Note: not 200 yet — first Pages deploy can take ~30–90s; the URLs will go live shortly.",
                  file=sys.stderr)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
