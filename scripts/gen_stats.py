#!/usr/bin/env python3
"""Generates assets/gh_languages.svg (a number-free language distribution chart) from your public repos.
No tokens or dependencies needed (standard library + git). Run:  python scripts/gen_stats.py
Set GH_USER to override the username."""
import os, re, math, html, shutil, subprocess, tempfile, datetime as dt, urllib.request
from pathlib import Path

USER = os.environ.get("GH_USER", "Hetvi-codes")
OUT = Path(__file__).resolve().parent.parent / "assets"
HDR = {"User-Agent": "Mozilla/5.0 (profile-stats-generator)"}
MONO = "ui-monospace,'SF Mono','JetBrains Mono','Fira Code',Menlo,Consolas,'DejaVu Sans Mono',monospace"

def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=30).read().decode("utf-8", "replace")

# ---------------------------------------------------------------- data
def repos():
    out, page = [], 1
    while True:
        h = fetch(f"https://github.com/{USER}?tab=repositories&page={page}")
        blocks = re.split(r'<li[^>]*itemprop="owns"', h)[1:]
        new = 0
        for b in blocks:
            n = re.search(r'itemprop="name codeRepository"[^>]*>\s*([^<]+?)\s*<', b)
            if not n or any(r["name"] == n.group(1) for r in out): continue
            st = re.search(r'/stargazers"[^>]*>(.*?)</a>', b, re.S)
            stars = re.sub(r'<[^>]+>|[\s,]', '', st.group(1)) if st else "0"
            out.append(dict(name=n.group(1), fork="Forked from" in b, stars=int(stars) if stars.isdigit() else 0)); new += 1
        if not new or page >= 10: break
        page += 1
    return out

EXT = {".py":"Python",".js":"JavaScript",".jsx":"JavaScript",".mjs":"JavaScript",".ts":"TypeScript",".tsx":"TypeScript",
       ".java":"Java",".html":"HTML",".htm":"HTML",".css":"CSS",".scss":"SCSS",".c":"C",".h":"C",".cpp":"C++",".cc":"C++",
       ".hpp":"C++",".ino":"C++",".sh":"Shell",".sql":"SQL",".kt":"Kotlin",".go":"Go",".rs":"Rust",".php":"PHP",".rb":"Ruby",".cs":"C#"}
COLORS = {"Python":"#3572A5","JavaScript":"#F1E05A","TypeScript":"#3178C6","Java":"#B07219","HTML":"#E34C26","CSS":"#9B6BDF",
          "SCSS":"#C6538C","C":"#7A7A7A","C++":"#F34B7D","Shell":"#89E051","SQL":"#E38C00","Kotlin":"#A97BFF","Go":"#00ADD8",
          "Rust":"#DEA584","PHP":"#4F5D95","Ruby":"#701516","C#":"#178600","Other":"#A1A1AA"}
SKIP = {".git","node_modules","venv",".venv","env","dist","build","__pycache__","vendor","site-packages",".next","target"}

