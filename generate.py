#!/usr/bin/env python3
"""
generate.py - build the profile README and its SVG cards from public GitHub data.

Needs python-chess for the playable board (pip install chess); without it the
board section is left out. Run locally or from the workflows:

  python generate.py

Writes README.md and assets/*.svg next to this file.
"""

import base64
import datetime as dt
import json
import os
import re
import urllib.parse
import urllib.request
from collections import Counter
from html import escape

try:
    import chess_game
except ImportError:  # python-chess not installed
    chess_game = None

# ----------------------------------------------------------------- config

USER = "Wajahat-Programmer"
NAME = "Wajahat Ali Khan"
ROLE = "Head of Software Division"
COMPANY = "Revive Medical Technologies"
LOCATION = "Islamabad, Pakistan"
TAGLINE = "RPM, EHR integration, RCM and AI software for medical practices."
FOCUS = "Healthcare software"
STACK = "React, React Native, Node.js, TypeScript, AWS"
LINKEDIN = "https://www.linkedin.com/in/wak-swe/"
EMAIL = "wajahatalikhanundoscore@gmail.com"

# Repositories shown in the featured reel, in order.
FEATURED = ["NeuroEHR", "rcm-demo", "rpm-demo", "negative-testing-ccda"]

# Only repositories listed in FEATURED are ever named on the profile.

# Full tech stack, grouped. Shown as chips on the tech stack card.
TECH = [
    ("Languages", ["JavaScript", "TypeScript", "Python", "Java"]),
    ("Frontend and mobile", ["React", "React Native", "Redux", "Tailwind CSS", "PyQt"]),
    ("Backend and data", ["Node.js", "MongoDB", "MySQL", "PostgreSQL", "WebSockets", "VideoSDK"]),
    ("Cloud and tooling", ["AWS", "Docker", "Git", "Linux"]),
    ("Design and delivery", ["Figma", "ClickUp", "Jira"]),
]

# The contribution snake is produced by the existing snake.yml workflow.
SNAKE_URL = f"https://raw.githubusercontent.com/{USER}/{USER}/output/github-snake-dark.svg"

# ----------------------------------------------------------------- palette

BG_A, BG_B, BG_C = "#05201d", "#0b3a35", "#0a2836"
EDGE = "#1f8f7f"
MINT = "#5ee6b8"
TEXT = "#f2fffa"
MUTED = "#8fbdb3"
PANEL = "#082a27"
PANEL_EDGE = "#1b6f63"
SANS = "'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

LANG_COLORS = {
    "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "HTML": "#e34c26",
    "CSS": "#663399", "Python": "#3572A5", "Java": "#b07219",
    "Handlebars": "#f7931e", "Kotlin": "#A97BFF", "Swift": "#F05138",
}
LEVELS = ["#103330", "#1c6b5c", "#2ba486", "#4bd3aa", "#93f7d6"]

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
W = 840

# ----------------------------------------------------------------- fetch


