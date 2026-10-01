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
import textwrap
from collections import Counter
from html import escape

try:
    import chess_game
except ImportError:  # python-chess not installed
    chess_game = None

# ----------------------------------------------------------------- config

USER = "Wajahat-Programmer"
NAME = "Wajahat Ali Khan"
ROLE = "Sr. Software Engineer"
COMPANY = "Revive Medical Technologies"
LOCATION = "Islamabad, Pakistan"
TAGLINE = "RPM, EHR integration, RCM and AI software for medical practices."
FOCUS = "Healthcare software"
STACK = "React, React Native, Node.js, TypeScript, AWS"
LINKEDIN = "https://www.linkedin.com/in/wak-swe/"
EMAIL = "wajahatalikhanundoscore@gmail.com"

# No repository is named on the profile; only counts and languages are shown.

# Full tech stack, grouped. Shown as chips on the tech stack card.
TECH = [
    ("Languages", ["JavaScript", "TypeScript", "Python", "Java"]),
    ("Frontend and mobile", ["React", "React Native", "Redux", "Tailwind CSS", "PyQt"]),
    ("Backend and data", ["Node.js", "MongoDB", "MySQL", "PostgreSQL", "WebSockets", "VideoSDK"]),
    ("Cloud and tooling", ["AWS", "Docker", "Proxmox", "Git", "Linux"]),
    ("AI tools", ["Cursor", "Claude Code", "Antigravity"]),
    ("Design and delivery", ["Figma", "ClickUp", "Jira"]),
]

# Shown as chips on the hero card and as tiles under "In the current cut".
HIGHLIGHTS = [
    ("JavaScript", "Web apps and services"),
    ("TypeScript", "Typed front ends, APIs"),
    ("React", "Web applications"),
    ("React Native", "iOS and Android apps"),
]

# Simple Icons slugs (https://simpleicons.org). Tools without one get a dot.
ICONS = {
    "JavaScript": "javascript", "TypeScript": "typescript", "Python": "python",
    "Java": "openjdk", "React": "react", "React Native": "react", "Redux": "redux",
    "Tailwind CSS": "tailwindcss", "PyQt": "qt", "Node.js": "nodedotjs",
    "MongoDB": "mongodb", "MySQL": "mysql", "PostgreSQL": "postgresql",
    "Docker": "docker", "Git": "git", "Linux": "linux", "Figma": "figma",
    "ClickUp": "clickup", "Jira": "jira", "Proxmox": "proxmox",
    "Cursor": "cursor", "Claude Code": "claudecode",
}

# The playable board and its move list. The issue workflow stays in the repo either way.
SHOW_LIVE_BOARD = False

# The contribution snake is produced by the existing snake.yml workflow.
SNAKE_URL = f"https://raw.githubusercontent.com/{USER}/{USER}/output/github-snake-dark.svg"

# ----------------------------------------------------------------- palette

BG_A, BG_B, BG_C = "#071323", "#0b2034", "#0d2c3d"
EDGE = "#2c6480"
MINT = "#5ee6b8"
CYAN = "#49d6ec"
TEXT = "#f2fbff"
MUTED = "#9cc6d6"
PANEL = "#0f2a40"
SHADE = "#030912"  # dark plate behind the content of every card
PANEL_EDGE = "#2c6480"
SANS = "'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

