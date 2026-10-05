#!/usr/bin/env python3
"""Build the DevilDriver static site from devildriver.json (notes model).

Usage: python3 build.py
- One page per category, generated automatically (new categories get pages free).
- Notes are the unit of knowledge: id, category, title, status, body, updated.
- Body markup: blank line = paragraph, lines starting with '- ' = bullets.
- prompts.html is composed from demon notes' data.image_prompt fields.
No dependencies.
"""
import json
import html
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
REPO_RAW = "https://raw.githubusercontent.com/Torres0990/devildriver-bible/main/devildriver.json"

if "--sync" in sys.argv[1:]:
    print("syncing devildriver.json from GitHub...")
    with urllib.request.urlopen(REPO_RAW, timeout=60) as resp:
        (HERE / "devildriver.json").write_bytes(resp.read())
    print("synced.")

DATA = json.loads((HERE / "devildriver.json").read_text())
CATS = DATA["categories"]
NOTES = DATA["notes"]

# Optional concept art per note id
ART = {
    "demon-samurai": [("assets/samurai-base.webp", "Samurai demon base form"),
                      ("assets/katana.webp", "Katana weapon asset")],
}

CSS = """
:root{--bg:#0d0d12;--panel:#16161f;--ink:#e8e6e1;--muted:#9a97a3;--red:#c1121f;--line:#2a2a38}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:860px;margin:0 auto;padding:24px 20px 64px}
nav.top{display:flex;gap:14px;flex-wrap:wrap;padding:14px 20px;background:#101018;border-bottom:1px solid var(--line);position:sticky;top:0}
nav.top a{color:var(--muted);text-decoration:none;font-weight:600}
nav.top a:hover,nav.top a.on{color:#fff}
nav.top .brand{color:var(--red);font-weight:800;letter-spacing:1px}
h1{font-size:2rem;margin:.4em 0}h2{margin-top:0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:14px 0}
.card h2{font-size:1.25rem}
.tag{display:inline-block;font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;border-radius:20px;padding:2px 10px;margin-right:8px}
.locked{background:#1d3a24;color:#7ee2a0}.decided{background:#3a2f14;color:#f0c96a}.open{background:#3a1a1a;color:#f08a8a}
.muted{color:var(--muted)}.noteid{font-size:.75rem;color:var(--muted)}
pre.prompt{background:#0a0a0f;border:1px solid var(--line);border-radius:8px;padding:14px;white-space:pre-wrap;font-size:.85rem;color:#d8d4c8}
button.copy{background:var(--red);color:#fff;border:0;border-radius:8px;padding:8px 16px;font-weight:700;cursor:pointer;margin-top:8px}
button.copy:hover{filter:brightness(1.15)}
footer{margin-top:48px;color:var(--muted);font-size:.85rem;border-top:1px solid var(--line);padding-top:16px}
footer code{background:#0a0a0f;padding:2px 6px;border-radius:4px}
img.art{max-width:100%;border-radius:10px;border:1px solid var(--line)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:640px){.grid2{grid-template-columns:1fr}}
ul.tight li{margin:.25em 0}
"""


def tag(status):
    return f'<span class="tag {status}">{status}</span>' if status in ("locked", "decided", "open") else ""


def render_body(body):
    """Tiny markup: paragraphs separated by blank lines, '- ' lines become bullets."""
    paras, bullets = [], []
    def flush():
        nonlocal paras, bullets
        if bullets:
            paras.append("<ul class='tight'>" + "".join(f"<li>{html.escape(b)}</li>" for b in bullets) + "</ul>")
            bullets = []
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("- "):
            bullets.append(s[2:])
        elif s == "":
            flush()
        else:
            flush()
            paras.append(f"<p>{html.escape(s)}</p>")
    flush()
    return "\n".join(paras)


def nav(active):
    links = "".join(
        f'<a href="{c["page"]}" class="{"on" if c["page"] == active else ""}">{html.escape(c["title"])}</a>'
        for c in CATS
    )
    return (f'<nav class="top"><span class="brand">DEVILDRIVER</span>{links}'
            f'<a href="prompts.html" class="{"on" if active == "prompts.html" else ""}">Prompt Lab</a>'
            f'<a href="devildriver.json">JSON</a><a href="llms.txt">llms.txt</a></nav>')


