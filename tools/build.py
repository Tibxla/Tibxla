"""Builds the SVG images used by the profile README (assets/*.svg).

GitHub serves README images through <img>, so an SVG cannot load web fonts
and the viewer's own fonts are unknown. Every piece of text is therefore
shaped with HarfBuzz and outlined to <path> here: the files render the same
everywhere, with no font dependency.

Each image comes in two variants, picked by <picture> in the README:
  dark   black slab, the portfolio's "inside" world (thibaudtl.com)
  light  white slab, its "outside" world

Run from the repo root after editing the data below:
  python -m venv .venv && .venv/bin/pip install fonttools brotli uharfbuzz
  .venv/bin/python tools/build.py
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "tools" / "fonts"
OUT = ROOT / "assets"

W = 720  # common viewBox width: keeps text legible once GitHub shrinks it on phones

# ---------------------------------------------------------------- fonts


class Face:
    def __init__(self, file: str):
        tt = TTFont(FONTS / file)
        tt.flavor = None
        buf = io.BytesIO()
        tt.save(buf)
        self.tt = TTFont(io.BytesIO(buf.getvalue()))
        self.glyphs = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        self.upm = self.tt["head"].unitsPerEm
        self.hb = hb.Font(hb.Face(buf.getvalue()))

    def shape(self, text: str, size: float, track: float = 0.0):
        b = hb.Buffer()
        b.add_str(text)
        b.guess_segment_properties()
        hb.shape(self.hb, b, {"kern": True, "liga": True})
        s = size / self.upm
        out, x = [], 0.0
        for info, pos in zip(b.glyph_infos, b.glyph_positions):
            out.append((self.order[info.codepoint], x + pos.x_offset * s, pos.y_offset * s))
            x += pos.x_advance * s + track
        return out, x - track if out else 0.0

    def width(self, text: str, size: float, track: float = 0.0) -> float:
        return self.shape(text, size, track)[1]

    def path(self, text: str, size: float, x: float, y: float, track: float = 0.0,
             anchor: str = "start") -> str:
        glyphs, w = self.shape(text, size, track)
        if anchor == "end":
            x -= w
        elif anchor == "middle":
            x -= w / 2
        s = size / self.upm
        pen = SVGPathPen(self.glyphs, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
        for name, gx, gy in glyphs:
            self.glyphs[name].draw(TransformPen(pen, (s, 0, 0, -s, x + gx, y - gy)))
        return pen.getCommands()


DISPLAY = Face("archivo-narrow-latin-700-normal.woff2")
SANS = Face("schibsted-grotesk-latin-500-normal.woff2")
MONO = Face("ibm-plex-mono-latin-400-normal.woff2")
MONO_M = Face("ibm-plex-mono-latin-500-normal.woff2")

# ---------------------------------------------------------------- themes

THEMES = {
    "dark": dict(
        bg="#000000", border="#ffffff24", rule="#ffffff17", hi="#f4f4f7", ink="#e8e8ec",
        prose="#9c9ca6", meta="#8a8a96", deco="#4f4f5a", red="#ff2a5c", cyan="#00c6ff",
        chroma=0.75, prod="#52d18a", live="#c8c8d0", oss="#e8e8ec", wip="#d6a44e",
    ),
    "light": dict(
        bg="#ffffff", border="#0000001f", rule="#00000012", hi="#0b0b0f", ink="#18181d",
        prose="#55555f", meta="#6b6b76", deco="#b9b9c3", red="#ff2a5c", cyan="#00b2e6",
        chroma=0.6, prod="#1f9d5c", live="#5f5f6a", oss="#18181d", wip="#b07a1c",
    ),
}


def p(d: str, fill: str, extra: str = "") -> str:
    return f'<path d="{d}" fill="{fill}"{extra}/>'


def svg(h: int, t: dict, body: str, title: str, style: str = "") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}" '
        f'role="img" aria-label="{title}"><title>{title}</title>'
        + (f"<style>{style}</style>" if style else "")
        + f'<rect x="0.5" y="0.5" width="{W - 1}" height="{h - 1}" rx="14" fill="{t["bg"]}" '
        f'stroke="{t["border"]}"/>' + body + "</svg>\n"
    )


# ---------------------------------------------------------------- banner

CARET_CSS = (
    "@keyframes b{0%,49%{opacity:1}50%,100%{opacity:0}}"
    ".c{animation:b 1.1s steps(1) infinite}"
    "@media (prefers-reduced-motion:reduce){.c{animation:none}}"
)


def banner(t: dict) -> str:
    h, pad = 268, 32
    out = []
    # top bar: terminal prompt + blinking caret, status on the right
    prompt = "tibxla@github:~$ whoami"
    out.append(p(MONO.path(prompt, 14, pad, 42), t["meta"]))
    cx = pad + MONO.width(prompt, 14) + 6
    out.append(f'<rect class="c" x="{cx:.1f}" y="31" width="8" height="14" fill="{t["hi"]}"/>')
    right = "online"
    rw = MONO.width(right, 14)
    out.append(p(MONO.path(right, 14, W - pad, 42, anchor="end"), t["meta"]))
    out.append(f'<circle cx="{W - pad - rw - 11:.1f}" cy="37.5" r="3.5" fill="{t["prod"]}"/>')
    out.append(f'<line x1="0" y1="62.5" x2="{W}" y2="62.5" stroke="{t["rule"]}"/>')

    # the name, with the portfolio's red/cyan chromatic split
    name, size, base = "Tibxla", 128, 186
    d = DISPLAY.path(name, size, pad - 4, base, track=-1.5)
    out.append(f'<defs><path id="n" d="{d}"/></defs>')
    out.append(f'<use href="#n" fill="{t["red"]}" opacity="{t["chroma"]}" x="-2.5"/>')
    out.append(f'<use href="#n" fill="{t["cyan"]}" opacity="{t["chroma"]}" x="2.5"/>')
    out.append(f'<use href="#n" fill="{t["hi"]}"/>')

    # role, bottom-aligned with the name on the right
    out.append(p(SANS.path("Full-stack & AI developer", 25, W - pad, base - 30, anchor="end"), t["hi"]))
    out.append(p(MONO.path("Master's in MIAGE · work-study", 14, W - pad, base, anchor="end"), t["meta"]))

    # bottom bar
    out.append(f'<line x1="0" y1="{h - 52.5}" x2="{W}" y2="{h - 52.5}" stroke="{t["rule"]}"/>')
    out.append(p(MONO.path("// build useful things, automate the rest", 13, pad, h - 21), t["deco"]))
    out.append(p(MONO.path("thibaudtl.com", 13, W - pad, h - 21, anchor="end"), t["meta"]))
    return svg(h, t, "".join(out), "Tibxla, full-stack and AI developer", CARET_CSS)


# ---------------------------------------------------------------- project strips


@dataclass
class Project:
    slug: str
    n: str
    title: str
    status: str  # prod | live | oss | wip
    status_label: str
    context: str
    metrics: list[tuple[str, str]]


PROJECTS = [
    Project("edifig", "01", "Edifig", "prod", "in production", "Le Figaro · 2026",
            [("1,443", "commits"), ("30", "ADRs"), ("~1,600", "tests")]),
    Project("au5000", "02", "Au5000", "live", "live", "Client · 2026",
            [("100", "Lighthouse SEO"), ("FR·EN", "bilingual"), ("18", "tables")]),
    Project("croustylift", "03", "Croustylift", "oss", "open source", "Product · 2026",
            [("1,900+", "tests"), ("24", "ADRs"), ("PWA", "offline-first")]),
    Project("autocalled", "04", "Autocalled", "oss", "open source", "AI voice · 2026",
            [("830+", "tests"), ("21", "ADRs"), ("HFP", "phone bridge")]),
    Project("crypto-graph", "05", "Crypto-Graph", "live", "live demo", "Data viz · 2026",
            [("12,880", "nodes"), ("12,000+", "edges"), ("0.978", "Gini index")]),
]


def strip(pr: Project, t: dict) -> str:
    h, pad = 136, 32
    out = []
    # left: index + status, title, context
    out.append(p(MONO_M.path(pr.n, 13, pad, 40), t["deco"]))
    sx = pad + MONO_M.width(pr.n, 13) + 16
    out.append(f'<circle cx="{sx + 3:.1f}" cy="35.5" r="3.5" fill="{t[pr.status]}"/>')
    out.append(p(MONO.path(pr.status_label, 13, sx + 13, 40), t["meta"]))
    out.append(p(DISPLAY.path(pr.title, 42, pad - 2, 88, track=-0.3), t["hi"]))
    out.append(p(MONO.path(pr.context, 13, pad, 112), t["meta"]))

    # right: telemetry on a fixed grid, so the columns line up from card to card
    col, gap = 118, 22
    x0 = W - pad - 3 * col - 2 * gap
    rx = x0 - 18
    left_edge = pad + max(DISPLAY.width(pr.title, 42, -0.3), MONO.width(pr.context, 13))
    assert rx > left_edge + 12, f"{pr.slug}: telemetry overlaps the title"
    for i, (value, label) in enumerate(pr.metrics):
        assert max(DISPLAY.width(value, 34), MONO.width(label, 13)) <= col, f"{pr.slug}: {value} too wide"
        cx = x0 + i * (col + gap)
        out.append(p(DISPLAY.path(value, 34, cx, 84), t["ink"]))
        out.append(p(MONO.path(label, 13, cx, 108), t["meta"]))
    # thin rule between identity and data
    out.append(f'<line x1="{rx:.1f}" y1="30" x2="{rx:.1f}" y2="112" stroke="{t["rule"]}"/>')

    alt = f"{pr.title}, {pr.status_label}: " + ", ".join(f"{v} {l}" for v, l in pr.metrics)
    return svg(h, t, "".join(out), alt)


# ---------------------------------------------------------------- main


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for name, t in THEMES.items():
        (OUT / f"banner-{name}.svg").write_text(banner(t))
        for pr in PROJECTS:
            (OUT / f"work-{pr.slug}-{name}.svg").write_text(strip(pr, t))
    print("\n".join(sorted(f.name for f in OUT.glob("*.svg"))))


if __name__ == "__main__":
    main()