def language_bytes(names):
    totals = {}
    tmp = tempfile.mkdtemp()
    try:
        for n in names:
            dest = os.path.join(tmp, n)
            r = subprocess.run(["git", "clone", "--depth", "1", "-q", f"https://github.com/{USER}/{n}.git", dest],
                               env={**os.environ, "GIT_TERMINAL_PROMPT": "0"}, capture_output=True, timeout=180)
            if r.returncode != 0: continue
            for root, dirs, files in os.walk(dest):
                dirs[:] = [d for d in dirs if d not in SKIP]
                for f in files:
                    lang = EXT.get(os.path.splitext(f)[1].lower())
                    if not lang or f.endswith(".min.js"): continue
                    try: size = os.path.getsize(os.path.join(root, f))
                    except OSError: continue
                    if size < 1_500_000: totals[lang] = totals.get(lang, 0) + size
            shutil.rmtree(dest, ignore_errors=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return totals

# ---------------------------------------------------------------- svg helpers
CSS = """
:root{--card:#FFFFFF;--fg:#18181B;--dim:#71717A;--line:#E4E4E7;--acc:#6D5EF5}
@media (prefers-color-scheme:dark){:root{--card:#0F0F14;--fg:#EDEDF0;--dim:#8B8B97;--line:#26262F;--acc:#9A8CFF}}
text{font-family:MONO;white-space:pre}
.fg{fill:var(--fg)}.dim{fill:var(--dim)}.acc{fill:var(--acc)}
.card{fill:var(--card);stroke:var(--line);stroke-width:1.5}
.rule{stroke:var(--line);stroke-width:1.5}
.dr{animation:dr 1.3s cubic-bezier(.2,.8,.2,1) both}
@keyframes dr{from{stroke-dasharray:0 999}}
""".replace("MONO", MONO)

def esc(s): return html.escape(str(s), quote=False)
def head(W, H, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="{html.escape(label, quote=True)}"><style>{CSS}</style>')
def chrome(W, H, title):
    s = f'<rect class="card" x="1" y="1" width="{W-2}" height="{H-2}" rx="12"/>'
    for i, (f, st) in enumerate([("#FF5F57","#E0443E"),("#FEBC2E","#DEA123"),("#28C840","#1AAB29")]):
        s += f'<circle cx="{22+i*20}" cy="22" r="6" fill="{f}" stroke="{st}" stroke-width=".7"/>'
    s += f'<text class="dim" x="{W/2}" y="26" font-size="12" text-anchor="middle">{esc(title)}</text>'
    s += f'<line class="rule" x1="1" y1="44" x2="{W-1}" y2="44"/>'
    return s

def languages_svg(totals):
    W = 900
    items = sorted(totals.items(), key=lambda kv: -kv[1])
    total = sum(v for _, v in items) or 1
    if len(items) > 6:
        other = sum(v for _, v in items[5:]); items = items[:5] + [("Other", other)]
    H = 230
    s = [head(W, H, "Language distribution: " + ", ".join(k for k, _ in items))]
    s.append(chrome(W, H, "languages --sort most-used"))
    cx, cy, r, sw = 310, 137, 54, 22
    C = 2 * math.pi * r
    s.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="var(--line)" stroke-width="{sw}"/>')
    off = 0
    for k, v in items:
        seg = v / total * C
        gap = 2.0 if len(items) > 1 else 0
        s.append(f'<circle class="dr" cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{COLORS.get(k, "#A1A1AA")}" stroke-width="{sw}" '
                 f'stroke-dasharray="{max(seg-gap,0.1):.2f} {C:.2f}" stroke-dashoffset="{-off:.2f}" transform="rotate(-90 {cx} {cy})"/>')
        off += seg
    s.append(f'<text class="acc" x="{cx}" y="{cy+6}" font-size="20" font-weight="700" text-anchor="middle">&lt;/&gt;</text>')
    s.append('<text x="460" y="78" font-size="12"><tspan class="acc">$</tspan><tspan class="dim"> what I code most</tspan></text>')
    for i, (k, v) in enumerate(items):
        y = 108 + i * 24
        col = COLORS.get(k, "#A1A1AA")
        s.append(f'<circle cx="466" cy="{y-4}" r="5" fill="{col}"/>')
        s.append(f'<text class="fg" x="482" y="{y}" font-size="13" font-weight="700">{esc(k)}</text>')
    s.append('</svg>')
    return "".join(s)

def main():
    OUT.mkdir(exist_ok=True)
    rl = [r for r in repos() if not r["fork"]]
    tot = language_bytes([r["name"] for r in rl])
    (OUT / "gh_languages.svg").write_text(languages_svg(tot), encoding="utf-8")
    print("repos", len(rl), {k: v for k, v in sorted(tot.items(), key=lambda kv: -kv[1])})

if __name__ == "__main__":
    main()
