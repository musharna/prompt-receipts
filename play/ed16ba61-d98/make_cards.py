#!/usr/bin/env python3
"""Generate foil collectible insert cards: Night Moth, Comet Fox, Ember Beetle.

Outputs (in ./cards):
  <card>.svg          full-colour artwork with simulated foil + twinkling stars
  <card>-foil.svg     foil mask (100% black = foil) for real foil / spot printing
  sheet-a4.svg        A4 landscape imposition, 2 of each card, with crop marks
  sheet-a4-foil.svg   matching foil mask sheet
  preview.html        browser preview with twinkle + holo shine on hover

Card: 63 x 88 mm trim (standard trading card), 3 mm bleed -> 69 x 94 mm.
"""
import os
import random

W, H, BLEED = 69, 94, 3
CX = W / 2
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cards")

# 4-point sparkle, unit radius
SPARK = ("M0,-1 C0.12,-0.12 0.12,-0.12 1,0 C0.12,0.12 0.12,0.12 0,1 "
         "C-0.12,0.12 -0.12,0.12 -1,0 C-0.12,-0.12 -0.12,-0.12 0,-1Z")

FOILS = {
    # silver holo
    "silver": ["#f4f7ff", "#c9d3ff", "#e6d6ff", "#bfeaff", "#ffffff", "#d8dcf0", "#f4f7ff"],
    # rainbow holo
    "holo": ["#ffd6f5", "#c8b6ff", "#a0e7ff", "#b9ffd8", "#fff3b0", "#ffc8a8", "#ffd6f5"],
    # gold / copper
    "gold": ["#fff1c1", "#e9b949", "#fff6d8", "#d98b3a", "#ffe08a", "#c8742e", "#fff1c1"],
}

CARDS = [
    dict(key="night-moth", no=1, name="NIGHT MOTH", kind="Lunar · Nocturne",
         flavor=("Drinks the moonlight", "others leave behind."),
         foil="silver", bg=("#2b2163", "#0c0a26"), body="#1b1546", seed=11),
    dict(key="comet-fox", no=2, name="COMET FOX", kind="Celestial · Swift",
         flavor=("Leaves a trail of wishes", "wherever it runs."),
         foil="holo", bg=("#14407a", "#050f26"), body="#0b2347", seed=23),
    dict(key="ember-beetle", no=3, name="EMBER BEETLE", kind="Ember · Hearth",
         flavor=("Carries the last warm coal", "of every campfire."),
         foil="gold", bg=("#5a1a0a", "#160504"), body="#2a0b06", seed=37),
]


# ---------------------------------------------------------------- creatures
def moth(F, fill, color):
    wing_u = "M1,-4 C6,-15 18,-18 21.5,-11.5 C24,-6 17,1.5 1.6,1.2 Z"
    wing_l = "M1.6,1.4 C12,1 17.5,7 14.5,13 C11.5,17.5 4,14.5 1.4,7 Z"
    half = f"""
      <path d="{wing_u}" fill="{fill}" stroke="{F}" stroke-width="0.6" stroke-linejoin="round"/>
      <path d="{wing_l}" fill="{fill}" stroke="{F}" stroke-width="0.6" stroke-linejoin="round"/>
      <path d="M2,-2 L18,-11.5 M2,-1 L15,-3.5 M2.5,-3 Q8,-12 13,-15.5 M2,3 L13,11"
            fill="none" stroke="{F}" stroke-width="0.25" stroke-linecap="round"/>
      <circle cx="12" cy="-8" r="3" fill="none" stroke="{F}" stroke-width="0.4"/>
      <circle cx="12" cy="-8" r="1.3" fill="{F}"/>
      <circle cx="9" cy="8.5" r="1.7" fill="none" stroke="{F}" stroke-width="0.35"/>
      <path d="M0.6,-8.6 C2,-13 5,-16 8.5,-17.5" fill="none" stroke="{F}" stroke-width="0.35" stroke-linecap="round"/>
      <path d="M2.6,-12.4 l1.2,-0.3 M4.2,-14.6 l1.2,0 M6,-16.3 l1.1,0.3"
            stroke="{F}" stroke-width="0.25" stroke-linecap="round"/>
    """
    moon = ('<circle cx="0" cy="-4" r="17" fill="url(#moon)"/>' if color else "")
    return f"""
    {moon}
    <g>{half}</g>
    <g transform="scale(-1 1)">{half}</g>
    <ellipse cx="0" cy="2.5" rx="1.7" ry="8.5" fill="{fill}" stroke="{F}" stroke-width="0.5"/>
    <path d="M-1.4,0 h2.8 M-1.5,2.5 h3 M-1.4,5 h2.8 M-1,7.5 h2" stroke="{F}" stroke-width="0.25"/>
    <circle cx="0" cy="-7.2" r="1.9" fill="{fill}" stroke="{F}" stroke-width="0.5"/>
    """


