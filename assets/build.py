"""Generates the profile SVG cards and README.md. Run from the repo root: python assets/build.py
Icon paths come from assets/icons.json (refresh with assets/fetch_icons.py). The prose
lives in assets/content.json and is copied into README.md verbatim; edit it there.

Hanami in two lights. Every card is built twice and the README picks one per
theme with <picture>: on light, an ink bough on GitHub's white page; on dark, a
night hanami with the bough in gold maki-e brushwork on black lacquer. The card
background is the exact page colour and the artwork feathers out at the edges,
so nothing reads as a rectangle sitting on the page."""
import io, json, html, math, random

MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace"
SERIF = "Georgia, 'Times New Roman', 'DejaVu Serif', serif"
CH12, CH13, CH15 = 7.22, 7.82, 9.02  # mono advance widths
HANDLE = "@XxMasterepicxX"
WASH = ["#FBD3E3", "#F7B6D0", "#F19BC0", "#E97AAE"]
FLOWERS = ["#FFE6F0", "#FBC6DC", "#F5A3C8", "#EC78B0", "#DC4A94", "#C22A78"]
FLOWERS_W = [2, 4, 5, 5, 3, 2]
PETAL = "M0,0C-2.6,-2.4 -6.2,-5.6 -3.8,-8.6C-2.4,-10.3 -0.6,-9.4 0,-8.1C0.6,-9.4 2.4,-10.3 3.8,-8.6C6.2,-5.6 2.6,-2.4 0,0Z"
LOOSE = "M0,-5C3.2,-5 4.6,-1 0,5C-4.6,-1 -3.2,-5 0,-5Z"

THEMES = {
    "light": dict(
        page="#FFFFFF", stroke="#1B1410", streak="#FFFFFF", spatter="#1B1410",
        text="#241609", dim="#4A3A22", muted="#7A6540", wm="#7A6540", rule="#B7282E",
        tag="#B5185C", outline="#1B1410", outline_fill="#FFF3F8", eye="#8E1548",
        wash_op=0.5, glow=[("#FFD2A6", 1), ("#F9BDBE", 0.7), ("#F7B9CC", 0)], disc=None,
        mist="#F3B9CF", mist_op=0.45,
        accents=("#B5185C", "#4F8A0B", "#8C4A1E"),
        # validated against white with the dataviz palette checker; Other is deliberately neutral
        langs={"TypeScript": "#2F6FBF", "Python": "#3E8E1E", "C#": "#B5185C", "JavaScript": "#A88600",
               "C++": "#6B3FA0", "Java": "#C2571A", "Other": "#A89C7A"},
        track="#EEE8D6", icon_blend=("#1B1410", "dark")),
    "dark": dict(
        page="#0D1117", stroke="url(#gold)", streak="#0D1117", spatter="#C9A452",
        text="#F2E9D8", dim="#B8AE98", muted="#8B7D63", wm="#6E6352", rule="#C9A452",
        tag="#F06AA8", outline="#E2C27A", outline_fill="#2A1622", eye="#E2C27A",
        wash_op=0.42, glow=[("#F4EEDC", 0.5), ("#B9A7C9", 0.16), ("#8E7FA6", 0)], disc="#F6F0DE",
        mist="#4A1740", mist_op=0.7,
        accents=("#F06AA8", "#8BC34A", "#D6A15F"),
        # validated against #0D1117 with the dataviz palette checker
        langs={"TypeScript": "#3F86D8", "Python": "#4FAE2F", "C#": "#DE4A90", "JavaScript": "#A6861A",
               "C++": "#9A6FE0", "Java": "#CC6A2C", "Other": "#6E7681"},
        track="#1C2230", icon_blend=("#FFFFFF", "light")),
}

ICONS = json.load(open("assets/icons.json", encoding="utf-8"))
OVERRIDE = {"light": {"JavaScript": "#8F7B00", "Linux": "#8A6E00", "Tailwind": "#0891B2",
                      "AWS": "#C46A00", "React": "#1B8DB0"},
            "dark": {"Java": "#E76F00", "Fastify": "#C9D1D9", "Django": "#44B78B",
                     "SQLite": "#4AA3C7", "Prisma": "#7B8CFF", "ONNX": "#4C8DFF"}}


def lerp_hex(a, b, t):
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02X%02X%02X" % tuple(round(x + (y - x) * t) for x, y in zip(ca, cb))


def readable(name, theme):
    """Brand colour nudged toward the text colour when it would vanish on this page."""
    hexv = OVERRIDE[theme].get(name) or ICONS[name]["hex"]
    r, g, b = (int(hexv[i:i + 2], 16) for i in (1, 3, 5))
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    target, mode = THEMES[theme]["icon_blend"]
    if mode == "dark":
        return hexv if lum <= 150 else lerp_hex(hexv, target, 0.45 if lum > 190 else 0.28)
    return hexv if lum >= 90 else lerp_hex(hexv, target, 0.55 if lum < 60 else 0.32)


# ------------------------------------------------ shared defs
def flower_symbol(id_, rot, T, outline=False):
    style = f' stroke="{T["outline"]}" stroke-width="0.9" stroke-linejoin="round"' if outline else ''
    petals = ''.join(f'<path d="{PETAL}" transform="rotate({rot + k * 72})"{style}/>' for k in range(5))
    eye = (f'<circle r="1.4" fill="{T["eye"]}" opacity="0.85"/>' if outline else
           '<circle r="1.5" fill="#8E1548" opacity="0.85"/>')
    stamens = ''.join(f'<circle cx="{2 * math.cos(math.radians(rot + 36 + k * 72)):.1f}" '
                      f'cy="{2 * math.sin(math.radians(rot + 36 + k * 72)):.1f}" r="0.5"/>' for k in range(5))
    return (f'<symbol id="{id_}" viewBox="-10 -10 20 20">{petals}{eye}'
            f'<g fill="{T["eye"] if outline else "#FFE9A8"}">{stamens}</g></symbol>')


