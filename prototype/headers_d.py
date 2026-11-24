"""PROTOTYPE : en-têtes des déclinaisons de D."""
import sys
from pathlib import Path
sys.path.insert(0, "/home/tibxla/projects/Tibxla/tools")
import build as b
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

OUT = Path(sys.argv[1])
W = 900


def glyphs(face, text, size, cx, y, track=0.0):
    """(chemin, x) par glyphe, centrés sur cx ; chemin vide pour une espace."""
    gl, w = face.shape(text, size, track)
    x0 = cx - w / 2
    s = size / face.upm
    out = []
    for name, gx, gy in gl:
        pen = SVGPathPen(face.glyphs, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
        face.glyphs[name].draw(TransformPen(pen, (s, 0, 0, -s, x0 + gx, y - gy)))
        out.append((pen.getCommands(), x0 + gx))
    return out, x0, w


def name_block(fill, y=118, size=96):
    gl, x0, w = glyphs(b.DISPLAY, "Tibxla", size, W / 2, y, track=-1)
    paths = "".join(
        f'<path class="l" style="animation-delay:{0.12 * i:.2f}s" d="{d}" fill="{fill}"/>'
        for i, (d, _) in enumerate(gl) if d
    )
    return paths, x0, w


BASE_CSS = (
    ".l{animation:up .9s cubic-bezier(.16,1,.3,1) both}"
    "@keyframes up{from{opacity:0;transform:translateY(18px)}}"
)


def underline(x0, w, y, color):
    return (
        f'<line class="u" x1="{x0:.1f}" y1="{y}" x2="{x0 + w:.1f}" y2="{y}" stroke="{color}" stroke-width="2" '
        f'style="stroke-dasharray:{w:.0f};animation:draw 1.1s .8s ease-out both"/>'
        f"<style>@keyframes draw{{from{{stroke-dashoffset:{w:.0f}}}}}</style>"
    )


def svg(h, body, css, slab=True):
    rect = f'<rect x=".5" y=".5" width="{W - 1}" height="{h - 1}" rx="14" fill="#000" stroke="#ffffff24"/>' if slab else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}" role="img" '
        f'aria-label="Tibxla, full-stack and AI developer"><title>Tibxla, full-stack and AI developer</title>'
        f"<style>{css}@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}</style>"
        f"{rect}{body}</svg>\n"
    )


# ------------------------------------------------ nom en fondu + ligne tapée, sur fond noir
H = 214
paths, x0, w = name_block("#f4f4f7", y=112)
line = "full-stack & AI developer · I build things and automate the rest"
gl, lx0, lw = glyphs(b.MONO, line, 16, W / 2, 170)
start, dt = 1.5, 0.045
chars = "".join(
    f'<path class="k" style="animation-delay:{start + i * dt:.3f}s" d="{d}"/>' for i, (d, _) in enumerate(gl) if d
)
n = len(gl)
adv = lw / n
css = (
    BASE_CSS
    + ".k{fill:#9c9ca6;opacity:0;animation:on 0s both}@keyframes on{to{opacity:1}}"
    + f".c{{animation:mv {n * dt:.2f}s steps({n}) {start}s both,bl 1s steps(1) {start + n * dt:.2f}s infinite}}"
    + f"@keyframes mv{{from{{transform:translateX(0)}}to{{transform:translateX({lw:.1f}px)}}}}"
    + "@keyframes bl{50%{opacity:0}}"
)
body = paths + underline(x0, w, 134, "#00c6ff") + chars + f'<rect class="c" x="{lx0:.1f}" y="157" width="{adv * .8:.1f}" height="17" fill="#00c6ff"/>'
(OUT / "header-type.svg").write_text(svg(H, body, css))

# ------------------------------------------------ sans fond, sombre et clair
for theme, ink, acc, sub in [("dark", "#f0f6fc", "#00c6ff", "#9198a1"), ("light", "#1f2328", "#0a8fd6", "#59636e")]:
    H = 180
    paths, x0, w = name_block(ink, y=110)
    s = b.MONO.path("full-stack & AI developer", 15, W / 2, 162, anchor="middle")
    css = BASE_CSS + ".s{animation:fade 1s 1.2s both}@keyframes fade{from{opacity:0}}"
    body = paths + underline(x0, w, 132, acc) + f'<path class="s" d="{s}" fill="{sub}"/>'
    (OUT / f"header-clear-{theme}.svg").write_text(svg(H, body, css, slab=False))
print("ok")
