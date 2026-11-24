"""PROTOTYPE : en-têtes animés maison pour les variantes A (vague) et D (fondu lettre à lettre)."""
import math, sys
from pathlib import Path
sys.path.insert(0, "/home/tibxla/projects/Tibxla/tools")
import build as b
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

OUT = Path(sys.argv[1])


def glyph_paths(face, text, size, cx, y, track=0.0):
    """Un chemin par glyphe, centré sur cx."""
    glyphs, w = face.shape(text, size, track)
    x0 = cx - w / 2
    s = size / face.upm
    out = []
    for name, gx, gy in glyphs:
        pen = SVGPathPen(face.glyphs, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
        face.glyphs[name].draw(TransformPen(pen, (s, 0, 0, -s, x0 + gx, y - gy)))
        out.append(pen.getCommands())
    return [d for d in out if d]


def wave(base, amp, period, width):
    pts = [f"M0 0 H{width} V{base:.1f}"]
    step = 10
    for x in range(width, -1, -step):
        pts.append(f"L{x} {base + amp * math.sin(2 * math.pi * x / period):.1f}")
    return " ".join(pts) + " Z"


# ---------------------------------------------------------------- A : vague
W, H = 900, 230
P1, P2 = 450, 300
name = b.DISPLAY.path("Tibxla", 84, 0, 0)  # mesure seulement
nw = b.DISPLAY.width("Tibxla", 84, -1)
title = b.DISPLAY.path("Tibxla", 84, W / 2 - nw / 2, 118, track=-1)
sub = b.SANS.path("Full-stack & AI developer", 21, W / 2, 152, anchor="middle")
a = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Tibxla, full-stack and AI developer"><title>Tibxla, full-stack and AI developer</title>
<style>
.w1{{animation:m1 9s linear infinite}}.w2{{animation:m2 13s linear infinite}}
@keyframes m1{{to{{transform:translateX(-{P1}px)}}}}@keyframes m2{{to{{transform:translateX(-{P2 * 2}px)}}}}
.t{{animation:in 1.2s ease-out both}}.s{{animation:in 1.2s .35s ease-out both}}
@keyframes in{{from{{opacity:0;transform:translateY(8px)}}}}
@media (prefers-reduced-motion:reduce){{.w1,.w2,.t,.s{{animation:none}}}}
</style>
<defs><linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="#0F2027"/><stop offset=".5" stop-color="#203A43"/><stop offset="1" stop-color="#2C5364"/></linearGradient>
<clipPath id="c"><rect width="{W}" height="{H}"/></clipPath></defs>
<g clip-path="url(#c)">
<path class="w2" d="{wave(196, 16, P2, W + 2 * P2)}" fill="url(#g)" opacity=".35"/>
<path class="w1" d="{wave(184, 14, P1, W + P1)}" fill="url(#g)"/>
</g>
<path class="t" d="{title}" fill="#fff"/>
<path class="s" d="{sub}" fill="#fff" fill-opacity=".9"/>
</svg>
'''
(OUT / "header-wave.svg").write_text(a)

# ---------------------------------------------------------------- D : fondu lettre à lettre
W, H = 900, 200
letters = glyph_paths(b.DISPLAY, "Tibxla", 96, W / 2, 128, track=-1)
lw = b.DISPLAY.width("Tibxla", 96, -1)
parts = "".join(
    f'<path class="l" style="animation-delay:{0.12 * i:.2f}s" d="{d}"/>' for i, d in enumerate(letters)
)
sub = b.MONO.path("full-stack & AI developer", 15, W / 2, 166, anchor="middle")
d = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Tibxla"><title>Tibxla</title>
<style>
.l{{fill:#f4f4f7;animation:up .9s cubic-bezier(.16,1,.3,1) both}}
@keyframes up{{from{{opacity:0;transform:translateY(18px)}}}}
.u{{stroke-dasharray:{lw:.0f};animation:draw 1.1s .8s ease-out both}}
@keyframes draw{{from{{stroke-dashoffset:{lw:.0f}}}}}
.s{{animation:fade 1s 1.2s both}}@keyframes fade{{from{{opacity:0}}}}
@media (prefers-reduced-motion:reduce){{.l,.u,.s{{animation:none}}}}
</style>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="#000" stroke="#ffffff24"/>
{parts}
<line class="u" x1="{W / 2 - lw / 2:.1f}" y1="142" x2="{W / 2 + lw / 2:.1f}" y2="142" stroke="#00c6ff" stroke-width="2"/>
<path class="s" d="{sub}" fill="#8a8a96"/>
</svg>
'''
(OUT / "header-fade.svg").write_text(d)
print("ok")