def defs(w, h, T, fl=80, fr=80, ft=40, fb=56):
    """Card defs. The two feather masks nest, so they multiply: every edge of the art fades into the page
    over its own width (left, right, top, bottom), and corners fade on both axes."""
    fade = lambda i, x1, y1, x2, y2: (f'<linearGradient id="{i}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">'
                                     f'<stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient>')
    return (f'<clipPath id="card"><rect width="{w}" height="{h}"/></clipPath>\n'
            f'    <linearGradient id="gold" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{w}" y2="{h}">'
            f'<stop offset="0" stop-color="#8F6E2C"/><stop offset="0.45" stop-color="#C9A452"/><stop offset="1" stop-color="#E6C878"/></linearGradient>\n'
            f'    {fade("fR", 0, 0, 1, 0)}{fade("fL", 1, 0, 0, 0)}{fade("fB", 0, 0, 0, 1)}{fade("fT", 0, 1, 0, 0)}\n'
            f'    <mask id="feathH" maskUnits="userSpaceOnUse" x="{-w}" y="{-h}" width="{3 * w}" height="{3 * h}"><rect width="{w}" height="{h}" fill="#fff"/>'
            f'<rect x="{w - fr}" width="{fr}" height="{h}" fill="url(#fR)"/>'
            f'<rect width="{fl}" height="{h}" fill="url(#fL)"/></mask>\n'
            f'    <mask id="feathV" maskUnits="userSpaceOnUse" x="{-w}" y="{-h}" width="{3 * w}" height="{3 * h}"><rect width="{w}" height="{h}" fill="#fff"/>'
            f'<rect y="{h - fb}" width="{w}" height="{fb}" fill="url(#fB)"/>'
            f'<rect width="{w}" height="{ft}" fill="url(#fT)"/></mask>\n'
            f'    <filter id="rough" x="-15%" y="-15%" width="130%" height="130%">'
            f'<feTurbulence type="fractalNoise" baseFrequency="0.11" numOctaves="3" seed="3" result="n"/>'
            f'<feDisplacementMap in="SourceGraphic" in2="n" scale="3.2" xChannelSelector="R" yChannelSelector="G"/></filter>\n'
            f'    <filter id="wash" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="5"/></filter>\n'
            f'    <filter id="bokeh" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="2.2"/></filter>\n'
            f'    {flower_symbol("f0", 0, T)}{flower_symbol("f1", 24, T)}{flower_symbol("f2", 48, T)}{flower_symbol("fo", 12, T, True)}')


def card(w, h, art, ui, T, extra_defs="", feather=True, fx=None, fy=None):
    """art is feathered into the page on all four edges; ui (text, marks, watermark) is not.
    fx / fy override the horizontal / vertical feather widths; defaults scale with the card."""
    fx = fx if fx is not None else min(80, round(w * 0.1))
    fy = fy if fy is not None else min(56, round(h * 0.34))
    feather = feather and bool(art)
    inner = f'<g mask="url(#feathV)"><g mask="url(#feathH)">{art}</g></g>' if feather else art
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
            f'  <defs>\n    {defs(w, h, T, fx, fx, min(40, fy), fy)}{extra_defs}\n  </defs>\n'
            f'  <rect width="{w}" height="{h}" fill="{T["page"]}"/>\n'
            f'  <g clip-path="url(#card)">{inner}{ui}</g>\n</svg>\n')


def watermark(w, h, T):
    return (f'<text x="{w - 26}" y="{h - 14}" text-anchor="end" font-family="{MONO}" font-size="10.5" '
            f'letter-spacing="1.2" fill="{T["wm"]}" opacity="0.55">{HANDLE}</text>')


# ------------------------------------------------ brush
def cubic(p, t):
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = p
    u = 1 - t
    return (u ** 3 * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t ** 3 * x3,
            u ** 3 * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t ** 3 * y3)


def brush(rng, p, w0, n=30, tip=0.7, press=True):
    """A brush stroke: a tapered polygon along a cubic with a wobbling edge, plus dry-brush streaks."""
    raw = [rng.uniform(-1, 1) for _ in range(n + 3)]
    noise = [(raw[i] + raw[i + 1] + raw[i + 2]) / 3 for i in range(n + 1)]
    L, R, C = [], [], []
    for i in range(n + 1):
        t = i / n
        x, y = cubic(p, t)
        x2, y2 = cubic(p, min(t + 0.01, 1))
        x1, y1 = cubic(p, max(t - 0.01, 0))
        dx, dy = x2 - x1, y2 - y1
        d = math.hypot(dx, dy) or 1
        nx, ny = -dy / d, dx / d
        wdt = (w0 * (1 - t) ** 0.5 * (1 + 0.22 * noise[i]) + tip) * min(1.0, (1 - t) * 7)  # lifts to a point
        if press:
            wdt *= 0.8 + 0.2 * min(1, t * 6)
        L.append((x + nx * wdt / 2, y + ny * wdt / 2))
        R.append((x - nx * wdt / 2, y - ny * wdt / 2))
        C.append((x, y, nx, ny, wdt))
    d = "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in L + R[::-1]) + "Z"
    streaks = []
    wide = w0 > 10
    for _ in range(3 if wide else (2 if w0 > 6 else 1)):
        off = rng.uniform(-0.36, 0.36)
        pl = " ".join(f"{x + nx * wdt * off:.1f},{y + ny * wdt * off:.1f}" for x, y, nx, ny, wdt in C[3:-5])
        if wide:  # long irregular hairlines, faint, so the limb reads as dry ink rather than a ladder
            dash = f"{rng.randint(12, 30)} {rng.randint(5, 11)} {rng.randint(20, 44)} {rng.randint(7, 14)}"
            streaks.append(f'<polyline points="{pl}" stroke-width="0.55" opacity="0.55" stroke-dasharray="{dash}" stroke-dashoffset="{rng.randint(0, 40)}"/>')
        else:
            streaks.append(f'<polyline points="{pl}" stroke-dasharray="{rng.randint(5, 12)} {rng.randint(3, 7)} {rng.randint(9, 18)} {rng.randint(2, 5)}"/>')
    return d, ''.join(streaks)


ROOT = []  # curves of every stroke grown, so twigs can be hung from a known point