def fox(F, fill, color):
    tail = "M-6.5,-1.5 C-13,-3 -21,3 -26,16 C-19,9 -12,5.5 -5.5,2.5 Z"
    streaks = "M-9,-3.6 C-15,-3 -22,1 -27,9 M-12,6 C-17,9 -21,13 -23,19 M-8,4 C-15,7 -19,12 -21,15.5"
    body = ("M17.5,-9 L12.5,-7.6 L10.4,-4.6 L8.6,-0.8 L10.6,4.6 L13.8,8.6 L11.4,9.6 L6.4,2.6 "
            "L0,3.4 L-4,6.4 L-9.4,11.2 L-10.6,10 L-6.2,1.8 L-7.6,-1.2 L-2,-4.4 L5,-7.2 "
            "L8,-11 L9,-17.4 L11,-12.4 L13.2,-16.8 L13.8,-11.6 Z")
    facets = "M8,-11 L10.4,-4.6 M5,-7.2 L8.6,-0.8 M-2,-4.4 L0,3.4 M5,-7.2 L6.4,2.6 M-6.2,1.8 L0,3.4"
    glow = ('<path d="M-6.5,-1.5 C-13,-3 -21,3 -26,16 C-19,9 -12,5.5 -5.5,2.5 Z" '
            'fill="url(#trail)" opacity="0.8"/>' if color else "")
    return f"""
    {glow}
    <path d="{tail}" fill="{fill if color else 'none'}" fill-opacity="0.35" stroke="{F}" stroke-width="0.5" stroke-linejoin="round"/>
    <path d="{streaks}" fill="none" stroke="{F}" stroke-width="0.3" stroke-linecap="round"/>
    <path d="{body}" fill="{fill}" stroke="{F}" stroke-width="0.6" stroke-linejoin="round"/>
    <path d="{facets}" fill="none" stroke="{F}" stroke-width="0.22" stroke-linecap="round"/>
    <path d="M12.5,-7.6 L10.4,-4.6 L14,-6.4 Z" fill="{F}"/>
    <path d="M13,-10.6 l1.4,-0.4" stroke="{F}" stroke-width="0.55" stroke-linecap="round"/>
    <circle cx="17.5" cy="-9" r="0.55" fill="{F}"/>
    <g transform="translate(-26 16)">
      <path d="{SPARK}" transform="scale(2.6)" fill="{F}"/>
    </g>
    """


def beetle(F, fill, color):
    half = f"""
      <path d="M0.35,-4.5 L7,-4.5 C9.5,1 9.5,10 0.35,16.5 Z" fill="{fill}" stroke="{F}" stroke-width="0.6" stroke-linejoin="round"/>
      <path d="M2.2,-2.5 L4,0.5 L3,3.6 L5.2,7.4 L3.6,11 M4,0.5 L6.6,1.6 M5.2,7.4 L7.4,6.6"
            fill="none" stroke="{'url(#emberline)' if color else F}" stroke-width="0.4" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M6,-8 L11,-11 L13,-16.5 M7,-1 L12.5,0 L15.5,-3.5 M6.5,5 L11,9 L13,14.5"
            fill="none" stroke="{F}" stroke-width="0.55" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M1.4,-15 L4,-19 L7,-20.4 M2.6,-14.6 Q4,-15.5 4.6,-17.2"
            fill="none" stroke="{F}" stroke-width="0.35" stroke-linecap="round"/>
    """
    glow = '<circle cx="0" cy="2" r="22" fill="url(#ember)"/>' if color else ""
    return f"""
    {glow}
    <g>{half}</g>
    <g transform="scale(-1 1)">{half}</g>
    <rect x="-6.5" y="-11" width="13" height="6.2" rx="2.6" fill="{fill}" stroke="{F}" stroke-width="0.6"/>
    <path d="M-3.5,-8 h7" stroke="{F}" stroke-width="0.25"/>
    <ellipse cx="0" cy="-13" rx="3.4" ry="2.4" fill="{fill}" stroke="{F}" stroke-width="0.5"/>
    <circle cx="-1.6" cy="-13.4" r="0.55" fill="{F}"/>
    <circle cx="1.6" cy="-13.4" r="0.55" fill="{F}"/>
    """