def note_card(n):
    art = ""
    if n["id"] in ART:
        imgs = "".join(
            f'<div><img class="art" src="{src}" alt="{html.escape(alt)}"><p class="muted">{html.escape(alt)}</p></div>'
            for src, alt in ART[n["id"]])
        art = f'<div class="grid2">{imgs}</div>'
    return f"""<div class="card">{tag(n.get('status'))}
<h2>{html.escape(n['title'])}</h2>
{art}
{render_body(n['body'])}
<p class="noteid">note: {html.escape(n['id'])} · updated {html.escape(n.get('updated',''))}</p>
</div>"""


def page(filename, title, desc, body):
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} — DevilDriver</title>
<meta name="description" content="{html.escape(desc or title)}">
<style>{CSS}</style></head>
<body>{nav(filename)}<div class="wrap">
<h1>{html.escape(title)}</h1>
{f'<p class="muted">{html.escape(desc)}</p>' if desc else ''}
{body}
<footer>DevilDriver design bible v{DATA['meta']['version']} — updated {DATA['meta']['updated']}.
Machine-readable: <code>/devildriver.json</code> · AI context + edit contract: <code>/llms.txt</code>.<br>
<span class="tag locked">locked</span> confirmed final · <span class="tag decided">decided</span> current direction · <span class="tag open">open</span> Sebastian decides.</footer>
</div>
<script>
document.querySelectorAll('button.copy').forEach(b=>b.addEventListener('click',()=>{{
  navigator.clipboard.writeText(document.getElementById(b.dataset.for).textContent);
  b.textContent='Copied';setTimeout(()=>b.textContent='Copy prompt',1200);
}}));
</script>
</body></html>"""


def build_llms():
    d = DATA
    L = [f"# {d['meta']['name']} (v{d['meta']['version']}, {d['meta']['updated']})", "",
         "## EDIT CONTRACT (AI contributors read first)", "",
         d["meta"]["edit_contract"], ""]
    for c in d["categories"]:
        L += ["", f"## {c['title']}"]
        for n in [x for x in NOTES if x["category"] == c["id"]]:
            L += ["", f"### {n['title']} [{n.get('status','')}] (note: {n['id']})", "", n["body"]]
    return "\n".join(L) + "\n"


def main():
    for c in CATS:
        notes = [n for n in NOTES if n["category"] == c["id"]]
        body = "\n".join(note_card(n) for n in notes) or '<p class="muted">No notes yet.</p>'
        (HERE / c["page"]).write_text(page(c["page"], c["title"], c.get("description"), body))
        print("wrote", c["page"], f"({len(notes)} notes)")
    # Prompt Lab from demon note data
    blocks = []
    for n in NOTES:
        data = n.get("data") or {}
        if data.get("image_prompt"):
            pid = "p-" + n["id"]
            blocks.append(f'<div class="card"><h2>{html.escape(n["title"])}</h2>'
                          f'<pre class="prompt" id="{pid}">{html.escape(data["image_prompt"])}</pre>'
                          f'<button class="copy" data-for="{pid}">Copy prompt</button></div>')
        kat = (data.get("weapons") or {}).get("katana_image_prompt")
        if kat:
            pid = "p-katana"
            blocks.append(f'<div class="card"><h2>Katana weapon asset</h2>'
                          f'<pre class="prompt" id="{pid}">{html.escape(kat)}</pre>'
                          f'<button class="copy" data-for="{pid}">Copy prompt</button></div>')
    (HERE / "prompts.html").write_text(
        page("prompts.html", "Prompt Lab",
             "Image prompts composed from the notes' structured fields. Copy, paste, generate.",
             "\n".join(blocks)))
    print("wrote prompts.html")
    (HERE / "llms.txt").write_text(build_llms())
    print("wrote llms.txt")


if __name__ == "__main__":
    main()