def bough(rng, start, direction, length, w0, depth=0, max_depth=3, keep=lambda x, y: True):
    """Grow a brush bough recursively. Returns (strokes, streaks, cluster points)."""
    ang = direction
    ex, ey = start[0] + math.cos(ang) * length, start[1] + math.sin(ang) * length
    if not keep(ex, ey):
        return [], [], []
    bend = rng.uniform(-0.28, 0.28) * length
    nx, ny = -math.sin(ang), math.cos(ang)
    p = (start,
         (start[0] + math.cos(ang) * length * 0.33 + nx * bend, start[1] + math.sin(ang) * length * 0.33 + ny * bend),
         (start[0] + math.cos(ang) * length * 0.66 - nx * bend * 0.6, start[1] + math.sin(ang) * length * 0.66 - ny * bend * 0.6),
         (ex, ey))
    d, streak = brush(rng, p, w0)
    strokes, streaks, clusters = [(w0, d)], [streak], []
    ROOT.append(p)
    if depth >= 1:
        for t in [rng.uniform(0.25, 0.5), rng.uniform(0.6, 0.85), 1.0]:
            if rng.random() < 0.8:
                clusters.append((depth, *cubic(p, t)))
    if depth == max_depth:
        return strokes, streaks, clusters
    n = [6, 3, 2][depth] if depth < 3 else 0
    ratio = [0.3, 0.5, 0.55][depth]
    for i in range(n):
        t = rng.uniform(0.25, 0.95) if depth else 0.12 + 0.85 * (i + rng.uniform(0.15, 0.85)) / n
        sx, sy = cubic(p, t)
        x2, y2 = cubic(p, min(t + 0.02, 1))
        tang = math.atan2(y2 - sy, x2 - sx)
        side = rng.choice([-1, 1])
        for attempt in range(4):  # a twig that would leave the frame tries again shorter and flatter
            na = tang + side * rng.uniform(0.35, 1.0) * (1 - attempt * 0.2)
            if math.sin(na) > 0.75:
                na = tang + side * 0.4
            nlen = length * ratio * rng.uniform(0.8, 1.2) * (1 - attempt * 0.2)
            s, k, c = bough(rng, (sx, sy), na, nlen, w0 * rng.uniform(0.38, 0.5), depth + 1, max_depth, keep)
            if s:
                strokes += s
                streaks += k
                clusters += c
                break
            side = -side
    return strokes, streaks, clusters


def blossoms(rng, clusters, T, scale=1.0):
    """Watercolour clusters: a soft wash, filled and outlined flowers, a bud or two. Grouped by depth for bloom-in."""
    layers, washes = {}, []
    for depth, x, y in clusters:
        spread = (9 + depth * 2) * scale
        washes.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{spread * 1.5:.0f}" fill="{rng.choice(WASH)}"/>')
        items = layers.setdefault(depth, [])
        for _ in range(rng.randint(2, 4)):
            a, dd = rng.uniform(0, math.tau), rng.uniform(0, spread)
            s = rng.uniform(9, 14) * scale
            fx, fy = x + math.cos(a) * dd - s / 2, y + math.sin(a) * dd - s / 2
            if rng.random() < 0.22:
                items.append(f'<use href="#fo" x="{fx:.0f}" y="{fy:.0f}" width="{s:.0f}" height="{s:.0f}" fill="{T["outline_fill"]}" opacity="0.92"/>')
            else:
                col = rng.choices(FLOWERS, FLOWERS_W)[0]
                items.append(f'<use href="#f{rng.randrange(3)}" x="{fx:.0f}" y="{fy:.0f}" width="{s:.0f}" height="{s:.0f}" fill="{col}" opacity="0.94"/>')
        for _ in range(rng.randint(1, 2)):
            a, dd = rng.uniform(0, math.tau), rng.uniform(spread * 0.6, spread * 1.3)
            bx, by = x + math.cos(a) * dd, y + math.sin(a) * dd
            r = rng.uniform(1.6, 2.6) * scale
            items.append(f'<circle cx="{bx:.0f}" cy="{by:.0f}" r="{r:.1f}" fill="{FLOWERS[4]}"/>'
                         f'<circle cx="{bx:.0f}" cy="{by:.0f}" r="{r + 0.9:.1f}" fill="none" stroke="{T["outline"]}" stroke-width="0.7" opacity="0.7"/>')
    wash_svg = f'<g opacity="{T["wash_op"]}" filter="url(#wash)">{"".join(washes)}</g>'
    layer_svg = ''.join(f'<g class="bd{d}">{"".join(v)}</g>' for d, v in sorted(layers.items()))
    return wash_svg + layer_svg


def ink(strokes, streaks, T):
    body = ''.join(f'<path d="{d}"/>' for _, d in sorted(strokes, key=lambda s: -s[0]))
    return (f'<g fill="{T["stroke"]}">{body}</g>'
            f'<g fill="none" stroke="{T["streak"]}" stroke-width="0.9" opacity="0.55">{"".join(streaks)}</g>')


def spatter(rng, x_range, y_range, n, T):
    return f'<g fill="{T["spatter"]}">' + ''.join(
        f'<circle cx="{rng.uniform(*x_range):.0f}" cy="{rng.uniform(*y_range):.0f}" r="{rng.uniform(0.5, 2.1):.1f}" opacity="{rng.uniform(0.35, 0.8):.2f}"/>'
        for _ in range(n)) + '</g>'


def petals(rng, n, x_range, y_range, big=0):
    """Petals on the wind: CSS keyframes carry them down and left, SMIL tumbles and flutters them."""
    out = []
    for i in range(n + big):
        fore = i >= n
        x0, y0 = rng.uniform(*x_range), rng.uniform(*y_range)
        kf = rng.choice(["fA", "fB", "fC"])
        dur, delay = (rng.uniform(16, 22) if fore else rng.uniform(9, 15)), -rng.uniform(0, 15)
        spin, flut = rng.uniform(3, 6), rng.uniform(1.1, 2.2)
        col = rng.choices(FLOWERS[1:5], [3, 4, 3, 1])[0]
        sc = rng.uniform(2.6, 3.4) if fore else rng.uniform(0.7, 1.2)
        extra = ' filter="url(#bokeh)" opacity="0.5"' if fore else ' opacity="0.9"'
        out.append(
            f'<g transform="translate({x0:.0f},{y0:.0f})"><g style="animation:{kf} {dur:.1f}s linear {delay:.1f}s infinite">'
            f'<g><animateTransform attributeName="transform" type="rotate" from="0" to="{rng.choice([360, -360])}" '
            f'dur="{spin:.1f}s" repeatCount="indefinite"/>'
            f'<g><animateTransform attributeName="transform" type="scale" values="1 1;0.3 1;1 1" '
            f'dur="{flut:.1f}s" repeatCount="indefinite"/>'
            f'<path d="{LOOSE}" transform="scale({sc:.2f})" fill="{col}"{extra}/></g></g></g></g>')
    return ''.join(out)