ART = {"night-moth": moth, "comet-fox": fox, "ember-beetle": beetle}


# ---------------------------------------------------------------- footer icons
def icon(key, F):
    if key == "night-moth":
        return f'<path d="M1.2,-1.6 A1.8,1.8 0 1 0 1.2,1.6 A1.4,1.4 0 1 1 1.2,-1.6 Z" fill="{F}"/>'
    if key == "comet-fox":
        return (f'<path d="{SPARK}" transform="translate(1 -0.6) scale(1.2)" fill="{F}"/>'
                f'<path d="M0,0 L-2.4,1.6 M0.2,0.6 L-1.6,2" stroke="{F}" stroke-width="0.3" stroke-linecap="round"/>')
    return f'<path d="M0,-2 C1.6,-0.4 1.4,0.6 1,1.6 Q0,2.4 -1,1.6 C-1.4,0.6 -0.6,-0.2 0,-2 Z" fill="{F}"/>'


# ---------------------------------------------------------------- card
def card_body(c, mode):
    """Return (defs, body) for one card. mode = 'color' | 'foil'."""
    color = mode == "color"
    p = c["key"]
    F = f"url(#{p}-foil)" if color else "#000"
    fill = c["body"] if color else "none"
    rnd = random.Random(c["seed"])

    stops = FOILS[c["foil"]]
    gstops = "".join(f'<stop offset="{i / (len(stops) - 1):.3f}" stop-color="{s}"/>'
                     for i, s in enumerate(stops))
    defs = f"""
    <linearGradient id="{p}-foil" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{W}" y2="{H}">{gstops}</linearGradient>
    <radialGradient id="{p}-bg" cx="50%" cy="35%" r="75%">
      <stop offset="0" stop-color="{c['bg'][0]}"/><stop offset="1" stop-color="{c['bg'][1]}"/>
    </radialGradient>
    <clipPath id="{p}-win"><rect x="9" y="9" width="51" height="52" rx="2"/></clipPath>
    """
    if color:
        defs += """
    <radialGradient id="moon"><stop offset="0" stop-color="#fffbe6" stop-opacity="0.55"/>
      <stop offset="0.7" stop-color="#d9d4ff" stop-opacity="0.18"/><stop offset="1" stop-color="#d9d4ff" stop-opacity="0"/></radialGradient>
    <linearGradient id="trail" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#bff4ff" stop-opacity="0.7"/>
      <stop offset="1" stop-color="#bff4ff" stop-opacity="0"/></linearGradient>
    <radialGradient id="ember"><stop offset="0" stop-color="#ff7a1a" stop-opacity="0.55"/>
      <stop offset="0.6" stop-color="#ff3d00" stop-opacity="0.15"/><stop offset="1" stop-color="#ff3d00" stop-opacity="0"/></radialGradient>
    <linearGradient id="emberline" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffe08a"/>
      <stop offset="1" stop-color="#ff5a1f"/></linearGradient>
    """

    out = []
    # background
    out.append(f'<rect width="{W}" height="{H}" fill="{"url(#" + p + "-bg)" if color else "#fff"}"/>')

    # faint dot starfield (ink, not foil)
    if color:
        for _ in range(70):
            x, y = rnd.uniform(0, W), rnd.uniform(0, H)
            r = rnd.choice([0.12, 0.15, 0.2, 0.28])
            cls = ' class="tw2"' if rnd.random() < 0.35 else ""
            out.append(f'<circle{cls} style="animation-delay:{rnd.uniform(0, 4):.2f}s" cx="{x:.2f}" cy="{y:.2f}" '
                       f'r="{r}" fill="#fff" opacity="{rnd.uniform(0.35, 0.9):.2f}"/>')

    # frames
    out.append(f'<rect x="5.5" y="5.5" width="58" height="83" rx="3" fill="none" stroke="{F}" stroke-width="0.8"/>')
    out.append(f'<rect x="6.9" y="6.9" width="55.2" height="80.2" rx="2.2" fill="none" stroke="{F}" stroke-width="0.2"/>')
    for x, y in [(5.5, 5.5), (63.5, 5.5), (5.5, 88.5), (63.5, 88.5)]:
        out.append(f'<path d="M{x},{y - 1.6} L{x + 1.6},{y} L{x},{y + 1.6} L{x - 1.6},{y} Z" fill="{F}"/>')

    # art window
    if color:
        out.append(f'<rect x="9" y="9" width="51" height="52" rx="2" fill="#000" fill-opacity="0.28"/>')
    art = ART[p](F, fill, color)
    dx = 4.5 if p == "comet-fox" else 0  # fox + tail sit off-centre
    out.append(f'<g clip-path="url(#{p}-win)"><g transform="translate({CX + dx} 36)">{art}</g></g>')
    out.append(f'<rect x="9" y="9" width="51" height="52" rx="2" fill="none" stroke="{F}" stroke-width="0.35"/>')

    # twinkling foil sparkles
    sparks = [(14, 15, 1.6), (54, 16, 1.2), (52, 53, 1.8), (16, 54, 1.0), (47, 12, 0.7),
              (13, 33, 0.8), (57, 37, 0.9), (35, 12.5, 0.6)]
    sparks += [(rnd.uniform(11, 58), rnd.uniform(11, 59), rnd.uniform(0.4, 0.75)) for _ in range(6)]
    for i, (x, y, r) in enumerate(sparks):
        out.append(f'<g transform="translate({x:.2f} {y:.2f}) scale({r:.2f})">'
                   f'<path class="tw" style="animation-delay:{(i * 0.37) % 2.6:.2f}s" d="{SPARK}" fill="{F}"/></g>')

    # title + kind
    serif = "Cinzel, 'Cormorant SC', 'Palatino Linotype', Palatino, Georgia, serif"
    out.append(f'<text x="{CX}" y="69.2" text-anchor="middle" font-family="{serif}" font-size="4.3" '
               f'font-weight="700" letter-spacing="0.6" fill="{F}">{c["name"]}</text>')
    out.append(f'<path d="M17,71.8 H52" stroke="{F}" stroke-width="0.2"/>')
    out.append(f'<path d="{SPARK}" transform="translate({CX} 71.8) scale(0.7)" fill="{F}"/>')
    if color:
        out.append(f'<text x="{CX}" y="75.6" text-anchor="middle" font-family="{serif}" font-size="2.2" '
                   f'letter-spacing="0.5" fill="#e8e4ff" fill-opacity="0.8">{c["kind"].upper()}</text>')
        l1, l2 = c["flavor"]
        out.append(f'<text text-anchor="middle" font-family="Georgia, serif" font-style="italic" font-size="2.4" '
                   f'fill="#f3efff" fill-opacity="0.85"><tspan x="{CX}" y="79.2">“{l1}</tspan>'
                   f'<tspan x="{CX}" y="82.2">{l2}”</tspan></text>')

    # footer
    out.append(f'<text x="11" y="85.8" font-family="{serif}" font-size="2" letter-spacing="0.3" '
               f'fill="{F}">No. {c["no"]:02d} / 03</text>')
    out.append(f'<g transform="translate(57 85.1)">{icon(p, F)}</g>')

    return defs, "\n  ".join(out)