LANG_COLORS = {
    "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "HTML": "#e34c26",
    "CSS": "#663399", "Python": "#3572A5", "Java": "#b07219",
    "Handlebars": "#f7931e", "Kotlin": "#A97BFF", "Swift": "#F05138",
}
LEVELS = ["#1a3a56", "#1d6b78", "#2ba58c", "#4bd3aa", "#93f7d6"]

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
ICON_DIR = os.path.join(HERE, "icons")
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
      <stop offset="0" stop-color="{CYAN}" stop-opacity="0.20"/>
      <stop offset="1" stop-color="{CYAN}" stop-opacity="0"/>
    </radialGradient>
    <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="1" fill="{CYAN}" fill-opacity="0.10"/>
    </pattern>
  </defs>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="18" fill="url(#bg)" stroke="{EDGE}" stroke-width="1.5"/>
  <clipPath id="card"><rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="18"/></clipPath>
  <ellipse cx="{width * 0.82:.0f}" cy="0" rx="{width * 0.45:.0f}" ry="{height * 0.9:.0f}" fill="url(#glow)" clip-path="url(#card)"/>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="18" fill="url(#grid)"/>
  <rect x="12" y="12" width="{width - 24}" height="{height - 24}" rx="11" fill="{SHADE}" fill-opacity="0.66" stroke="{PANEL_EDGE}" stroke-opacity="0.45"/>
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