PETAL_CSS = """
      @keyframes fA{0%{transform:translate(0,0);opacity:0}5%{opacity:1}25%{transform:translate(-40px,70px)}50%{transform:translate(-110px,140px)}75%{transform:translate(-170px,215px)}92%{opacity:.9}100%{transform:translate(-240px,320px);opacity:0}}
      @keyframes fB{0%{transform:translate(0,0);opacity:0}5%{opacity:1}30%{transform:translate(-70px,95px)}55%{transform:translate(-90px,170px)}80%{transform:translate(-190px,250px)}92%{opacity:.9}100%{transform:translate(-230px,320px);opacity:0}}
      @keyframes fC{0%{transform:translate(0,0);opacity:0}5%{opacity:1}20%{transform:translate(-18px,62px)}45%{transform:translate(-72px,140px)}70%{transform:translate(-96px,220px)}92%{opacity:.9}100%{transform:translate(-150px,320px);opacity:0}}"""
BLOOM_CSS = ("@keyframes bloom{from{opacity:0}to{opacity:1}}"
             + ''.join(f".bd{d}{{animation:bloom .9s ease-out {1.1 + d * 0.28:.2f}s both}}" for d in range(4)))


def corner_twig(rng, w, T, ang=155, length=180, w0=10, scale=1.0, keep=lambda x, y: True):
    """A brush twig hanging into a card from the top-right corner, blossoms and all."""
    s, k, c = bough(rng, (w + 12, -8), math.radians(ang), length, w0, 1, 3, keep)
    c = [x for x in c if x[2] > -6]
    return (f'<g transform="translate({w},0) scale({scale}) translate({-w},0)">'
            f'{ink(s, k, T)}{blossoms(rng, c, T, 0.9)}</g>')


# ------------------------------------------------ content
TAGLINES = [
    "I like building the whole thing, database to UI",
    "Desktop apps, agents, pipelines, dashboards",
    "Right now: Ghost, a proactive AI assistant",
]
GROUPS = [
    ("LANGUAGES", ["TypeScript", "Python", "C#", "JavaScript", "C++", "Java"]),  # ordered by share, see languages card
    ("FRAMEWORKS", [".NET", "React", "Node", "Fastify", "FastAPI", "Django", "Electron", "Vite", "Tailwind", "Prisma"]),
    ("DATA, ML &amp; INFRA", ["PostgreSQL", "SQLite", "AWS", "BigQuery", "Firebase", "Docker", "PyTorch", "scikit-learn", "ONNX", "Actions", "Linux"]),
]
LANGS = [("TypeScript", 57.0), ("Python", 30.0), ("C#", 5.8), ("JavaScript", 2.2), ("C++", 1.1), ("Java", 0.9), ("Other", 3.0)]


