"""Builds the animated header of the profile README (assets/header-clear-*.svg).

GitHub serves README images through <img>, so an SVG cannot load web fonts
and the viewer's own fonts are unknown. The text is therefore shaped with
HarfBuzz and outlined to <path> here: the header renders the same everywhere.

Two variants, picked by <picture> in the README: dark and light. There is no
background slab: the name sits on the page and follows GitHub's theme.
The letters rise one by one, then the cyan rule draws itself, then the
subtitle fades in. Everything stays still under prefers-reduced-motion.

Run from the repo root after editing the text below:
  python -m venv .venv && .venv/bin/pip install fonttools brotli uharfbuzz
  .venv/bin/python tools/build.py
"""

from __future__ import annotations

import io
from pathlib import Path
from xml.sax.saxutils import escape

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "tools" / "fonts"
OUT = ROOT / "assets"

NAME = "Tibxla"
SUBTITLE = "full-stack & AI developer"
W, H = 900, 180

THEMES = {
    "dark": dict(ink="#f0f6fc", rule="#00c6ff", sub="#9198a1"),
    "light": dict(ink="#1f2328", rule="#0a8fd6", sub="#59636e"),
}


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
        return out, (x - track if out else 0.0)

    def glyph_paths(self, text: str, size: float, cx: float, y: float, track: float = 0.0):
        """One path per glyph, the whole line centred on cx."""
        glyphs, w = self.shape(text, size, track)
        x0, s = cx - w / 2, size / self.upm
        paths = []
        for name, gx, gy in glyphs:
            pen = SVGPathPen(self.glyphs, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
            self.glyphs[name].draw(TransformPen(pen, (s, 0, 0, -s, x0 + gx, y - gy)))
            paths.append(pen.getCommands())
        return paths, x0, w


DISPLAY = Face("archivo-narrow-latin-700-normal.woff2")
MONO = Face("ibm-plex-mono-latin-400-normal.woff2")


def header(t: dict) -> str:
    letters, x0, w = DISPLAY.glyph_paths(NAME, 96, W / 2, 110, track=-1)
    sub = "".join(MONO.glyph_paths(SUBTITLE, 15, W / 2, 162)[0])
    name = "".join(
        f'<path class="l" style="animation-delay:{0.12 * i:.2f}s" d="{d}" fill="{t["ink"]}"/>'
        for i, d in enumerate(letters) if d
    )
    css = (
        ".l{animation:up .9s cubic-bezier(.16,1,.3,1) both}"
        "@keyframes up{from{opacity:0;transform:translateY(18px)}}"
        f".u{{stroke-dasharray:{w:.0f};animation:draw 1.1s .8s ease-out both}}"
        f"@keyframes draw{{from{{stroke-dashoffset:{w:.0f}}}}}"
        ".s{animation:fade 1s 1.2s both}@keyframes fade{from{opacity:0}}"
        "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
    )
    title = escape(f"{NAME}, {SUBTITLE}", {'"': "&quot;"})
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-label="{title}"><title>{title}</title><style>{css}</style>'
        f"{name}"
        f'<line class="u" x1="{x0:.1f}" y1="132" x2="{x0 + w:.1f}" y2="132" stroke="{t["rule"]}" stroke-width="2"/>'
        f'<path class="s" d="{sub}" fill="{t["sub"]}"/>'
        "</svg>\n"
    )


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for name, t in THEMES.items():
        (OUT / f"header-clear-{name}.svg").write_text(header(t))
        print(f"assets/header-clear-{name}.svg")


if __name__ == "__main__":
    main()