def fetch(url, binary=False):
    headers = {"User-Agent": "profile-readme-generator"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as res:
        data = res.read()
    return data if binary else data.decode("utf-8")


def load():
    user = json.loads(fetch(f"https://api.github.com/users/{USER}"))
    repos = json.loads(fetch(
        f"https://api.github.com/users/{USER}/repos?per_page=100&sort=pushed"))
    repos = [r for r in repos if not r["fork"] and r["name"] != USER]
    avatar = fetch(user["avatar_url"] + "&s=192", binary=True)
    html = fetch(f"https://github.com/users/{USER}/contributions")

    cells = {}
    for td in re.findall(r"<td[^>]*data-date=[^>]*>", html):
        date = re.search(r'data-date="([\d-]+)"', td).group(1)
        level = int(re.search(r'data-level="(\d)"', td).group(1))
        cid = re.search(r'id="([^"]+)"', td).group(1)
        cells[cid] = {"date": dt.date.fromisoformat(date), "level": level, "count": 0}
    for cid, n in re.findall(
            r'<tool-tip[^>]*for="([^"]+)"[^>]*>\s*(\d+|No) contribution', html):
        if cid in cells and n != "No":
            cells[cid]["count"] = int(n)
    days = sorted(cells.values(), key=lambda c: c["date"])
    try:
        snake = fetch(SNAKE_URL)
    except OSError:
        snake = None
    return user, repos, avatar, days, snake


# ----------------------------------------------------------------- svg bits


def frame(height, body, width=W):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{BG_A}"/>
      <stop offset="0.55" stop-color="{BG_B}"/>
      <stop offset="1" stop-color="{BG_C}"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="{MINT}" stop-opacity="0.22"/>
      <stop offset="1" stop-color="{MINT}" stop-opacity="0"/>
    </radialGradient>
    <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="1" fill="{MINT}" fill-opacity="0.10"/>
    </pattern>
  </defs>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="18" fill="url(#bg)" stroke="{EDGE}" stroke-width="1.5"/>
  <clipPath id="card"><rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="18"/></clipPath>
  <ellipse cx="{width * 0.82:.0f}" cy="0" rx="{width * 0.45:.0f}" ry="{height * 0.9:.0f}" fill="url(#glow)" clip-path="url(#card)"/>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="18" fill="url(#grid)"/>
{body}
</svg>
"""


def label(x, y, text, anchor="start", size=10.5, fill=MUTED):
    return (f'  <text x="{x}" y="{y}" font-family="{MONO}" font-size="{size}" '
            f'letter-spacing="2" fill="{fill}" text-anchor="{anchor}">{escape(text.upper())}</text>')


def text(x, y, s, size=14, fill=TEXT, weight=400, anchor="start", family=SANS):
    return (f'  <text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>')


def panel(x, y, w, h):
    return (f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{PANEL}" '
            f'fill-opacity="0.72" stroke="{PANEL_EDGE}" stroke-width="1"/>')


def clip(s, n):
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def lang_color(lang):
    return LANG_COLORS.get(lang, MINT)


# ----------------------------------------------------------------- cards


def card_hero(user, repos, avatar, days, langs):
    b64 = base64.b64encode(avatar).decode()
    out = [
        label(40, 42, f"@{USER}"),
        label(W - 40, 42, "profile", anchor="end"),
        '  <clipPath id="av"><circle cx="92" cy="122" r="50"/></clipPath>',
        f'  <image href="data:image/png;base64,{b64}" x="42" y="72" width="100" height="100" clip-path="url(#av)"/>',
        f'  <circle cx="92" cy="122" r="51.5" fill="none" stroke="{MINT}" stroke-width="2.5"/>',
        text(166, 112, NAME, size=33, weight=700),
        text(166, 139, f"{ROLE} · {COMPANY}", size=15, fill=MUTED),
    ]
    x = 166
    for lang, _ in langs[:3]:
        w = int(len(lang) * 7.4 + 34)
        out.append(f'  <rect x="{x}" y="156" width="{w}" height="26" rx="13" fill="{PANEL}" stroke="{PANEL_EDGE}"/>')
        out.append(f'  <circle cx="{x + 15}" cy="169" r="4" fill="{lang_color(lang)}"/>')
        out.append(text(x + 25, 173.5, lang, size=12.5))
        x += w + 10
    out += [
        text(W - 40, 124, f"{len(repos)}", size=52, weight=700, fill=MINT, anchor="end"),
        label(W - 40, 148, "public repositories", anchor="end"),
        label(W - 40, 204, f"github.com/{USER}", anchor="end", size=9.5),
    ]
    return frame(226, "\n".join(out))


def card_highlights(repos, langs):
    out = [label(40, 40, "highlights")]
    cw, gap, x = 240, 20, 40
    for lang, n in langs[:3]:
        out.append(panel(x, 56, cw, 92))
        out.append(f'  <circle cx="{x + 22}" cy="86" r="5" fill="{lang_color(lang)}"/>')
        out.append(text(x + 36, 92, lang, size=19, weight=700))
        noun = "repository" if n == 1 else "repositories"
        out.append(text(x + 20, 124, f"Main language in {n} {noun}", size=12.5, fill=MUTED))
        x += cw + gap
    return frame(176, "\n".join(out))


def card_languages(langs):
    total = sum(n for _, n in langs)
    rows = langs[:6]
    out = [
        text(40, 54, "Language Stack", size=24, weight=700),
        text(40, 78, "Repository-weighted technologies", size=13, fill=MINT),
        label(W - 40, 50, f"{total} repositories", anchor="end"),
    ]
    y = 114
    for lang, n in rows:
        pct = n / total
        out.append(f'  <circle cx="46" cy="{y - 4}" r="5" fill="{lang_color(lang)}"/>')
        out.append(text(62, y, lang, size=14, weight=600))
        out.append(f'  <rect x="200" y="{y - 11}" width="520" height="10" rx="5" fill="{PANEL}" stroke="{PANEL_EDGE}" stroke-width="0.8"/>')
        out.append(f'  <rect x="200" y="{y - 11}" width="{max(10, 520 * pct):.0f}" height="10" rx="5" fill="{lang_color(lang)}"/>')
        out.append(text(W - 40, y, f"{pct * 100:.0f}%", size=13, fill=MUTED, anchor="end", family=MONO))
        y += 34
    return frame(y + 4, "\n".join(out))


def card_featured(featured):
    out = [label(40, 40, "featured reel"), label(W - 40, 40, f"{len(featured)} projects", anchor="end")]
    cw, ch = 372, 122
    for i, r in enumerate(featured[:4]):
        x = 40 + (i % 2) * (cw + 16)
        y = 56 + (i // 2) * (ch + 16)
        lang = r["language"] or "Code"
        pushed = dt.datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00"))
        desc = r["description"] or "Description coming soon."
        out.append(panel(x, y, cw, ch))
        out.append(label(x + 18, y + 26, f"{USER}/", size=9))
        out.append(text(x + 18, y + 54, clip(r["name"], 26), size=19, weight=700, fill=MINT, family=MONO))
        out.append(text(x + 18, y + 77, clip(desc, 44), size=12.5, fill=MUTED))
        out.append(f'  <circle cx="{x + 23}" cy="{y + 100}" r="4.5" fill="{lang_color(lang)}"/>')
        out.append(text(x + 34, y + 104.5, f"{lang}  ·  updated {pushed:%b %Y}", size=12, fill=TEXT))
        cx, cy = x + cw - 48, y + 60
        short = "".join(c for c in lang if c.isupper())[:2] or lang[:2].upper()
        out.append(f'  <circle cx="{cx}" cy="{cy}" r="26" fill="none" stroke="{PANEL_EDGE}" stroke-width="7"/>')
        out.append(f'  <circle cx="{cx}" cy="{cy}" r="26" fill="none" stroke="{lang_color(lang)}" stroke-width="7" '
                   f'stroke-dasharray="118 164" stroke-linecap="round" transform="rotate(-90 {cx} {cy})"/>')
        out.append(text(cx, cy + 5, short, size=14, weight=700, anchor="middle", family=MONO))
    rows = (min(len(featured), 4) + 1) // 2
    return frame(56 + rows * (ch + 16) + 20, "\n".join(out))


def card_tech():
    out = [
        text(40, 54, "Tech Stack", size=24, weight=700),
        text(40, 78, "What I build and ship with", size=13, fill=MINT),
        label(W - 40, 50, f"{sum(len(items) for _, items in TECH)} tools", anchor="end"),
    ]
    y = 112
    for group, items in TECH:
        out.append(label(40, y + 4, group, size=9.5))
        x = 236
        for item in items:
            w = int(len(item) * 7.6 + 26)
            if x + w > W - 36:
                x, y = 236, y + 36
            out.append(f'  <rect x="{x}" y="{y - 14}" width="{w}" height="27" rx="13.5" fill="{PANEL}" '
                       f'fill-opacity="0.8" stroke="{PANEL_EDGE}"/>')
            out.append(text(x + w / 2, y + 4.5, item, size=12.5, anchor="middle"))
            x += w + 8
        y += 40
    return frame(y - 4, "\n".join(out))


def embed_snake(svg, x, y, width):
    """Recolour the Platane/snk animation and nest it inside a card. Returns (markup, height)."""
    head = re.match(r"<svg[^>]*>", svg)
    box = re.search(r'viewBox="([-\d. ]+)"', head.group(0)).group(1)
    _, _, vw, vh = (float(v) for v in box.split())
    inner = svg[head.end(): svg.rindex("</svg>")]
    palette = (f":root{{--cb:#00000000;--cs:{MINT};--ce:{LEVELS[0]};--c0:{LEVELS[0]};"
               f"--c1:{LEVELS[1]};--c2:{LEVELS[2]};--c3:{LEVELS[3]};--c4:{LEVELS[4]}}}")
    inner = re.sub(r":root\{[^}]*\}", palette, inner, count=1)
    height = width * vh / vw
    return (f'  <svg x="{x}" y="{y}" width="{width}" height="{height:.1f}" viewBox="{box}">{inner}</svg>',
            height)


def card_trail(days, snake):
    total = sum(d["count"] for d in days)
    active = sum(1 for d in days if d["count"])
    best = run = 0
    for d in days:
        run = run + 1 if d["count"] else 0
        best = max(best, run)
    out = [
        label(40, 40, "commit trail"),
        text(40, 68, f"{total:,} contributions, {active} active days, longest run {best} days", size=15, weight=600),
    ]
    if snake:
        markup, height = embed_snake(snake, 34, 80, W - 68)
        out.append(markup)
        ly = 80 + height + 14
    else:
        first = days[0]["date"]
        start = first - dt.timedelta(days=(first.weekday() + 1) % 7)  # back to Sunday
        cell, gap, x0, y0 = 11, 3.2, 44, 90
        for d in days:
            col, row = divmod((d["date"] - start).days, 7)
            out.append(f'  <rect x="{x0 + col * (cell + gap):.1f}" y="{y0 + row * (cell + gap):.1f}" '
                       f'width="{cell}" height="{cell}" rx="2.5" fill="{LEVELS[d["level"]]}"/>')
        ly = y0 + 7 * (cell + gap) + 16
    out.append(label(W - 150, ly + 1, "less", anchor="end", size=9))
    for i, c in enumerate(LEVELS):
        out.append(f'  <rect x="{W - 142 + i * 15}" y="{ly - 9}" width="11" height="11" rx="2.5" fill="{c}"/>')
    out.append(label(W - 62, ly + 1, "more", size=9))
    return frame(int(ly + 24), "\n".join(out))


def card_chess(placement, last=None):
    size, sq, pad = 420, 44, 34
    glyph = {"k": "♚", "q": "♛", "r": "♜", "b": "♝", "n": "♞", "p": "♟"}
    marked = set(last or ())
    out = [f'  <rect x="{pad - 8}" y="{pad - 8}" width="{sq * 8 + 16}" height="{sq * 8 + 16}" rx="12" '
           f'fill="{PANEL}" stroke="{MINT}" stroke-opacity="0.55" stroke-width="1.5"/>']
    for r, rank in enumerate(placement.split("/")):
        f = 0
        for ch in rank:
            for _ in range(int(ch) if ch.isdigit() else 1):
                name = "abcdefgh"[f] + str(8 - r)
                fill = "#1d7566" if (r + f) % 2 == 0 else "#0e4a42"
                out.append(f'  <rect x="{pad + f * sq}" y="{pad + r * sq}" width="{sq}" height="{sq}" fill="{fill}"/>')
                if name in marked:
                    out.append(f'  <rect x="{pad + f * sq + 1.5}" y="{pad + r * sq + 1.5}" width="{sq - 3}" '
                               f'height="{sq - 3}" fill="{MINT}" fill-opacity="0.22" stroke="{MINT}" stroke-width="2"/>')
                f += 1
            if ch.isdigit():
                continue
            white = ch.isupper()
            out.append(
                f'  <text x="{pad + (f - 1) * sq + sq / 2}" y="{pad + r * sq + sq * 0.76:.1f}" font-size="33" '
                f'text-anchor="middle" fill="{"#f2fffa" if white else "#06211e"}" '
                f'stroke="{"#06211e" if white else "#93f7d6"}" stroke-width="0.9" '
                f"font-family=\"'Segoe UI Symbol', 'Apple Symbols', 'DejaVu Sans', 'Noto Sans Symbols2', serif\">"
                f'{glyph[ch.lower()]}&#xFE0E;</text>')
    for i, letter in enumerate("abcdefgh"):
        out.append(label(pad + i * sq + sq / 2 - 3, size - 12, letter, size=9))
    for i in range(8):
        out.append(label(11, pad + i * sq + sq / 2 + 3, str(8 - i), size=9))
    return frame(size, "\n".join(out), width=size)


# ----------------------------------------------------------------- readme

DIVIDER = '<p align="center">───── ◆ ─────</p>'


def issue_url(command):
    query = urllib.parse.urlencode({
        "title": f"chess|{command}",
        "body": 'Press "Submit new issue" to play. No need to change anything here.',
    })
    return f"https://github.com/{USER}/{USER}/issues/new?{query}"


def chess_section(game):
    if not game:
        return ""
    status = f"{game['turn']} to move"
    if game["check"]:
        status += ", and in check"
    rows = "\n".join(
        f"| {piece} | {square} | "
        + " · ".join(f'<a href="{escape(issue_url("move|" + uci))}">{san}</a>' for san, uci in options)
        + " |"
        for piece, square, options in game["moves"])
    recent = game["history"][-6:]
    trail = " · ".join(
        f'{m["n"]}{"." if m["color"] == "White" else "..."} {m["san"]} '
        f'(<a href="https://github.com/{m["by"]}">{m["by"]}</a>)' for m in recent)
    extras = []
    if trail:
        extras.append(f'<p align="center"><sub>Recent moves: {trail}</sub></p>')
    if game["last_result"]:
        extras.append(f'<p align="center"><sub>Last game: {escape(game["last_result"])}. '
                      f'Games finished: {game["finished"]}.</sub></p>')
    if game["can_reset"]:
        extras.append(f'<p align="center"><sub><a href="{escape(issue_url("new"))}">Start a new game</a></sub></p>')
    extras = "\n\n".join(extras)
    return f"""## Play the next move

<p align="center"><img src="./assets/chess.svg" alt="Chess board. {status}." width="400"/></p>

<p align="center"><b>{status}.</b> Anyone can play. Pick a move below, press "Submit new issue", and the board updates in about a minute.</p>

| Piece | From | Move to |
| --- | --- | --- |
{rows}

{extras}

{DIVIDER}
"""


def readme(user, repos, featured, langs, days, game):
    total = sum(d["count"] for d in days)
    top = " · ".join(lang for lang, _ in langs[:3])
    cells = "\n".join(
        f'    <td width="25%" valign="top"><a href="{r["html_url"]}"><b>{escape(r["name"])}</b></a><br/><br/>'
        f'{escape(r["description"] or "Description coming soon.")}<br/><br/>'
        f'<sub>{escape(r["language"] or "Code")}</sub></td>'
        for r in featured[:4])
    return f"""<p align="center"><sub>AN ORIGINAL PROFILE · {USER.upper()}</sub></p>

<p align="center"><img src="./assets/hero.svg" alt="{NAME}, {ROLE} at {COMPANY}" width="100%"/></p>

<p align="center"><b>{ROLE}</b> · {LOCATION}</p>

<p align="center">{TAGLINE}</p>

<p align="center"><a href="{LINKEDIN}">LinkedIn</a> · <a href="mailto:{EMAIL}">Email</a> · <a href="https://github.com/{USER}?tab=repositories">Repositories</a></p>

{DIVIDER}

<table>
  <tr>
    <td width="62%" valign="top">
      <h2>The point of view</h2>
      <blockquote>Software for a medical practice has one job: get the device reading into the chart and the claim out the door, without a clinician typing it twice.</blockquote>
      <sub>Small teams, tested edge cases, and code that is safe to run near patient data.</sub>
    </td>
    <td width="38%" valign="top">
      <sub><b>PROFILE</b></sub><br/><br/>
      <sub>ROLE · {ROLE}</sub><br/>
      <sub>BASED · {LOCATION}</sub><br/>
      <sub>FOCUS · {FOCUS}</sub><br/>
      <sub>STACK · {STACK}</sub><br/><br/>
      <b>{len(repos)}</b> public repositories<br/>
      <b>{total:,}</b> contributions in the last year
    </td>
  </tr>
</table>

{DIVIDER}

## In the current cut

<p align="center"><img src="./assets/highlights.svg" alt="Most used languages: {top}" width="100%"/></p>

<p align="center"><sub>The languages behind the most recent public work.</sub></p>

{DIVIDER}

## Production palette

<p align="center"><img src="./assets/tech.svg" alt="Tech stack: {escape(', '.join(i for _, items in TECH for i in items))}" width="100%"/></p>

<p align="center"><img src="./assets/languages.svg" alt="Language stack, weighted by repository" width="100%"/></p>

<p align="center"><sub>Tools chosen for the work, not the trend.</sub></p>

{DIVIDER}

## Featured reel

<p align="center"><img src="./assets/featured.svg" alt="Featured repositories" width="100%"/></p>

<table>
  <tr>
{cells}
  </tr>
</table>

{DIVIDER}

## Contribution trail

<p align="center"><img src="./assets/trail.svg" alt="{total:,} contributions in the last year" width="100%"/></p>

{DIVIDER}

{chess_section(game)}
<p align="center"><sub>THE NEXT SCENE</sub></p>

<h2 align="center">Keep the story moving</h2>

<p align="center">I enjoy working with people who care about the details, share the context, and ship something useful.</p>

<p align="center"><a href="{LINKEDIN}">LinkedIn</a> · <a href="mailto:{EMAIL}">Email</a></p>
"""


# ----------------------------------------------------------------- main


def main():
    user, repos, avatar, days, snake = load()
    langs = Counter(r["language"] for r in repos if r["language"]).most_common()
    by_name = {r["name"]: r for r in repos}
    featured = [by_name[n] for n in FEATURED if n in by_name]
    game = chess_game.view(chess_game.load_state()) if chess_game else None

    os.makedirs(ASSETS, exist_ok=True)
    cards = {
        "hero.svg": card_hero(user, repos, avatar, days, langs),
        "highlights.svg": card_highlights(repos, langs),
        "tech.svg": card_tech(),
        "languages.svg": card_languages(langs),
        "featured.svg": card_featured(featured),
        "trail.svg": card_trail(days, snake),
    }
    if game:
        cards["chess.svg"] = card_chess(game["placement"], game["last"])
    for name, svg in cards.items():
        with open(os.path.join(ASSETS, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(svg)
    with open(os.path.join(HERE, "README.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(readme(user, repos, featured, langs, days, game))

    print(f"wrote README.md and {len(cards)} cards; "
          f"{sum(d['count'] for d in days)} contributions, {len(repos)} repos, "
          f"snake {'embedded' if snake else 'missing'}, chess {'on' if game else 'off'}")


if __name__ == "__main__":
    main()