def icon(name, x, y, size=15):
    """Brand icon for a tool, cached in icons/. Falls back to a dot."""
    slug = ICONS.get(name)
    path = os.path.join(ICON_DIR, f"{slug}.svg")
    if slug and not os.path.exists(path):
        try:
            svg = fetch(f"https://cdn.simpleicons.org/{slug}")
            os.makedirs(ICON_DIR, exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(svg)
        except OSError:
            slug = None
    if not slug:
        return f'  <circle cx="{x + size / 2}" cy="{y + size / 2}" r="3.5" fill="{MINT}"/>'
    with open(path, encoding="utf-8") as fh:
        svg = fh.read()
    d = re.search(r'<path d="([^"]+)"', svg).group(1)
    fill = re.search(r'fill="#([0-9A-Fa-f]{6})"', svg).group(1)
    r, g, b = (int(fill[i:i + 2], 16) for i in (0, 2, 4))
    if 0.2126 * r + 0.7152 * g + 0.0722 * b < 110:  # too dark for the card
        fill = "e6f3f8"
    return (f'  <svg x="{x}" y="{y}" width="{size}" height="{size}" viewBox="0 0 24 24">'
            f'<path d="{d}" fill="#{fill}"/></svg>')


def chip(name, x, y, height=27):
    """Icon + label pill. Returns (markup, width)."""
    w = int(len(name) * 7.6 + 46)
    return "\n".join([
        f'  <rect x="{x}" y="{y}" width="{w}" height="{height}" rx="{height / 2}" fill="{PANEL}" '
        f'fill-opacity="0.85" stroke="{PANEL_EDGE}"/>',
        icon(name, x + 11, y + (height - 15) / 2),
        text(x + 33, y + height / 2 + 4.5, name, size=12.5),
    ]), w


# ----------------------------------------------------------------- cards


def card_hero(user, repos, avatar, days, langs):
    b64 = base64.b64encode(avatar).decode()
    out = [
        label(40, 42, f"@{USER}"),
        label(W - 40, 42, "profile", anchor="end"),
        '  <clipPath id="av"><circle cx="92" cy="122" r="50"/></clipPath>',
        f'  <image href="data:image/png;base64,{b64}" x="42" y="72" width="100" height="100" clip-path="url(#av)"/>',
        f'  <circle cx="92" cy="122" r="51.5" fill="none" stroke="{MINT}" stroke-width="2.5"/>',
        f'  <rect x="166" y="70" width="46" height="4" rx="2" fill="{MINT}"/>',
        text(166, 112, NAME, size=33, weight=700),
        text(166, 139, f"{ROLE} · {COMPANY}", size=15, fill=MUTED),
    ]
    x = 166
    for name, _ in HIGHLIGHTS:
        markup, w = chip(name, x, 156, height=26)
        out.append(markup)
        x += w + 8
    out += [
        text(W - 40, 124, f"{len(repos)}", size=52, weight=700, fill=MINT, anchor="end"),
        label(W - 40, 148, "public repositories", anchor="end"),
        label(W - 40, 204, f"github.com/{USER}", anchor="end", size=9.5),
    ]
    return frame(226, "\n".join(out))


def card_pov(repos, days):
    quote = ("Software for a medical practice has one job: get the device reading into "
             "the chart and the claim out the door, without a clinician typing it twice.")
    note = "Small teams, tested edge cases, and code that is safe to run near patient data."
    out = [
        label(40, 42, "the point of view"),
        f'  <text x="36" y="132" font-family="Georgia, serif" font-size="78" fill="{MINT}" fill-opacity="0.9">&#8220;</text>',
    ]
    y = 104
    for line in textwrap.wrap(quote, 40):
        out.append(text(84, y, line, size=19.5, weight=600))
        y += 28
    out.append(f'  <rect x="84" y="{y - 6}" width="46" height="3" rx="1.5" fill="{CYAN}"/>')
    y += 20
    for line in textwrap.wrap(note, 58):
        out.append(text(84, y, line, size=13, fill=MUTED))
        y += 19
    height = max(y + 22, 268)

    px, pw = 548, 252
    out.append(panel(px, 34, pw, height - 68))
    out.append(label(px + 20, 62, "profile", fill=MINT))
    ry = 90
    for key, value in (("role", ROLE), ("based", LOCATION), ("focus", FOCUS)):
        out.append(label(px + 20, ry, key, size=9))
        out.append(text(px + 84, ry, value, size=13, weight=600))
        ry += 26
    total = sum(d["count"] for d in days)
    tw = (pw - 40 - 12) / 2
    for i, (number, caption) in enumerate(((len(repos), "public repos"), (f"{total:,}", "contributions"))):
        tx = px + 20 + i * (tw + 12)
        out.append(f'  <rect x="{tx}" y="{ry}" width="{tw}" height="62" rx="10" fill="{BG_A}" '
                   f'fill-opacity="0.7" stroke="{PANEL_EDGE}"/>')
        out.append(text(tx + tw / 2, ry + 30, str(number), size=24, weight=700, fill=MINT, anchor="middle"))
        out.append(label(tx + tw / 2, ry + 49, caption, anchor="middle", size=7.5))
    return frame(int(height), "\n".join(out))


def card_highlights(repos, langs):
    out = [label(40, 40, "highlights")]
    gap = 14
    cw = (W - 80 - gap * (len(HIGHLIGHTS) - 1)) / len(HIGHLIGHTS)
    x = 40
    for name, note in HIGHLIGHTS:
        out.append(panel(x, 56, cw, 92))
        out.append(icon(name, x + 16, 74, size=20))
        out.append(text(x + 44, 91, name, size=16.5, weight=700))
        out.append(text(x + 16, 126, note, size=12, fill=MUTED))
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
            if x + int(len(item) * 7.6 + 46) > W - 36:
                x, y = 236, y + 36
            markup, w = chip(item, x, y - 14)
            out.append(markup)
            x += w + 8
        y += 40
    return frame(y - 4, "\n".join(out))


# 5x5 pixel font for the terminal banner. Only the letters in BANNER are needed.
PIXELS = {
    "A": [".###.", "#...#", "#####", "#...#", "#...#"],
    "H": ["#...#", "#...#", "#####", "#...#", "#...#"],
    "I": ["#####", "..#..", "..#..", "..#..", "#####"],
    "J": ["..###", "...#.", "...#.", "#..#.", ".##.."],
    "K": ["#..#.", "#.#..", "##...", "#.#..", "#..#."],
    "L": ["#....", "#....", "#....", "#....", "#####"],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#"],
    "T": ["#####", "..#..", "..#..", "..#..", "..#.."],
    "W": ["#...#", "#...#", "#.#.#", "##.##", "#...#"],
    " ": [".....", ".....", ".....", ".....", "....."],
}
BANNER = "WAJAHAT ALI KHAN"
TERMINAL = [
    ("whoami", f"{ROLE} · {LOCATION}"),
    ("cat focus.txt", "Healthcare software: RPM, EHR integration, RCM and AI"),
    ("ls stack/", "javascript   typescript   react   react-native   node   aws"),
]


def smil(attr, values, times, extra=""):
    """One looping SMIL animation. `times` are seconds; the last one is the loop length."""
    dur = times[-1]
    keys = ";".join(f"{t / dur:.4f}" for t in times)
    return (f'<animate attributeName="{attr}" values="{";".join(str(v) for v in values)}" '
            f'keyTimes="{keys}" dur="{dur}s" repeatCount="indefinite" {extra}/>')


def card_terminal():
    dur, height = 16, 352
    out = [
        f'  <rect x="24" y="22" width="{W - 48}" height="{height - 44}" rx="12" fill="{BG_A}" '
        f'fill-opacity="0.92" stroke="{PANEL_EDGE}"/>',
        f'  <path d="M24 34 a12 12 0 0 1 12 -12 h{W - 72} a12 12 0 0 1 12 12 v18 h-{W - 48}z" fill="{PANEL}"/>',
        '  <circle cx="46" cy="37" r="5" fill="#ff5f57"/>',
        '  <circle cx="64" cy="37" r="5" fill="#febc2e"/>',
        '  <circle cx="82" cy="37" r="5" fill="#28c840"/>',
        text(W / 2, 41.5, f"{USER.lower()}@github: ~", size=12, fill=MUTED, anchor="middle", family=MONO),
    ]
    # banner, revealed one pixel row at a time
    x0, y0 = 62, 76
    cols = len(BANNER) * 6 - 1
    cell = min(10, (W - 2 * x0) / cols)  # shrink the pixels so long names still fit
    for row in range(5):
        start = 0.3 + row * 0.18
        out.append(f'  <g opacity="0">{smil("opacity", [0, 0, 1, 1], [0, start, start + 0.15, dur])}')
        for i, ch in enumerate(BANNER):
            for col, bit in enumerate(PIXELS[ch][row]):
                if bit == "#":
                    cx = i * 6 + col
                    mix = cx / cols
                    r, g, b = (round(a + (c - a) * mix) for a, c in zip((0x5e, 0xe6, 0xb8), (0x49, 0xd6, 0xec)))
                    out.append(f'    <rect x="{x0 + cx * cell:.1f}" y="{y0 + row * cell:.1f}" width="{cell - 1.3:.1f}" '
                               f'height="{cell - 1.3:.1f}" rx="1.6" fill="#{r:02x}{g:02x}{b:02x}"/>')
        out.append("  </g>")

    # typed commands and their output
    y, t, char = 164, 1.6, 7.83
    for n, (cmd, result) in enumerate(TERMINAL):
        typed = len(cmd) * 0.09
        width = len(cmd) * char + 6
        out.append(f'  <g opacity="0">{smil("opacity", [0, 0, 1, 1], [0, t - 0.05, t, dur])}')
        out.append("  " + text(62, y, "$", size=13, fill=MINT, weight=700, family=MONO))
        out.append("  </g>")
        out.append(f'  <clipPath id="type{n}"><rect x="82" y="{y - 14}" height="20" width="0">'
                   f'{smil("width", [0, 0, f"{width:.0f}", f"{width:.0f}"], [0, t + 0.2, t + 0.2 + typed, dur])}'
                   f'</rect></clipPath>')
        out.append(f'  <g clip-path="url(#type{n})">' + text(82, y, cmd, size=13, family=MONO) + "</g>")
        shown = t + 0.2 + typed + 0.35
        out.append(f'  <g opacity="0">{smil("opacity", [0, 0, 1, 1], [0, shown, shown + 0.1, dur])}')
        out.append("  " + text(62, y + 23, result, size=13, fill=MUTED, family=MONO))
        out.append("  </g>")
        y += 52
        t = shown + 0.9
    # resting prompt with a blinking cursor
    out.append(f'  <g opacity="0">{smil("opacity", [0, 0, 1, 1], [0, t, t + 0.05, dur])}')
    out.append("  " + text(62, y, "$", size=13, fill=MINT, weight=700, family=MONO))
    out.append(f'    <rect x="82" y="{y - 12}" width="8" height="15" fill="{MINT}">'
               f'<animate attributeName="opacity" values="1;0" dur="1s" calcMode="discrete" repeatCount="indefinite"/></rect>')
    out.append("  </g>")
    return frame(height, "\n".join(out))


def card_shooter(days):
    """Contribution grid as a space shooter: a ship clears every active day, then the grid resets."""
    first = days[0]["date"]
    start = first - dt.timedelta(days=(first.weekday() + 1) % 7)  # back to Sunday
    cell, gap, x0, y0 = 11, 3.2, 44, 84
    step = cell + gap
    grid = []
    for d in days:
        col, row = divmod((d["date"] - start).days, 7)
        grid.append((col, row, d["level"]))
    targets = sorted((c for c in grid if c[2]), key=lambda c: (c[0], -c[1]))
    if len(targets) > 44:  # keep the loop short on busy profiles
        keep = sorted(targets, key=lambda c: -c[2])[:44]
        targets = sorted(keep, key=lambda c: (c[0], -c[1]))
    per, lead = 0.55, 1.0
    dur = round(lead + len(targets) * per + 3.0, 2)
    ship_y = y0 + 7 * step + 34
    hits = {(c, r): lead + i * per + per * 0.75 for i, (c, r, _) in enumerate(targets)}

    out = [
        label(40, 40, "space shooter"),
        text(40, 64, f"{len(targets)} active days to clear", size=15, weight=600),
        label(W - 40, 40, "contribution game", anchor="end"),
    ]
    for i in range(26):  # stars
        sx, sy = 40 + (i * 131) % (W - 80), 74 + (i * 57) % (ship_y - 60)
        out.append(f'  <circle cx="{sx}" cy="{sy}" r="0.9" fill="{TEXT}" fill-opacity="{0.15 + (i % 4) * 0.08:.2f}"/>')
    for col, row, level in grid:
        x, y = x0 + col * step, y0 + row * step
        hit = hits.get((col, row))
        anim = ""
        if hit is not None:
            anim = smil("fill", [LEVELS[level], LEVELS[level], LEVELS[0], LEVELS[0]],
                        [0, hit, hit + 0.01, dur], 'calcMode="discrete"')
        out.append(f'  <rect x="{x:.1f}" y="{y:.1f}" width="{cell}" height="{cell}" rx="2.5" '
                   f'fill="{LEVELS[level]}">{anim}</rect>')

    # bullets and bursts, one per target
    for i, (col, row, _) in enumerate(targets):
        fire = lead + i * per + per * 0.35
        hit = hits[(col, row)]
        cx, cy = x0 + col * step + cell / 2, y0 + row * step + cell / 2
        out.append(
            f'  <rect x="{cx - 1.2:.1f}" y="{ship_y - 8}" width="2.4" height="8" rx="1.2" fill="{CYAN}" opacity="0">'
            f'{smil("opacity", [0, 0, 1, 1, 0, 0], [0, fire, fire + 0.01, hit, hit + 0.01, dur], "calcMode=\"discrete\"")}'
            f'{smil("y", [ship_y - 8, ship_y - 8, f"{cy:.1f}", f"{cy:.1f}"], [0, fire, hit, dur])}</rect>')
        out.append(
            f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="0" fill="none" stroke="{MINT}" stroke-width="1.6" opacity="0">'
            f'{smil("r", [0, 0, 11, 11], [0, hit, hit + 0.3, dur])}'
            f'{smil("opacity", [0, 0, 0.9, 0, 0], [0, hit, hit + 0.02, hit + 0.3, dur])}</circle>')

    # the ship glides to each target column, then returns
    xs = [x0 + cell / 2] + [x0 + c * step + cell / 2 for c, _, _ in targets] + [x0 + cell / 2]
    ts = [0] + [lead + i * per + per * 0.3 for i in range(len(targets))] + [dur]
    values = [f"{x:.1f} {ship_y}" for x in xs]
    keys = ";".join(f"{t / dur:.4f}" for t in ts)
    out.append(
        f'  <g transform="translate({xs[0]:.1f} {ship_y})">'
        f'<animateTransform attributeName="transform" type="translate" values="{";".join(values)}" '
        f'keyTimes="{keys}" dur="{dur}s" repeatCount="indefinite"/>'
        f'<path d="M0 -11 L7 6 L2.5 3.5 L0 8 L-2.5 3.5 L-7 6 Z" fill="{MINT}"/>'
        f'<path d="M-2 7 L0 13 L2 7 Z" fill="{CYAN}"><animate attributeName="opacity" values="1;0.3;1" dur="0.3s" repeatCount="indefinite"/></path>'
        f'</g>')
    return frame(int(ship_y + 34), "\n".join(out))


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
                fill = "#1f6f86" if (r + f) % 2 == 0 else "#123f58"
                out.append(f'  <rect x="{pad + f * sq}" y="{pad + r * sq}" width="{sq}" height="{sq}" fill="{fill}"/>')
                if name in marked:
                    out.append(f'  <rect x="{pad + f * sq + 1.5}" y="{pad + r * sq + 1.5}" width="{sq - 3}" '
                               f'height="{sq - 3}" fill="{MINT}" fill-opacity="0.22" stroke="{MINT}" stroke-width="2"/>')
                f += 1
            if ch.isdigit():
                continue
            white = ch.isupper()
            here = "abcdefgh"[f - 1] + str(8 - r)
            slide = ""
            if last and here == last[1]:  # replay the latest move on a loop so visitors can see it
                dx = ("abcdefgh".index(last[0][0]) - (f - 1)) * sq
                dy = ((8 - int(last[0][1])) - r) * sq
                slide = (f'<animateTransform attributeName="transform" type="translate" '
                         f'values="{dx} {dy};{dx} {dy};0 0;0 0" keyTimes="0;0.2;0.5;1" dur="3.4s" '
                         f'repeatCount="indefinite"/>')
            out.append(
                f'  <g>{slide}<text x="{pad + (f - 1) * sq + sq / 2}" y="{pad + r * sq + sq * 0.76:.1f}" font-size="33" '
                f'text-anchor="middle" fill="{"#f2fbff" if white else "#071323"}" '
                f'stroke="{"#071323" if white else "#93f7d6"}" stroke-width="0.9" '
                f"font-family=\"'Segoe UI Symbol', 'Apple Symbols', 'DejaVu Sans', 'Noto Sans Symbols2', serif\">"
                f'{glyph[ch.lower()]}&#xFE0E;</text></g>')
    for i, letter in enumerate("abcdefgh"):
        out.append(label(pad + i * sq + sq / 2 - 3, size - 12, letter, size=9))
    for i in range(8):
        out.append(label(11, pad + i * sq + sq / 2 + 3, str(8 - i), size=9))
    return frame(size, "\n".join(out), width=size)


# Game shown by the self-playing board: Morphy's Opera Game, Paris 1858.
REPLAY_NAME = "The Opera Game, Paris 1858"
REPLAY_MOVES = ("e4 e5 Nf3 d6 d4 Bg4 dxe5 Bxf3 Qxf3 dxe5 Bc4 Nf6 Qb3 Qe7 Nc3 c6 Bg5 b5 Nxb5 cxb5 "
                "Bxb5+ Nbd7 O-O-O Rd8 Rxd7 Rxd7 Rd1 Qe6 Bxd7+ Nxd7 Qb8+ Nxb8 Rd8#").split()


def card_chess_replay():
    """A board that plays REPLAY_MOVES by itself on a loop. Needs python-chess."""
    import chess

    size, sq, pad = 420, 44, 34
    per, lead, hold = 0.95, 1.2, 4.0
    dur = round(lead + len(REPLAY_MOVES) * per + hold, 2)
    glyph = {"k": "♚", "q": "♛", "r": "♜", "b": "♝", "n": "♞", "p": "♟"}

    def centre(square):
        f, r = chess.square_file(square), 7 - chess.square_rank(square)
        return pad + f * sq + sq / 2, pad + r * sq + sq * 0.76

    board = chess.Board()
    pieces = {}  # current square -> piece record
    for square, piece in board.piece_map().items():
        pieces[square] = {"symbol": piece.symbol(), "path": [(0, centre(square))], "gone": None}
    records = list(pieces.values())

    def slide(record, t0, t1, target):
        record["path"].append((t0, record["path"][-1][1]))
        record["path"].append((t1, centre(target)))

    for i, san in enumerate(REPLAY_MOVES):
        move = board.parse_san(san)
        t0 = lead + i * per
        t1 = t0 + per * 0.55
        victim = move.to_square
        if board.is_en_passant(move):
            victim = chess.square(chess.square_file(move.to_square), chess.square_rank(move.from_square))
        if board.is_capture(move):
            pieces.pop(victim)["gone"] = t1
        if board.is_castling(move):
            rank = chess.square_rank(move.from_square)
            kingside = chess.square_file(move.to_square) > chess.square_file(move.from_square)
            rook_from = chess.square(7 if kingside else 0, rank)
            rook_to = chess.square(5 if kingside else 3, rank)
            rook = pieces.pop(rook_from)
            slide(rook, t0, t1, rook_to)
            pieces[rook_to] = rook
        mover = pieces.pop(move.from_square)
        slide(mover, t0, t1, move.to_square)
        pieces[move.to_square] = mover
        board.push(move)

    out = [f'  <rect x="{pad - 8}" y="{pad - 8}" width="{sq * 8 + 16}" height="{sq * 8 + 16}" rx="12" '
           f'fill="{PANEL}" stroke="{MINT}" stroke-opacity="0.55" stroke-width="1.5"/>']
    for r in range(8):
        for f in range(8):
            fill = "#1f6f86" if (r + f) % 2 == 0 else "#123f58"
            out.append(f'  <rect x="{pad + f * sq}" y="{pad + r * sq}" width="{sq}" height="{sq}" fill="{fill}"/>')
    for record in records:
        white = record["symbol"].isupper()
        path = record["path"] + [(dur, record["path"][-1][1])]
        values = ";".join(f"{x:.1f} {y:.1f}" for _, (x, y) in path)
        keys = ";".join(f"{t / dur:.4f}" for t, _ in path)
        x, y = path[0][1]
        fade = ""
        if record["gone"] is not None:
            fade = smil("opacity", [1, 1, 0, 0], [0, record["gone"] - 0.12, record["gone"], dur])
        move_anim = ""
        if len(path) > 2:
            move_anim = (f'<animateTransform attributeName="transform" type="translate" values="{values}" '
                         f'keyTimes="{keys}" dur="{dur}s" repeatCount="indefinite"/>')
        out.append(
            f'  <g transform="translate({x:.1f} {y:.1f})">{move_anim}{fade}'
            f'<text font-size="33" text-anchor="middle" fill="{"#f2fbff" if white else "#071323"}" '
            f'stroke="{"#071323" if white else "#93f7d6"}" stroke-width="0.9" '
            f"font-family=\"'Segoe UI Symbol', 'Apple Symbols', 'DejaVu Sans', 'Noto Sans Symbols2', serif\">"
            f'{glyph[record["symbol"].lower()]}&#xFE0E;</text></g>')
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
        "body": "Press the green Create button to play this move. No need to change anything here.",
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
    if not SHOW_LIVE_BOARD:
        return f"""## Play the next move

<p align="center"><img src="./assets/chess-replay.svg" alt="A chess board replaying {REPLAY_NAME}" width="420"/></p>

<p align="center"><sub>{REPLAY_NAME}, replayed move by move. I like strategy on and off the screen.</sub></p>

{DIVIDER}
"""
    return f"""## Play the next move

<table>
  <tr>
    <td width="50%" align="center"><img src="./assets/chess-replay.svg" alt="A chess board replaying {REPLAY_NAME}" width="100%"/><br/><sub>REPLAY · {REPLAY_NAME}. Plays by itself.</sub></td>
    <td width="50%" align="center"><a href="#choose-your-move"><img src="./assets/chess.svg" alt="Live chess board. {status}." width="100%"/></a><br/><sub>LIVE BOARD · {status}. Pick your move from the list below.</sub></td>
  </tr>
</table>

### Choose your move

<p align="center"><b>{status}.</b> Anyone with a GitHub account can play. A README cannot run a game, so pieces cannot be dragged: each move below is a link.</p>

<p align="center"><sub>1. Click a move in the table below. 2. On the page that opens, press the green <b>Create</b> button without changing anything. 3. Come back in about a minute and refresh: the board has moved.</sub></p>

| Piece | From | Move to |
| --- | --- | --- |
{rows}

{extras}

{DIVIDER}
"""


def readme(user, repos, langs, days, game):
    total = sum(d["count"] for d in days)
    top = " · ".join(lang for lang, _ in langs[:3])
    return f"""<p align="center"><sub>AN ORIGINAL PROFILE · {USER.upper()}</sub></p>

<p align="center"><img src="./assets/terminal.svg" alt="Terminal: {NAME}, {ROLE}, {LOCATION}" width="100%"/></p>

<p align="center"><img src="./assets/hero.svg" alt="{NAME}, {ROLE}" width="100%"/></p>

<p align="center"><b>{ROLE}</b> · {LOCATION}</p>

<p align="center">{TAGLINE}</p>

<p align="center"><a href="{LINKEDIN}">LinkedIn</a> · <a href="mailto:{EMAIL}">Email</a> · <a href="https://github.com/{USER}?tab=repositories">Repositories</a></p>

{DIVIDER}

<p align="center"><img src="./assets/pov.svg" alt="The point of view. {ROLE}, {LOCATION}. Focus: {FOCUS}." width="100%"/></p>

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

## Contribution trail

<p align="center"><img src="./assets/trail.svg" alt="{total:,} contributions in the last year" width="100%"/></p>

<p align="center"><img src="./assets/shooter.svg" alt="Contribution grid as a space shooter game" width="100%"/></p>

<p align="center"><sub>A snake eats the year, then a ship clears every active day. Both replay on a loop.</sub></p>

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
    game = chess_game.view(chess_game.load_state()) if chess_game else None

    os.makedirs(ASSETS, exist_ok=True)
    cards = {
        "terminal.svg": card_terminal(),
        "hero.svg": card_hero(user, repos, avatar, days, langs),
        "pov.svg": card_pov(repos, days),
        "highlights.svg": card_highlights(repos, langs),
        "tech.svg": card_tech(),
        "languages.svg": card_languages(langs),
        "trail.svg": card_trail(days, snake),
        "shooter.svg": card_shooter(days),
    }
    if game:
        cards["chess.svg"] = card_chess(game["placement"], game["last"])
        cards["chess-replay.svg"] = card_chess_replay()
    for name, svg in cards.items():
        with open(os.path.join(ASSETS, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(svg)
    with open(os.path.join(HERE, "README.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(readme(user, repos, langs, days, game))

    print(f"wrote README.md and {len(cards)} cards; "
          f"{sum(d['count'] for d in days)} contributions, {len(repos)} repos, "
          f"snake {'embedded' if snake else 'missing'}, chess {'on' if game else 'off'}")


if __name__ == "__main__":
    main()