STYLE = """
  <style>
    .tw, .tw2 { transform-box: fill-box; transform-origin: center; }
    .tw  { animation: twinkle 2.6s ease-in-out infinite; }
    .tw2 { animation: blink 4s ease-in-out infinite; }
    @keyframes twinkle { 0%,100% { opacity: 1; transform: scale(1) rotate(0deg); }
                         50%     { opacity: .3; transform: scale(.45) rotate(45deg); } }
    @keyframes blink   { 0%,100% { opacity: .9; } 50% { opacity: .1; } }
    @media print, (prefers-reduced-motion: reduce) { .tw, .tw2 { animation: none; } }
  </style>"""


def card_svg(c, mode):
    defs, body = card_body(c, mode)
    style = STYLE if mode == "color" else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">\n'
            f'  <title>{c["name"].title()} — {"foil mask" if mode == "foil" else "insert card"}</title>{style}\n'
            f'  <defs>{defs}</defs>\n  {body}\n</svg>\n')


# ---------------------------------------------------------------- A4 sheet
def sheet_svg(mode):
    SW, SH, GAP = 297, 210, 4
    bw, bh = 3 * W + 2 * GAP, 2 * H + GAP
    ox, oy = (SW - bw) / 2, (SH - bh) / 2
    defs, cards = [], []
    for i, c in enumerate(CARDS):
        d, b = card_body(c, mode)
        defs.append(d)
        cards.append(f'<svg x="{i * (W + GAP)}" y="0" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{b}</svg>')
    marks = []
    xs = [ox + i * (W + GAP) + t for i in range(3) for t in (BLEED, W - BLEED)]
    ys = [oy + j * (H + GAP) + t for j in range(2) for t in (BLEED, H - BLEED)]
    for x in xs:
        marks.append(f'M{x:.2f},{oy - 7} V{oy - 2} M{x:.2f},{oy + bh + 2} V{oy + bh + 7}')
    for y in ys:
        marks.append(f'M{ox - 7},{y:.2f} H{ox - 2} M{ox + bw + 2},{y:.2f} H{ox + bw + 7}')
    style = STYLE if mode == "color" else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{SW}mm" height="{SH}mm" viewBox="0 0 {SW} {SH}">{style}\n'
            f'<defs>{"".join(defs)}</defs>\n<rect width="{SW}" height="{SH}" fill="#fff"/>\n'
            f'<g id="row" transform="translate({ox} {oy})">{"".join(cards)}</g>\n'
            f'<use href="#row" xlink:href="#row" y="{H + GAP}"/>\n'
            f'<path d="{" ".join(marks)}" stroke="#000" stroke-width="0.15" fill="none"/>\n</svg>\n')