def build(theme):
    T = THEMES[theme]
    W, H = 1000, 300
    rng = random.Random(23)
    ROOT.clear()

    def keep(x, y):
        # the name owns the lower left; the bough lives in the upper band and the right half
        if x < 560:
            return y < 118 and x > 260
        return -30 < y < 250 and x < W + 40

    strokes, streaks, clusters = bough(rng, (W + 30, 34), math.radians(175), 700, 24, 0, 3, keep)
    main = ROOT[0]
    for start, ang, length, w0 in [((W + 20, 60), 150, 330, 12), (cubic(main, 0.5), 108, 150, 8)]:
        s2, k2, c2 = bough(rng, start, math.radians(ang), length, w0, 1, 3, keep)
        strokes += s2
        streaks += k2
        clusters += c2
    clusters = [c for c in clusters if 0 < c[2] < H - 20]

    n = len(TAGLINES)
    cycle = 4.2 * n
    css, txt = [], []
    for i, t in enumerate(TAGLINES):
        a, b = i * 100 / n, (i + 1) * 100 / n
        css.append(f"@keyframes tl{i}{{0%,{max(a - 1, 0):.1f}%{{opacity:0;transform:translateY(6px)}}"
                   f"{a + 2:.1f}%,{b - 4:.1f}%{{opacity:1;transform:translateY(0)}}"
                   f"{b - 1:.1f}%,100%{{opacity:0;transform:translateY(-6px)}}}}")
        css.append(f".tl{i}{{animation:tl{i} {cycle:.1f}s infinite ease-in-out}}")
        txt.append(f'<g class="tl{i}"><text class="tl" x="60" y="246">{html.escape(t)}</text>'
                   f'<rect class="cur" x="{60 + len(t) * CH15 + 5:.0f}" y="234" width="8" height="16"/></g>')

    glow = ''.join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{op}"/>' for o, (c, op) in zip(("0%", "60%", "100%"), T["glow"]))
    hdr_defs = f"""
    <radialGradient id="glow" cx="0.5" cy="0.5" r="0.5">{glow}</radialGradient>
    <radialGradient id="mist" cx="0.5" cy="1" r="0.5">
      <stop offset="0%" stop-color="{T["mist"]}" stop-opacity="{T["mist_op"]}"/><stop offset="100%" stop-color="{T["mist"]}" stop-opacity="0"/>
    </radialGradient>
    <clipPath id="reveal"><rect x="{W}" y="-40" width="{W + 80}" height="{H + 80}">
      <animate attributeName="x" from="{W}" to="-80" dur="1.5s" begin="0.1s" fill="freeze" calcMode="spline" keySplines="0.5 0 0.3 1" keyTimes="0;1"/>
    </rect></clipPath>
    <style>
      .name{{font:700 54px {SERIF};fill:{T["text"]};letter-spacing:-0.5px}}
      .role{{font:400 12px {MONO};fill:{T["muted"]};letter-spacing:6px}}
      .tl{{font:400 15px {MONO};fill:{T["tag"]}}}
      .cur{{fill:{T["tag"]};animation:blink 1s steps(1) infinite}}
      @keyframes blink{{0%,50%{{opacity:1}}50.01%,100%{{opacity:0}}}}
      {''.join(css)}{PETAL_CSS}
      {BLOOM_CSS}
      @keyframes rise{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}
      .rise{{animation:rise 1.1s ease-out .3s both}}
    </style>"""
    disc = f'<circle cx="700" cy="118" r="62" fill="{T["disc"]}" opacity="0.10"/>' if T["disc"] else ''
    art = f"""
    <circle cx="700" cy="118" r="128" fill="url(#glow)"/>{disc}
    <ellipse cx="640" cy="{H}" rx="520" ry="120" fill="url(#mist)"/>
    <g clip-path="url(#reveal)">{ink(strokes, streaks, T)}{spatter(rng, (860, 1000), (10, 90), 22, T)}</g>
    {blossoms(rng, clusters, T)}
    {petals(rng, 34, (520, 1000), (10, 150), big=4)}"""
    ui = f"""
    <g class="rise">
      <text class="role" x="62" y="150">SOFTWARE ENGINEER</text>
      <text class="name" x="60" y="202">Cesar Valentin</text>
      <line x1="60" y1="216" x2="140" y2="216" stroke="{T["rule"]}" stroke-width="2"/>
    </g>
    {''.join(txt)}
    {watermark(W, H, T)}"""
    io.open(f"assets/header-{theme}.svg", "w", encoding="utf-8", newline="\n").write(card(W, H, art, ui, T, hdr_defs))

    # ------------------------------------------------ stack: three columns under brush-dash headings
    rng = random.Random(5)
    COLS = [56, 292, 528]      # x of each group; the third group wraps into a second column
    Y0, ROW, ICON, SPLIT = 82, 28, 17, 6
    parts = []
    rows_used = 0
    for gi, (label, items) in enumerate(GROUPS):
        accent = T["accents"][gi]
        x = COLS[gi]
        dash, _ = brush(rng, ((x, 46), (x + 8, 44), (x + 16, 48), (x + 26, 46)), 5, n=10, tip=1.2)
        parts.append(f'<path d="{dash}" fill="{accent}"/><text class="cat" x="{x + 36}" y="50" fill="{accent}">{label}</text>')
        for j, name in enumerate(items):
            col, row = (j // SPLIT, j % SPLIT) if gi == 2 else (0, j)
            ix, yb = x + col * 160, Y0 + row * ROW
            rows_used = max(rows_used, row + 1)
            parts.append(
                f'<g class="it" style="animation-delay:{gi * 0.06 + col * 0.12 + row * 0.045:.2f}s">'
                f'<g transform="translate({ix},{yb - 13}) scale({ICON / 24:.4f})"><path d="{ICONS[name]["d"]}" fill="{readable(name, theme)}"/></g>'
                f'<text class="ct" x="{ix + 27}" y="{yb}">{html.escape(name)}</text></g>')
    SH = Y0 + (rows_used - 1) * ROW + 40
    stack_defs = f"""
    <style>
      .cat{{font:600 11px {MONO};letter-spacing:2.5px}}
      .ct{{font:400 13px {MONO};fill:{T["text"]}}}
      @keyframes pop{{from{{opacity:0;transform:translateX(-6px)}}to{{opacity:1;transform:translateX(0)}}}}
      .it{{opacity:0;animation:pop .45s ease-out forwards}}{PETAL_CSS}
      {BLOOM_CSS}
    </style>"""
    twig = corner_twig(rng, 1000, T, 150, 250, 13, keep=lambda x, y: x > 870 or y < 28)
    ROOT.clear()
    s, k, c = bough(rng, (-12, SH + 8), math.radians(-28), 190, 9, 1, 3, keep=lambda x, y: x < 420 and y > 255)
    low = ink(s, k, T) + blossoms(rng, [x for x in c if x[2] < SH + 4], T, 0.9)
    art = twig + low + petals(rng, 10, (760, 1010), (-20, 30))
    ui = ''.join(parts) + watermark(1000, SH, T)
    io.open(f"assets/stack-{theme}.svg", "w", encoding="utf-8", newline="\n").write(card(1000, SH, art, ui, T, stack_defs))

    # ------------------------------------------------ languages
    rng = random.Random(9)
    X0, BARY, BARH, GAP = 48, 80, 18, 2
    TRACK = 1000 - X0 * 2 - 120  # leave the right end to the twig
    segs, legend, cx, lx = [], [], X0, X0
    for i, (name, pct) in enumerate(LANGS):
        col = T["langs"][name]
        w = TRACK * pct / 100 - GAP
        segs.append(f'<rect x="{cx:.1f}" y="{BARY}" height="{BARH}" fill="{col}" width="0">'
                    f'<animate attributeName="width" from="0" to="{max(w, 2):.1f}" dur="0.9s" begin="{i * 0.09:.2f}s" '
                    f'fill="freeze" calcMode="spline" keySplines="0.22 1 0.36 1" keyTimes="0;1"/></rect>')
        cx += w + GAP
        lab = f"{name} {pct}%"
        legend.append(f'<circle cx="{lx + 4}" cy="{BARY + 48}" r="4.5" fill="{col}"/>'
                      f'<text class="lg" x="{lx + 16}" y="{BARY + 52}">{html.escape(lab)}</text>')
        lx += 26 + len(lab) * CH12
    lang_defs = f"""
    <clipPath id="bar"><rect x="{X0}" y="{BARY}" width="{TRACK}" height="{BARH}" rx="9"/></clipPath>
    <style>.h{{font:600 21px {SERIF};fill:{T["text"]}}}.s{{font:400 12.5px {MONO};fill:{T["muted"]}}}.lg{{font:400 12.5px {MONO};fill:{T["dim"]}}}{PETAL_CSS}
      {BLOOM_CSS}</style>"""
    art = corner_twig(rng, 1000, T, 150, 130, 8, 0.85) + petals(rng, 5, (800, 1010), (-20, 10))
    ui = f"""
    <text class="h" x="{X0}" y="42">What I actually write</text>
    <text class="s" x="{X0}" y="62">measured across 31 repositories, private ones included</text>
    <g clip-path="url(#bar)"><rect x="{X0}" y="{BARY}" width="{TRACK}" height="{BARH}" fill="{T["track"]}"/>{''.join(segs)}</g>
    {''.join(legend)}
    {watermark(1000, 165, T)}"""
    io.open(f"assets/languages-{theme}.svg", "w", encoding="utf-8", newline="\n").write(card(1000, 165, art, ui, T, lang_defs))


# ------------------------------------------------ the rest of the page
CONTENT = json.load(open("assets/content.json", encoding="utf-8"))
RISE_CSS = "@keyframes rise{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}.rise{animation:rise .9s ease-out .1s both}"
RAW = "https://raw.githubusercontent.com/XxMasterepicxX/XxMasterepicxX/main/assets/"


def linked(p):
    """Blurb plus its repo link. The nameplate itself must not be wrapped in <a>."""
    return p["blurb"] + (f' [See the repo]({p["link"]})' if p.get("link") else "")


def slug(name):
    return ''.join(c if c.isalnum() else '-' for c in name.lower()).strip('-')


def seed(key):
    return sum(ord(c) * (i + 1) for i, c in enumerate(key))


def dash(rng, x, y, color, w=26):
    d, _ = brush(rng, ((x, y), (x + w * 0.3, y - 2), (x + w * 0.6, y + 2), (x + w, y)), 5, n=10, tip=1.2)
    return f'<path d="{d}" fill="{color}"/>'


MARKS = ["sprig", "blossom", "buds", "petals", "fork"]


def mark(rng, x, y, T, kind):
    """One small organic mark, never the same twice: a sprig, a blossom, buds, fallen petals or a fork."""
    out = []
    twig = lambda pts, w: brush(rng, pts, w, n=12, tip=0.9)[0]
    flower = lambda fx, fy, sz, col=None, outline=False: (
        f'<use href="#{"fo" if outline else "f" + str(rng.randrange(3))}" x="{fx - sz / 2:.1f}" y="{fy - sz / 2:.1f}" '
        f'width="{sz:.0f}" height="{sz:.0f}" fill="{T["outline_fill"] if outline else (col or rng.choices(FLOWERS[1:5], [3, 4, 3, 2])[0])}"/>')
    bud = lambda bx, by, r: (f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="{r:.1f}" fill="{FLOWERS[4]}"/>'
                             f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="{r + 0.9:.1f}" fill="none" stroke="{T["outline"]}" stroke-width="0.7" opacity="0.75"/>')
    if kind == "sprig":
        dy = rng.uniform(-8, 8)
        d = twig(((x, y + 5), (x + 9, y + 2 + dy * 0.3), (x + 18, y - 3 + dy), (x + 30, y - 6 + dy)), rng.uniform(2.8, 3.8))
        out.append(f'<path d="{d}" fill="{T["stroke"]}"/>')
        out.append(flower(x + 29, y - 7 + dy, rng.uniform(11, 14)))
        out.append(bud(x + 14, y - 1 + dy * 0.5, rng.uniform(1.6, 2.2)))
    elif kind == "blossom":
        sz = rng.uniform(17, 21)
        out.append(flower(x + 11, y, sz))
        out.append(bud(x + 25, y + rng.uniform(3, 7), rng.uniform(1.6, 2.3)))
        if rng.random() < 0.6:
            out.append(f'<path d="{LOOSE}" transform="translate({x + 30:.0f},{y - 8:.0f}) rotate({rng.uniform(0, 360):.0f}) scale(0.7)" fill="{FLOWERS[2]}" opacity="0.85"/>')
    elif kind == "buds":
        up = rng.choice([-1, 1])
        d = twig(((x, y + 4 * up), (x + 10, y + 1 * up), (x + 20, y - 2 * up), (x + 31, y - 5 * up)), rng.uniform(2.4, 3.2))
        out.append(f'<path d="{d}" fill="{T["stroke"]}"/>')
        out.append(bud(x + 12, y + 1 * up - 4, rng.uniform(1.7, 2.3)))
        out.append(bud(x + 22, y - 2 * up + 4, rng.uniform(1.5, 2.1)))
        out.append(flower(x + 31, y - 6 * up, rng.uniform(9, 12), outline=True))
    elif kind == "petals":
        for i in range(3):
            px, py = x + 5 + i * 11 + rng.uniform(-2, 2), y + rng.uniform(-6, 6)
            out.append(f'<path d="{LOOSE}" transform="translate({px:.0f},{py:.0f}) rotate({rng.uniform(0, 360):.0f}) scale({rng.uniform(0.75, 1.15):.2f})" '
                       f'fill="{rng.choice(FLOWERS[1:5])}" opacity="0.92"/>')
    else:  # fork
        d = twig(((x, y + 6), (x + 8, y + 3), (x + 16, y - 1), (x + 24, y - 4)), rng.uniform(2.6, 3.4))
        d2 = twig(((x + 12, y + 1), (x + 18, y + 5), (x + 24, y + 8), (x + 31, y + 9)), rng.uniform(1.8, 2.4))
        out.append(f'<path d="{d}" fill="{T["stroke"]}"/><path d="{d2}" fill="{T["stroke"]}"/>')
        out.append(flower(x + 25, y - 6, rng.uniform(10, 13)))
        out.append(bud(x + 31, y + 9, rng.uniform(1.6, 2.1)))
    return ''.join(out)


def branch_in(rng, T, w, y0, length, w0, keep, ang=172, scale=1.0):
    """A brush branch sweeping in from the right edge with blossoms, for headings."""
    ROOT.clear()
    s, k, c = bough(rng, (w + 14, y0), math.radians(ang), length, w0, 1, 3, keep)
    return f'<g transform="translate({w},0) scale({scale}) translate({-w},0)">{ink(s, k, T)}{blossoms(rng, c, T, 0.85)}</g>'


def heading(theme, key, title, idx):
    """A section heading: brush dash, serif title, a flower at the far end."""
    """A section heading: an organic mark, serif title, and its own branch sweeping in from the right."""
    T = THEMES[theme]
    rng = random.Random(seed(key))
    W, H = 1000, 66
    ui = (f'<g class="rise">{mark(rng, 38, 38, T, MARKS[idx % len(MARKS)])}'
          f'<text x="84" y="46" font-family="{SERIF}" font-weight="700" font-size="26" fill="{T["text"]}">{html.escape(title)}</text></g>')
    tw = 84 + len(title) * 14.5  # keep the branch clear of the title
    y0, ang = rng.choice([(14, 170), (H - 14, 190), (H / 2, 178)])  # entries sit inside the feather band
    art = (branch_in(rng, T, W, y0, rng.uniform(230, 300), rng.uniform(8, 11), keep=lambda x, y: x > tw + 40 and -20 < y < H + 20, ang=ang)
           + petals(rng, 3, (tw + 80, 980), (-20, -6)))
    css = f'<style>{RISE_CSS}{PETAL_CSS}{BLOOM_CSS}</style>'
    io.open(f"assets/{key}-{theme}.svg", "w", encoding="utf-8", newline="\n").write(card(W, H, art, ui, T, css, fy=24))


def nameplate(theme, key, name, stack, idx):
    """A project's title row: an organic mark, serif name, its stack with brand icons on the right, petals passing."""
    T = THEMES[theme]
    rng = random.Random(seed(key))
    W, H = 780, 58
    parts = [mark(rng, 22, 33, T, MARKS[(idx + 2) % len(MARKS)]),
             f'<text x="62" y="40" font-family="{SERIF}" font-weight="700" font-size="22" fill="{T["text"]}">{html.escape(name)}</text>']
    if stack:
        items = [(t, t in ICONS) for t in stack]
        widths = [(19 if has else 0) + len(t) * CH12 for t, has in items]
        total = sum(widths) + 26 * (len(items) - 1)
        room = W - 24 - (62 + len(name) * 12.8 + 28)
        sc = min(1.0, room / total)
        parts.append(f'<g transform="translate({W - 24},0) scale({sc:.3f}) translate({-(W - 24)},0)">')
        x = W - 24 - total
        for i, ((t, has), wdt) in enumerate(zip(items, widths)):
            if has:
                parts.append(f'<g transform="translate({x:.0f},27) scale({13 / 24:.4f})"><path d="{ICONS[t]["d"]}" fill="{readable(t, theme)}"/></g>')
            parts.append(f'<text x="{x + (19 if has else 0):.0f}" y="38" font-family="{MONO}" font-size="12" fill="{T["dim"]}">{html.escape(t)}</text>')
            x += wdt
            if i < len(items) - 1:
                parts.append(f'<circle cx="{x + 13:.0f}" cy="34" r="1.6" fill="{T["muted"]}"/>')
                x += 26
        parts.append('</g>')
    ui = f'<g class="rise">{"".join(parts)}</g>'
    nw = 62 + len(name) * 13
    art = petals(rng, 3, (nw + 40, W - 30), (-40, -8))
    css = f'<style>{RISE_CSS}{PETAL_CSS}</style>'
    io.open(f"assets/{key}-{theme}.svg", "w", encoding="utf-8", newline="\n").write(card(W, H, art, ui, T, css, fy=20))


def enso(rng, cx, cy, r, w0, start=-100, sweep=332):
    """A brush enso: one open circle, thick where the brush lands, thinning to a lifted tip."""
    n = 60
    raw = [rng.uniform(-1, 1) for _ in range(n + 3)]
    noise = [(raw[i] + raw[i + 1] + raw[i + 2]) / 3 for i in range(n + 1)]
    outer, inner, mid = [], [], []
    for i in range(n + 1):
        t = i / n
        a = math.radians(start + sweep * t)
        wdt = (w0 * (1 - t) ** 0.55 * (1 + 0.25 * noise[i]) + 0.8) * (0.75 + 0.25 * min(1, t * 8)) * min(1.0, (1 - t) * 9)
        outer.append((cx + (r + wdt / 2) * math.cos(a), cy + (r + wdt / 2) * math.sin(a)))
        inner.append((cx + (r - wdt / 2) * math.cos(a), cy + (r - wdt / 2) * math.sin(a)))
        mid.append((a, wdt))
    d = "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in outer + inner[::-1]) + "Z"
    streaks = []
    for off in (rng.uniform(-0.3, -0.1), rng.uniform(0.1, 0.3)):
        pl = " ".join(f"{cx + (r + wdt * off) * math.cos(a):.1f},{cy + (r + wdt * off) * math.sin(a):.1f}" for a, wdt in mid[3:-3])
        streaks.append(f'<polyline points="{pl}" stroke-dasharray="{rng.randint(6, 14)} {rng.randint(3, 6)} {rng.randint(10, 20)} {rng.randint(2, 5)}"/>')
    return d, ''.join(streaks)


def ghost_card(theme):
    """Floats beside the Ghost paragraphs: an enso, the three facts, a quiet pulse, a twig."""
    T = THEMES[theme]
    rng = random.Random(41)
    W, H = 340, 300
    cx, cy = 186, 158
    d, streaks = enso(rng, cx, cy, 102, 14)
    ROOT.clear()
    s, k, c = bough(rng, (W + 10, -6), math.radians(152), 120, 7, 1, 3, keep=lambda x, y: x > 150 and y < 150)
    c = [x for x in c if x[2] > -6]
    art = (f'<g fill="{T["stroke"]}"><path d="{d}"/></g>'
           f'<g fill="none" stroke="{T["streak"]}" stroke-width="0.9" opacity="0.55">{streaks}</g>'
           f'{ink(s, k, T)}{blossoms(rng, c, T, 0.85)}')
    facts = ["160k lines of C#", "runs on your machine", "nothing leaves your disk"]
    ui = (f'<g class="rise"><text x="{cx}" y="150" text-anchor="middle" font-family="{SERIF}" font-weight="700" font-size="32" fill="{T["text"]}">Ghost</text>'
          + ''.join(f'<text x="{cx}" y="{178 + i * 19}" text-anchor="middle" font-family="{MONO}" font-size="10.5" fill="{T["muted"]}">{html.escape(f)}</text>' for i, f in enumerate(facts))
          + f'<circle cx="{cx}" cy="245" r="3" fill="{T["tag"]}"/>'
          f'<circle cx="{cx}" cy="245" r="3" fill="none" stroke="{T["tag"]}" stroke-width="1.2">'
          f'<animate attributeName="r" values="3;15" dur="2.8s" repeatCount="indefinite"/>'
          f'<animate attributeName="opacity" values="0.8;0" dur="2.8s" repeatCount="indefinite"/></circle></g>')
    css = f'<style>{RISE_CSS}{BLOOM_CSS}</style>'
    io.open(f"assets/ghost-{theme}.svg", "w", encoding="utf-8", newline="\n").write(card(W, H, art, ui, T, css))


def pill(theme, key, label):
    """A small link: brush dash, mono label, dotted underline."""
    T = THEMES[theme]
    rng = random.Random(seed(key))
    tw = len(label) * 7.52
    W, H = round(14 + 34 + 8 + tw + 14), 34
    ui = (mark(rng, 10, 17, T, "sprig" if "email" in key else "buds")
          + f'<text x="56" y="21.5" font-family="{MONO}" font-size="12.5" fill="{T["text"]}">{html.escape(label)}</text>'
          f'<line x1="56" y1="27" x2="{56 + tw:.0f}" y2="27" stroke="{T["muted"]}" stroke-width="1" stroke-dasharray="1 3" opacity="0.8"/>')
    io.open(f"assets/{key}-{theme}.svg", "w", encoding="utf-8", newline="\n").write(card(W, H, "", ui, T, feather=False))


def side_art(theme):
    """Floats right of the project list: a bough hanging from the top, twigs and blossoms, petals falling the whole way."""
    T = THEMES[theme]
    rng = random.Random(77)
    W, H = 200, 760
    keep = lambda x, y: 34 < x < W + 30 and -20 < y < H - 30
    ROOT.clear()
    s, k, c = bough(rng, (W + 6, -10), math.radians(99), 330, 12, 0, 3, keep)
    # the second trunk starts inside the first where it is still as wide as the new limb's base, so the join is
    # buried in ink and the first trunk's lifted tip reads as a short fork instead of a gap over a chisel edge
    join = cubic(ROOT[0], 0.66)
    s2, k2, c2 = bough(rng, join, math.radians(93), 440, 8, 0, 3, keep)
    resting = ''.join(
        f'<path d="{LOOSE}" transform="translate({rng.uniform(50, 190):.0f},{rng.uniform(H - 70, H - 40):.0f}) rotate({rng.uniform(0, 360):.0f}) scale({rng.uniform(0.7, 1.1):.2f})" '
        f'fill="{rng.choice(FLOWERS[1:5])}" opacity="0.75"/>' for _ in range(7))
    art = (f'{ink(s + s2, k + k2, T)}{blossoms(rng, c + c2, T, 0.95)}'
           f'{petals(rng, 18, (60, 215), (-20, 440), big=2)}{resting}')
    extra = f'<style>{PETAL_CSS}{BLOOM_CSS}</style>'
    io.open(f"assets/side-{theme}.svg", "w", encoding="utf-8", newline="\n").write(card(W, H, art, "", T, extra, fx=48))


HEADINGS = [("h-working", "What I'm working on"), ("h-built", "Things I've built"),
            ("h-stack", "What I build with"), ("h-numbers", "The numbers")]
STREAK = {
    "dark": "background=0D1117&border=0D1117&stroke=0D1117&ring=C9A452&fire=F06AA8&currStreakNum=F2E9D8&sideNums=F2E9D8&currStreakLabel=F06AA8&sideLabels=8B7D63&dates=8B7D63",
    "light": "background=FFFFFF&border=FFFFFF&stroke=FFFFFF&ring=B7282E&fire=B5185C&currStreakNum=241609&sideNums=241609&currStreakLabel=B5185C&sideLabels=7A6540&dates=7A6540",
}


def picture(key, alt, attrs='width="100%"', inline=False):
    img_attrs = (attrs + " ") if attrs else ""
    nl, ind = ("", "") if inline else ("\n", "  ")
    return (f'<picture>{nl}{ind}<source media="(prefers-color-scheme: dark)" srcset="{RAW}{key}-dark.svg">{nl}'
            f'{ind}<img {img_attrs}src="{RAW}{key}-light.svg" alt="{html.escape(alt, quote=True)}">{nl}</picture>')


def write_readme():
    C = CONTENT
    out = [picture("header", "Cesar Valentin, software engineer"), ""]
    views = "https://komarev.com/ghpvc/?username=XxMasterepicxX&style=flat-square&label=views&color="
    out += ['<p align="center">',
            f'  <a href="mailto:{C["email"]}">{picture("pill-email", "Email " + C["email"], "", inline=True)}</a>',
            f'  <a href="https://github.com/XxMasterepicxX?tab=repositories">{picture("pill-repos", C["repos"], "", inline=True)}</a>',
            f'  <picture>\n  <source media="(prefers-color-scheme: dark)" srcset="{views}C9A452">\n'
            f'  <img src="{views}B5185C" alt="Profile views">\n</picture>',
            '</p>', ""]
    out += [picture("h-working", "What I'm working on"), "",
            picture("ghost", "Ghost: about 160k lines of C#, runs on your machine, nothing leaves your disk", 'align="right" width="340"'), ""]
    for para in C["ghost"]:
        out += [para, ""]
    out += [picture("h-built", "Things I've built"), "",
            picture("side", "", 'align="right" width="16%"'), ""]
    for p in C["projects"]:
        key = "p-" + slug(p["name"])
        pic = picture(key, f'{p["name"]}. Built with {", ".join(p["stack"])}', 'width="72%"')
        out += [pic, "", linked(p), ""]
    out += ["<details>", "<summary><b>More things I've made</b></summary>", "", "<br>", ""]
    for p in C["extras"]:
        pic = picture("p-" + slug(p["name"]), p["name"], 'width="72%"')
        out += [pic, "", linked(p), ""]
    out += ["</details>", "", "<br>", "", C["closing"], ""]
    out += [picture("h-stack", "What I build with"), "",
            picture("stack", "Languages, frameworks and infrastructure I work with"), "",
            picture("h-numbers", "The numbers"), "",
            picture("languages", "Language breakdown across 31 repositories"), ""]
    streak = "https://streak-stats.demolab.com?user=XxMasterepicxX&hide_border=true&border_radius=14&"
    out += ['<p align="center">',
            f'  <picture>\n  <source media="(prefers-color-scheme: dark)" srcset="{streak}{STREAK["dark"]}">\n'
            f'  <img src="{streak}{STREAK["light"]}" alt="Contribution streak">\n</picture>',
            '</p>', ""]
    io.open("README.md", "w", encoding="utf-8", newline="\n").write("\n".join(out))


import xml.dom.minidom as m, os
total = 0
for theme in THEMES:
    build(theme)
    for i, (key, title) in enumerate(HEADINGS):
        heading(theme, key, title, i)
    for i, p in enumerate(CONTENT["projects"] + CONTENT["extras"]):
        nameplate(theme, "p-" + slug(p["name"]), p["name"], p.get("stack", []), i)
    ghost_card(theme)
    side_art(theme)
    pill(theme, "pill-email", CONTENT["email"])
    pill(theme, "pill-repos", CONTENT["repos"])
    for f in sorted(os.listdir("assets")):
        if f.endswith(f"-{theme}.svg"):
            m.parse(f"assets/{f}")
            total += 1
    for f in ("header", "stack", "languages", "ghost"):
        print("valid:", f"{f}-{theme}", os.path.getsize(f"assets/{f}-{theme}.svg") // 1024, "KB")
write_readme()
print("svgs valid:", total, "| README written")