# ---------------------------------------------------------------- preview
PREVIEW = """<!doctype html>
<html lang="en"><meta charset="utf-8"><title>Foil insert cards</title>
<style>
  body { margin: 0; min-height: 100vh; display: flex; flex-wrap: wrap; gap: 48px; align-items: center;
         justify-content: center; background: radial-gradient(#22223a, #0b0b14); font-family: Georgia, serif; }
  .card { position: relative; width: 252px; height: 352px; border-radius: 12px; overflow: hidden;
          box-shadow: 0 20px 40px #0009; transition: transform .25s; transform-style: preserve-3d; }
  .card object { position: absolute; width: 276px; height: 376px; left: -12px; top: -12px; pointer-events: none; }
  .card::after { content: ""; position: absolute; inset: 0; pointer-events: none; mix-blend-mode: color-dodge;
          background: linear-gradient(115deg, transparent 30%, #ffffff55 45%, #a0e7ff44 50%, #ffd6f566 55%, transparent 70%);
          background-size: 250% 250%; background-position: var(--px, 100%) var(--py, 100%); opacity: .8; }
  p { width: 100%; text-align: center; color: #aab; font-size: 13px; margin: 0 0 -24px; }
</style>
<p>Hover to tilt. Shown at trim size (bleed hidden).</p>
__CARDS__
<script>
  document.querySelectorAll('.card').forEach(el => {
    el.addEventListener('pointermove', e => {
      const r = el.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
      el.style.transform = `perspective(700px) rotateY(${(x - .5) * 18}deg) rotateX(${(.5 - y) * 18}deg)`;
      el.style.setProperty('--px', `${x * 100}%`); el.style.setProperty('--py', `${y * 100}%`);
    });
    el.addEventListener('pointerleave', () => { el.style.transform = ''; });
  });
</script>
</html>
"""


def main():
    os.makedirs(OUT, exist_ok=True)
    for c in CARDS:
        for mode, suffix in (("color", ""), ("foil", "-foil")):
            with open(os.path.join(OUT, f"{c['key']}{suffix}.svg"), "w") as f:
                f.write(card_svg(c, mode))
    for mode, suffix in (("color", ""), ("foil", "-foil")):
        with open(os.path.join(OUT, f"sheet-a4{suffix}.svg"), "w") as f:
            f.write(sheet_svg(mode))
    cards = "\n".join(f'<div class="card"><object type="image/svg+xml" data="{c["key"]}.svg"></object></div>'
                      for c in CARDS)
    with open(os.path.join(OUT, "preview.html"), "w") as f:
        f.write(PREVIEW.replace("__CARDS__", cards))
    print("wrote", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
