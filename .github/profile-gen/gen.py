"""Generate animated SVG panels for the takiahmed24 GitHub profile README,
in the portfolio's theme: black + signal red, Figma-style agent cursors that build the page."""
import base64, math, os, random, sys
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.varLib import instancer

FD = os.environ.get('FONT_DIR', 'fonts/')
OUT = sys.argv[1] if len(sys.argv) > 1 else '../../assets'
os.makedirs(OUT, exist_ok=True)

BG, PANEL, LINE, INK, MUTED, RED, RED2, FIG = '#07070A', '#111116', '#22222A', '#F3F1EE', '#8C8A93', '#E3262E', '#FF4D5A', '#2D8CFF'
COLORS = ['#3DD9C5', '#FF6BB5', '#FF9F43', '#A88BFA', '#4DA3FF', '#FFD24D', '#7CE38B', '#FF5F5F']

# ---------------- fonts -> outlines ----------------
def _var(path, axes):
    f = TTFont(path)
    return instancer.instantiateVariableFont(f, axes)
FONTS = {
    'anton': TTFont(FD + 'anton/Anton-Regular.ttf'),
    'body': _var(FD + 'archivo/Archivo[wdth,wght].ttf', {'wght': 500, 'wdth': 100}),
    'bold': _var(FD + 'archivo/Archivo[wdth,wght].ttf', {'wght': 600, 'wdth': 100}),
    'mono': TTFont(FD + 'dmmono/DMMono-Medium.ttf'),
    'script': _var(FD + 'caveat/Caveat[wght].ttf', {'wght': 600}),
}
_cache = {}
def glyphs(fk):
    if fk not in _cache:
        f = FONTS[fk]
        _cache[fk] = (f.getGlyphSet(), f.getBestCmap(), f['hmtx'], f['head'].unitsPerEm)
    return _cache[fk]

import re
_num = re.compile(r'-?\d+\.\d+')
def _rnd(d): return _num.sub(lambda m: ('%.1f' % float(m.group())).rstrip('0').rstrip('.'), d)

def chars(fk, s, size, x, y, ls=0.0):
    """Return list of (char, d, x0, x1) laid out from x at baseline y. ls = letter-spacing in em."""
    gs, cmap, hmtx, upm = glyphs(fk)
    k = size / upm
    out = []
    for ch in s:
        g_s, g_h, kk = gs, hmtx, k
        gn = cmap.get(ord(ch))
        if gn is None:  # fall back to Archivo for symbols (arrows) the font lacks
            g_s, fc, g_h, fupm = glyphs('bold'); kk = size / fupm
            gn = fc.get(ord(ch)) or fc.get(ord('?'))
        adv = g_h[gn][0] * kk
        pen = SVGPathPen(g_s)
        g_s[gn].draw(TransformPen(pen, (kk, 0, 0, -kk, x, y)))
        out.append((ch, _rnd(pen.getCommands()), x, x + adv))
        x += adv + ls * size
    return out

def width(fk, s, size, ls=0.0):
    gs, cmap, hmtx, upm = glyphs(fk)
    tot = 0
    for c in s:
        gn = cmap.get(ord(c))
        if gn is None:
            _, fc, fh, fupm = glyphs('bold'); tot += fh[fc.get(ord(c)) or fc.get(ord('?'))][0] * size / fupm
        else: tot += hmtx[gn][0] * size / upm
    return tot + ls * size * max(0, len(s) - 1)

def text(fk, s, size, x, y, fill=INK, anchor='start', ls=0.0, extra=''):
    w = width(fk, s, size, ls)
    if anchor == 'middle': x -= w / 2
    elif anchor == 'end': x -= w
    d = ''.join(c[1] for c in chars(fk, s, size, x, y, ls))
    return f'<path d="{d}" fill="{fill}" {extra}/>', x, w

def typed(fk, s, size, x, y, t0, t1, fill=INK, ls=0.0, anchor='start'):
    """Characters appear one by one between t0 and t1 (seconds)."""
    w = width(fk, s, size, ls)
    if anchor == 'middle': x -= w / 2
    elif anchor == 'end': x -= w
    cs = [c for c in chars(fk, s, size, x, y, ls)]
    n = max(1, sum(1 for c in cs if c[0].strip()))
    out, i = [], 0
    for ch, d, x0, x1 in cs:
        if not d: continue
        t = t0 + (t1 - t0) * i / n; i += 1
        out.append(f'<path d="{d}" fill="{fill}" opacity="0"><set attributeName="opacity" to="1" begin="{t:.2f}s" fill="freeze"/></path>')
    return ''.join(out), x, w

# ---------------- shared bits ----------------
ARROW = 'M1 1 L1 17 L5.2 13.2 L8.2 20 L11 18.8 L8 12.2 L13.6 12.2 Z'
def defs_common():
    return f'''<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="2" fill="#ffffff06"/></pattern>
<pattern id="rt" width="10" height="16" patternUnits="userSpaceOnUse"><rect width="1" height="6" y="10" fill="#2d8cff66"/></pattern>
<pattern id="rl" width="16" height="10" patternUnits="userSpaceOnUse"><rect width="6" height="1" x="10" fill="#2d8cff66"/></pattern>
<linearGradient id="phg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4a5a72"/><stop offset="1" stop-color="#2c384a"/></linearGradient>'''

def frame_open(w, h, extra_defs=''):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
            f'<defs>{defs_common()}<clipPath id="round"><rect width="{w}" height="{h}" rx="14"/></clipPath>{extra_defs}</defs>'
            f'<g clip-path="url(#round)"><rect width="{w}" height="{h}" fill="{BG}"/>')
def frame_close():
    return '</g></svg>'

def cursor(c, keys, total, idle=None, idle_begin=None, label=None):
    """keys: list of (t, x, y). Build path frozen at the end; optional idle wander loop after."""
    keys = sorted(keys)
    if keys[0][0] > 0: keys = [(0, keys[0][1], keys[0][2])] + keys
    if keys[-1][0] < total: keys.append((total, keys[-1][1], keys[-1][2]))
    vals = ';'.join(f'{x:.1f},{y:.1f}' for _, x, y in keys)
    kt = ';'.join(f'{t / total:.4f}' for t, _, _ in keys)
    spl = ';'.join(['.45 .05 .25 1'] * (len(keys) - 1))
    tag = ''
    if label:
        lw = width('mono', label, 10) + 14
        p, _, _ = text('mono', label, 10, 18, 31, fill='#0b0b0e')
        tag = f'<rect x="11" y="19" width="{lw:.0f}" height="17" rx="3" fill="{c}"/>{p}'
    inner = f'<path d="{ARROW}" fill="{c}" stroke="#000" stroke-opacity=".55" stroke-width="1.1" stroke-linejoin="round"/>{tag}'
    if idle:
        iv = ';'.join(f'{x:.1f},{y:.1f}' for x, y in idle + [idle[0]])
        inner = f'<g><animateTransform attributeName="transform" type="translate" values="{iv}" dur="{random.uniform(7, 11):.1f}s" begin="{idle_begin}s" repeatCount="indefinite" calcMode="spline" keySplines="{";".join([".45 .05 .55 .95"] * len(idle))}"/>{inner}</g>'
    return (f'<g transform="translate({keys[0][1]:.1f},{keys[0][2]:.1f})"><animateTransform attributeName="transform" type="translate" values="{vals}" keyTimes="{kt}" '
            f'calcMode="spline" keySplines="{spl}" dur="{total}s" fill="freeze"/>{inner}</g>')

def selbox(x, y, w, h, name, t0, t1, color=FIG):
    hs = ''.join(f'<rect x="{px - 3.5:.1f}" y="{py - 3.5:.1f}" width="7" height="7" fill="#fff" stroke="{color}"/>' for px, py in [(x, y), (x + w, y), (x, y + h), (x + w, y + h)])
    nm, _, _ = text('mono', name, 10, x, y - 7, fill=color)
    dims = f'{round(w)} × {round(h)}'
    dw = width('mono', dims, 10) + 12
    dp, _, _ = text('mono', dims, 10, x + w / 2, y + h + 17, fill='#fff', anchor='middle')
    body = (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="none" stroke="{color}"/>{hs}{nm}'
            f'<rect x="{x + w / 2 - dw / 2:.1f}" y="{y + h + 6:.1f}" width="{dw:.1f}" height="16" rx="2" fill="{color}"/>{dp}')
    return (f'<g opacity="0"><set attributeName="opacity" to="1" begin="{t0:.2f}s" fill="freeze"/>'
            f'<animate attributeName="opacity" from="1" to="0" begin="{t1:.2f}s" dur=".3s" fill="freeze"/>{body}</g>')

def plus(x, y, c, t):
    return (f'<g opacity="0"><animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.15;.7;1" begin="{t:.2f}s" dur="2.4s" fill="freeze"/>'
            f'<path d="M{x - 7} {y}h14M{x} {y - 7}v14" stroke="{c}" stroke-width="1.6" stroke-linecap="round"/></g>')

def placeholder(x, y, w, h, t0, t1):
    return (f'<g opacity="0"><set attributeName="opacity" to="1" begin="{t0:.2f}s" fill="freeze"/>'
            f'<animate attributeName="opacity" from="1" to="0" begin="{t1:.2f}s" dur=".8s" fill="freeze"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#phg)" stroke="#8fa6c8"/>'
            f'<path d="M{x} {y}L{x + w} {y + h}M{x + w} {y}L{x} {y + h}" stroke="#9fb4d466"/>'
            f'<path d="M{x + w / 2 - 11} {y + h / 2}h22M{x + w / 2} {y + h / 2 - 11}v22" stroke="#cfe0ff" stroke-width="1.4"/></g>')

def appear(inner, t, dur=.5):
    return f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{t:.2f}s" dur="{dur}s" fill="freeze"/>{inner}</g>'

def rulers(w, h, t_off):
    return (f'<g><animate attributeName="opacity" from="1" to="0" begin="{t_off}s" dur=".6s" fill="freeze"/>'
            f'<rect width="{w}" height="16" fill="#0b1420"/><rect width="{w}" height="16" fill="url(#rt)"/><path d="M0 16H{w}" stroke="#2d8cff88"/>'
            f'<rect y="16" width="16" height="{h}" fill="#0b1420"/><rect y="16" width="16" height="{h}" fill="url(#rl)"/><path d="M16 16V{h}" stroke="#2d8cff88"/></g>')

def save(name, svg):
    p = os.path.join(OUT, name)
    open(p, 'w').write(svg)
    print(f'{name}: {len(svg) / 1024:.0f} KB')

random.seed(7)

# =====================================================================
# HERO
# =====================================================================
def hero():
    W, H = 1200, 660
    END = 5.6
    port = base64.b64encode(open(os.environ.get('PORTRAIT', 'portrait.jpg'), 'rb').read()).decode()
    px, py, pw, ph = 600, 104, 420, 567
    defs = f'''<linearGradient id="giantg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{RED2}"/><stop offset=".45" stop-color="{RED}"/><stop offset=".8" stop-color="#5d0c12"/><stop offset="1" stop-color="#5d0c12" stop-opacity="0"/></linearGradient>
<linearGradient id="redl" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{RED}" stop-opacity="0"/><stop offset=".06" stop-color="{RED}"/><stop offset=".94" stop-color="{RED}"/><stop offset="1" stop-color="{RED}" stop-opacity="0"/></linearGradient>
<linearGradient id="mv" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#000"/><stop offset=".07" stop-color="#fff"/><stop offset=".6" stop-color="#fff"/><stop offset=".97" stop-color="#000"/></linearGradient>
<linearGradient id="mh" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#000"/><stop offset=".2" stop-color="#fff"/><stop offset=".8" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient>
<mask id="mhm" maskUnits="userSpaceOnUse" x="{px}" y="{py}" width="{pw}" height="{ph}"><rect x="{px}" y="{py}" width="{pw}" height="{ph}" fill="url(#mh)"/></mask>
<mask id="pm" maskUnits="userSpaceOnUse" x="{px}" y="{py}" width="{pw}" height="{ph}"><rect x="{px}" y="{py}" width="{pw}" height="{ph}" fill="url(#mv)" mask="url(#mhm)"/></mask>
<clipPath id="gclip"><rect x="0" y="0" width="0" height="{H}"><animate attributeName="width" from="0" to="{W}" begin=".5s" dur="2s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".5 0 .2 1"/></rect></clipPath>
<clipPath id="pclip"><rect x="{px}" y="{py + ph}" width="{pw}" height="0"><animate attributeName="y" from="{py + ph}" to="{py}" begin="2.7s" dur="1.1s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".2 .8 .2 1"/><animate attributeName="height" from="0" to="{ph}" begin="2.7s" dur="1.1s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".2 .8 .2 1"/></rect></clipPath>
<radialGradient id="glow" cx=".5" cy=".45" r=".5"><stop offset="0" stop-color="{RED}" stop-opacity=".22"/><stop offset="1" stop-color="{RED}" stop-opacity="0"/></radialGradient>
<linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0"><stop offset=".4" stop-color="#ff4d5a" stop-opacity="0"/><stop offset=".48" stop-color="#ff4d5a" stop-opacity=".35"/><stop offset=".5" stop-color="#fff" stop-opacity=".3"/><stop offset=".52" stop-color="#ff4d5a" stop-opacity=".35"/><stop offset=".6" stop-color="#ff4d5a" stop-opacity="0"/></linearGradient>'''
    s = [frame_open(W, H, defs)]
    s.append(f'<rect x="{px - 80}" y="60" width="{pw + 160}" height="560" fill="url(#glow)"/>')
    s.append(f'<rect x="44" y="70" width="2" height="{H - 70}" fill="url(#redl)" opacity=".7"/>')

    # nav
    lg, _, lw = text('anton', 'TAKI', 26, 76, 58)
    dot, _, _ = text('anton', '.', 26, 76 + lw, 58, fill=RED)
    nav = lg + dot
    lx = 470
    for i, l in enumerate(['Work', 'Toolkit', 'Journey', 'Contact']):
        p, _, w = text('body', l, 13, lx, 54, fill=MUTED); nav += p; lx += w + 28
    av, _, aw = text('body', 'Open to projects', 12, 940, 54, fill=MUTED)
    nav += f'<circle cx="930" cy="50" r="3.5" fill="#3DDC84"/><circle cx="930" cy="50" r="7" fill="#3DDC84" opacity=".15"/>{av}'
    bt, _, bw = text('bold', "LET'S TALK", 12, 1124, 55, fill='#fff', anchor='middle', ls=.04)
    nav += f'<rect x="{1124 - bw / 2 - 16:.0f}" y="34" width="{bw + 32:.0f}" height="32" rx="4" fill="{RED}"/>{bt}'
    s.append(appear(nav, .3, .6))

    # giant PORTFOLIO wipe
    gsz = 236
    gp, gx, gw = text('anton', 'PORTFOLIO', gsz, W / 2, 452, fill='url(#giantg)', anchor='middle')
    s.append(f'<g clip-path="url(#gclip)">{gp}</g>')

    # portrait
    s.append(placeholder(px - 60, py + 20, pw + 120, ph - 40, 1.3, 3.2))
    s.append(f'<g mask="url(#pm)"><g clip-path="url(#pclip)"><image x="{px}" y="{py}" width="{pw}" height="{ph}" preserveAspectRatio="xMidYMin slice" xlink:href="data:image/jpeg;base64,{port}" href="data:image/jpeg;base64,{port}">'
             f'<animateTransform attributeName="transform" type="scale" values="1;1.04;1" dur="16s" begin="3.8s" repeatCount="indefinite" additive="sum"/></image>'
             f'<rect x="{px - pw}" y="{py}" width="{pw}" height="{ph}" fill="url(#sweep)"><animate attributeName="x" from="{px - pw}" to="{px + pw}" begin="3.1s" dur="1.6s" fill="freeze"/></rect></g></g>')
    # sparks
    for i in range(12):
        sx = px + 40 + random.random() * (pw - 80); sy = py + ph * (.55 + random.random() * .4)
        d = 4 + random.random() * 4; b = 4 + random.random() * 4
        s.append(f'<circle cx="{sx:.0f}" cy="{sy:.0f}" r="1.6" fill="{RED2}" opacity="0"><animate attributeName="cy" from="{sy:.0f}" to="{sy - 340:.0f}" begin="{b:.1f}s" dur="{d:.1f}s" repeatCount="indefinite"/>'
                 f'<animate attributeName="cx" from="{sx:.0f}" to="{sx + 26:.0f}" begin="{b:.1f}s" dur="{d:.1f}s" repeatCount="indefinite"/>'
                 f'<animate attributeName="opacity" values="0;1;.8;0" keyTimes="0;.1;.7;1" begin="{b:.1f}s" dur="{d:.1f}s" repeatCount="indefinite"/></circle>')

    # left copy (typed)
    L = 76
    k1, _, k1w = typed('mono', 'STUDENT & CREATOR', 11, L, 150, .8, 1.4, fill=RED2, ls=.14)
    k2, _, k2w = typed('mono', 'BUILDER · AIUB · BANGLADESH', 11, L, 168, 1.2, 1.9, ls=.14)
    hello, _, hw = typed('script', "Hello, I'm", 44, L, 226, 1.6, 2.2, fill=RED2)
    n1, _, n1w = typed('anton', 'TAKI', 104, L, 330, 1.0, 1.8)
    n2, _, n2w = typed('anton', 'AHMED', 104, L, 432, 1.8, 2.8)
    n2d, _, _ = typed('anton', '.', 104, L + n2w, 432, 2.85, 2.9, fill=RED)
    role, _, rw = typed('anton', 'BUILDER & STORYTELLER', 26, L, 476, 3.0, 3.6, fill=RED2, ls=.01)
    b1, _, b1w = typed('body', 'CSE undergrad at AIUB. I build stores, games, apps', 15, L, 512, 3.4, 4.2, fill=MUTED)
    b2, _, b2w = typed('body', 'and local AI agents, then turn ideas into stories.', 15, L, 536, 3.7, 4.5, fill=MUTED)
    s += [k1, k2, hello, n1, n2, n2d, role, b1, b2]
    btxt, _, btw = text('bold', 'SEE MY WORK  →', 13, L + 20, 586, fill='#fff', ls=.04)
    s.append(appear(f'<rect x="{L}" y="562" width="{btw + 40:.0f}" height="38" rx="4" fill="{RED}"/>{btxt}', 4.5, .4))

    # stats (right)
    SX = 1060
    stats = [('AIUB', 'UNDERGRADUATE'), ('2026', 'PORTFOLIO LAUNCH'), ('04', 'PROJECTS SHIPPED')]
    for i, (v, l) in enumerate(stats):
        y = 250 + i * 100
        vp, _, vw = text('anton', v, 46, SX, y)
        dp, _, _ = text('anton', '.', 46, SX + vw, y, fill=RED)
        lp, _, _ = text('mono', l, 9.5, SX, y + 22, fill=MUTED, ls=.12)
        s.append(appear(vp + dp + lp, 2.3 + i * .45, .45))

    # bottom bar
    rl, _, _ = text('mono', 'SCROLL TO EXPLORE  ↓', 10, W - 76, H - 26, fill=MUTED, anchor='end', ls=.14)
    s.append(appear(rl, 4.8))

    # selection boxes
    s.append(selbox(gx - 6, 452 - gsz * .74, gw + 12, gsz * .76, 'Text · Giant', .5, 2.6))
    s.append(selbox(L - 4, 136, k2w + 8, 38, 'Text · Label', .8, 2.0))
    s.append(selbox(L - 4, 248, max(n1w, n2w) + 64, 192, 'H1 · Name', 1.0, 3.1))
    s.append(selbox(px - 60, py + 20, pw + 120, ph - 40, 'Image · Portrait', 1.3, 3.9))
    s.append(selbox(L - 4, 456, b1w + 8, 88, 'Text · Bio', 3.0, 4.7))
    s.append(selbox(SX - 6, 200, 128, 280, 'Stats', 2.3, 3.9))
    for (x, y, c, t) in [(px + 90, py + 160, COLORS[3], 1.5), (px + 300, py + 380, COLORS[3], 1.8), (L + 300, 440, COLORS[1], 3.0), (SX + 120, 480, COLORS[5], 3.9), (L + 180, 600, COLORS[4], 4.6)]:
        s.append(plus(x, y, c, t))

    s.append(rulers(W, H, END))

    # HUD
    hy = H - 46
    hud_build, _, _ = text('body', 'Building', 12, 0, 0)  # placeholder to warm cache
    a1, _, a1w = text('bold', '6', 12, 562, hy + 20)
    a2, _, _ = text('body', 'agents', 12, 562 + a1w + 4, hy + 20, fill=MUTED)
    b_l, _, _ = text('body', '34 layers', 12, 634, hy + 20, fill=MUTED)
    done1, _, d1w = text('body', 'Built by', 12, 562, hy + 20, fill=MUTED)
    done2, _, d2w = text('bold', '6 agents', 12, 562 + d1w + 5, hy + 20)
    done3, _, d3w = text('body', 'in', 12, 562 + d1w + d2w + 10, hy + 20, fill=MUTED)
    done4, _, _ = text('bold', f'{END - .6:.1f}s', 12, 562 + d1w + d2w + d3w + 15, hy + 20)
    avs = ''.join(f'<circle cx="{500 + i * 11}" cy="{hy + 16}" r="7" fill="{c}" stroke="#15161c" stroke-width="2"/>' for i, c in enumerate(COLORS[:5][::-1]))
    s.append(appear(
        f'<rect x="478" y="{hy}" width="262" height="32" rx="16" fill="#15161cee" stroke="#2a2b33"/>{avs}'
        f'<g><set attributeName="opacity" to="0" begin="{END}s" fill="freeze"/>{a1}{a2}{b_l}'
        f'<rect x="690" y="{hy + 15}" width="0" height="3" rx="1.5" fill="none"/></g>'
        f'<g opacity="0"><set attributeName="opacity" to="1" begin="{END}s" fill="freeze"/>{done1}{done2}{done3}{done4}</g>', .2))
    s.append(f'<rect x="0" y="{H - 2}" width="0" height="2" fill="{FIG}"><animate attributeName="width" from="0" to="{W}" begin=".2s" dur="{END - .2}s" fill="freeze"/><animate attributeName="opacity" from="1" to="0" begin="{END}s" dur=".6s" fill="freeze"/></rect>')

    # cursors
    rnd = lambda cx, cy, r: [(cx + random.uniform(-r, r), cy + random.uniform(-r * .6, r * .6)) for _ in range(4)]
    s.append(cursor(COLORS[0], [(0, 600, 330), (.5, gx, 300), (2.5, gx + gw, 330), (2.9, 930, 140)], END, rnd(0, 0, 40), END))
    s.append(cursor(COLORS[1], [(0, 620, 340), (.8, L, 140), (1.4, L + k1w, 150), (1.9, L + k2w, 168), (2.2, L + hw, 222), (3.0, L, 470), (3.6, L + rw, 476), (4.0, 420, 330)], END, rnd(0, 0, 50), END))
    s.append(cursor(COLORS[2], [(0, 580, 320), (1.0, L, 280), (1.8, L + n1w, 300), (2.8, L + n2w, 400), (3.4, 480, 250)], END, rnd(0, 0, 50), END))
    s.append(cursor(COLORS[3], [(0, 610, 360), (1.3, px - 60, py + 20), (2.4, px + pw + 60, py + ph - 20), (3.4, px + pw / 2, py + ph / 2), (4.4, 760, 190)], END, rnd(0, 0, 60), END))
    s.append(cursor(COLORS[4], [(0, 590, 350), (3.0, L + 200, 520), (3.4, L, 505), (4.5, L + b2w, 536), (4.9, L + 120, 600), (5.3, 300, 610)], END, rnd(0, 0, 40), END))
    s.append(cursor(COLORS[5], [(0, 630, 320), (.3, 520, 50), (1.2, 900, 50), (2.3, SX, 210), (3.9, SX + 120, 470), (4.6, 1100, 560)], END, rnd(0, 0, 40), END))
    s.append(frame_close())
    save('hero.svg', ''.join(s))

# =====================================================================
# SECTION HEADER
# =====================================================================
def header(fname, num, eyebrow, white, red, color, right=None):
    W, H = 1200, 168
    s = [frame_open(W, H)]
    L = 60
    nb, _, nw = text('mono', num, 11, L, 50, fill=RED2, ls=.14)
    eb, _, ew = typed('mono', ' / ' + eyebrow.upper(), 11, L + nw, 50, .3, .9, fill=MUTED, ls=.14)
    s.append(appear(nb, .2, .2)); s.append(eb)
    t1, _, w1 = typed('anton', white + ' ', 72, L, 132, .7, 1.5)
    t2, _, w2 = typed('anton', red, 72, L + w1, 132, 1.5, 2.1, fill=RED2)
    s += [t1, t2]
    s.append(selbox(L - 6, 70, w1 + w2 + 12, 72, 'H2 · Heading', .7, 2.4))
    s.append(f'<path d="M{L} 158H{W - L}" stroke="{LINE}"/>')
    if right:
        rp, _, _ = text('mono', right, 10, W - L, 132, fill=MUTED, anchor='end', ls=.14)
        s.append(appear(rp, 2.1))
    s.append(cursor(color, [(0, W - 200, 150), (.7, L, 80), (1.5, L + w1, 132), (2.1, L + w1 + w2, 132), (2.6, L + w1 + w2 + 60, 110)], 2.6,
                    [(0, 0), (40, -20), (80, 10), (30, 20)], 2.6))
    s.append(frame_close())
    save(fname, ''.join(s))

# =====================================================================
# PROJECT CARD
# =====================================================================
def card(fname, n, tag, title, desc, cta, color, delay, accent=RED):
    W, H = 590, 420
    fw, fh = 590, 320
    defs = f'''<radialGradient id="cg" cx=".8" cy="0" r=".9"><stop offset="0" stop-color="{accent}" stop-opacity=".32"/><stop offset=".6" stop-color="{accent}" stop-opacity="0"/></radialGradient>
<linearGradient id="cb" x1="0" y1="0" x2=".6" y2="1"><stop offset="0" stop-color="#1b1b22"/><stop offset="1" stop-color="#0b0b0e"/></linearGradient>'''
    s = [frame_open(W, H, defs)]
    s.append(f'<rect width="{fw}" height="{fh}" fill="url(#cb)"/><rect width="{fw}" height="{fh}" fill="url(#cg)"/><rect width="{fw}" height="{fh}" fill="url(#scan)"/>')
    tg, _, tw = text('mono', tag.upper(), 9, 22, 30, fill=INK, ls=.12)
    s.append(f'<rect x="14" y="16" width="{tw + 16:.0f}" height="20" rx="2" fill="#000a"/>{tg}')
    # title, scaled to fit
    size = 58
    while width('anton', title.upper(), size) > fw - 80: size -= 2
    tp, _, _ = text('anton', title.upper(), size, fw / 2, fh / 2 + size * .36, anchor='middle')
    s.append(tp)
    s.append(f'<circle cx="{fw - 40}" cy="{fh - 40}" r="20" fill="none" stroke="#ffffff44"/><path d="M{fw - 45} {fh - 48}l13 8-13 8z" fill="#fff" opacity=".85"/>')
    s.append(f'<path d="M0 {fh}H{W}" stroke="{LINE}"/>')
    # caption
    np_, _, nw = text('anton', n, 34, 20, fh + 50, fill=RED)
    hp, _, _ = text('bold', title.upper(), 15, 20 + nw + 16, fh + 34, ls=.02)
    dp, _, _ = text('body', desc, 12.5, 20 + nw + 16, fh + 56, fill=MUTED)
    cp, _, _ = text('mono', cta, 10, W - 20, fh + 34, fill=RED2, anchor='end', ls=.14)
    s += [np_, hp, dp, cp]
    # looping agent: hover in, select frame, wander out
    T = 9.0
    a, b = delay, delay
    sel_inner = selbox(10, 10, fw - 20, fh - 20, 'Frame · ' + title, 0, 0)  # build static then loop via animate
    # static body of a selbox without timing:
    hs = ''.join(f'<rect x="{x - 3.5}" y="{y - 3.5}" width="7" height="7" fill="#fff" stroke="{FIG}"/>' for x, y in [(10, 10), (fw - 10, 10), (10, fh - 10), (fw - 10, fh - 10)])
    nm, _, _ = text('mono', 'Frame · ' + title, 10, 14, 28 + 2, fill=FIG)
    dims = f'{fw - 20} × {fh - 20}'; dw = width('mono', dims, 10) + 12
    dmp, _, _ = text('mono', dims, 10, fw / 2, fh - 25, fill='#fff', anchor='middle')
    box = (f'<rect x="10" y="10" width="{fw - 20}" height="{fh - 20}" fill="none" stroke="{FIG}"/>{hs}'
           f'<rect x="{fw / 2 - dw / 2:.0f}" y="{fh - 37}" width="{dw:.0f}" height="16" rx="2" fill="{FIG}"/>{dmp}')
    s.append(f'<g opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;.18;.22;.62;.68;1" dur="{T}s" begin="{delay}s" repeatCount="indefinite"/>{box}</g>')
    path = [(W + 30, fh + 60), (W + 30, fh + 60), (30, 30), (fw - 30, fh - 30), (fw * .62, fh * .55), (W + 30, fh * .3), (W + 30, fh + 60)]
    kt = [0, .12, .22, .42, .6, .8, 1]
    vals = ';'.join(f'{x},{y}' for x, y in path)
    s.append(f'<g transform="translate({W + 30},{fh + 60})"><animateTransform attributeName="transform" type="translate" values="{vals}" keyTimes="{";".join(map(str, kt))}" '
             f'calcMode="spline" keySplines="{";".join([".45 .05 .25 1"] * 6)}" dur="{T}s" begin="{delay}s" repeatCount="indefinite"/>'
             f'<path d="{ARROW}" fill="{color}" stroke="#000" stroke-opacity=".55" stroke-width="1.1" stroke-linejoin="round"/></g>')
    s.append(frame_close())
    save(fname, ''.join(s))

# =====================================================================
# TOOLKIT
# =====================================================================
def toolkit():
    items = [('Python', 'Language'), ('Java', 'Language'), ('C#', 'Language'), ('JavaScript', 'Language'), ('HTML · CSS', 'Web'),
             ('Git', 'Workflow'), ('Android ADB', 'Automation'), ('Ollama', 'Local AI'), ('LLM routing', 'AI agents'), ('Desktop automation', 'Automation')]
    W, H = 1200, 236
    s = [frame_open(W, H)]
    cols, gx, gy, cw, ch = 5, 60, 30, 204, 80
    gap = (W - 2 * gx - cols * cw) / (cols - 1)
    keys = [(0, W - 80, H - 20)]
    for i, (name, cat) in enumerate(items):
        r, c = divmod(i, cols)
        x, y = gx + c * (cw + gap), gy + r * (ch + 22)
        t = .4 + i * .32
        cp, _, _ = text('mono', cat.upper(), 9.5, x + 20, y + 30, fill=MUTED, ls=.12)
        np_, _, _ = text('bold', name, 17, x + 20, y + 58)
        body = (f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="4" fill="{PANEL}" stroke="{LINE}"/>'
                f'<rect x="{x}" y="{y}" width="3" height="{ch}" fill="{RED}"/>'
                f'<circle cx="{x + cw - 20}" cy="{y + 24}" r="3.5" fill="{RED2}"/>{cp}{np_}')
        s.append(placeholder(x, y, cw, ch, t, t + .45))
        s.append(appear(body, t + .4, .35))
        keys += [(t, x + 4, y + 4), (t + .3, x + cw - 6, y + ch - 6)]
    end = keys[-1][0] + .6
    keys.append((end, W - 120, H - 30))
    s.append(cursor(COLORS[4], keys, end, [(0, 0), (-60, -30), (-120, 5), (-40, 20)], end))
    s.append(frame_close())
    save('toolkit.svg', ''.join(s))

# =====================================================================
# JOURNEY
# =====================================================================
def journey():
    W, H = 1200, 420
    rows = [('SSC', 'Milestone College', 'Secondary School Certificate', 'DONE'),
            ('HSC', 'Milestone College', 'Higher Secondary Certificate', 'DONE'),
            ('NOW', 'Undergraduate · AIUB', 'Computer Science & Engineering, American International University-Bangladesh', 'IN PROGRESS'),
            ('BUILDING', 'TITAN · Nyxeris · Last Charge · CheckFirst', 'An AI operator, a store, an Android game and a safety app', 'ONGOING'),
            ('NEXT', 'The next chapter', 'To be announced', 'SOON')]
    s = [frame_open(W, H)]
    L, top, rh = 90, 40, 70
    s.append(f'<rect x="{L - 30}" y="{top}" width="2" height="0" fill="{RED}"><animate attributeName="height" from="0" to="{rh * 5}" begin=".2s" dur="2.4s" fill="freeze"/></rect>')
    for i, (yr, b, sm, st) in enumerate(rows):
        y = top + i * rh
        t = .4 + i * .45
        yp, _, _ = text('mono', yr, 10.5, L, y + 32, fill=MUTED, ls=.1)
        bp, _, _ = text('bold', b, 15, L + 120, y + 30)
        sp, _, _ = text('body', sm, 12, L + 120, y + 50, fill=MUTED)
        stp, _, _ = text('mono', st, 10, 820, y + 32, fill=RED2, anchor='end', ls=.14)
        now = yr == 'NOW'
        dot = (f'<circle cx="{L - 29}" cy="{y + 28}" r="12" fill="{RED}" opacity=".25"><animate attributeName="r" values="8;14;8" dur="2s" repeatCount="indefinite"/></circle>'
               f'<circle cx="{L - 29}" cy="{y + 28}" r="7" fill="{RED}"/>') if now else f'<circle cx="{L - 29}" cy="{y + 28}" r="7" fill="{BG}" stroke="{RED}" stroke-width="2"/>'
        s.append(appear(dot + yp + bp + sp + stp + f'<path d="M{L} {y + rh - 4}H820" stroke="{LINE}"/>', t, .4))
    # wins card
    cx, cy, cw, chh = 870, top, 270, 340
    w1, _, _ = text('anton', 'LITTLE WINS.', 38, cx + 26, cy + 70)
    w2, _, _ = text('anton', 'BIG MEANING.', 38, cx + 26, cy + 112, fill=RED2)
    w3, _, _ = text('body', 'Every milestone gets logged', 13, cx + 26, cy + 150, fill=MUTED)
    w4, _, _ = text('body', 'here as it happens.', 13, cx + 26, cy + 170, fill=MUTED)
    sig, _, _ = text('script', 'Taki', 34, cx + 26, cy + chh - 30, fill=RED2)
    s.append(appear(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{chh}" rx="4" fill="none" stroke="{LINE}"/>{w1}{w2}{w3}{w4}{sig}', 2.6, .6))
    s.append(selbox(cx, cy, cw, chh, 'Card', 2.6, 3.6))
    keys = [(0, 600, H - 10)] + [(.4 + i * .45, L + 120, top + i * rh + 28) for i in range(5)] + [(2.6, cx + 8, cy + 8), (3.2, cx + cw - 8, cy + chh - 8), (3.8, cx + 140, cy + 230)]
    s.append(cursor(COLORS[6], keys, 3.8, [(0, 0), (-50, -40), (-90, 10), (-20, 30)], 3.8))
    s.append(frame_close())
    save('journey.svg', ''.join(s))

# =====================================================================
# CONTACT (finale: the swarm circles the reel card)
# =====================================================================
def contact():
    W, H = 1200, 400
    defs = f'''<radialGradient id="feel" cx=".3" cy=".2" r=".9"><stop offset="0" stop-color="#3a1018"/><stop offset="1" stop-color="#0b0b0f"/></radialGradient>'''
    s = [frame_open(W, H, defs)]
    L = 60
    nb, _, nw = text('mono', '05', 11, L, 92, fill=RED2, ls=.14)
    eb, _, _ = text('mono', ' / YOUR NEXT STORY', 11, L + nw, 92, fill=MUTED, ls=.14)
    t1, _, _ = typed('anton', "LET'S WORK", 92, L, 196, .4, 1.2)
    t2, _, _ = typed('anton', 'TOGETHER.', 92, L, 292, 1.2, 1.9, fill=RED2)
    p1, _, _ = text('body', 'Got a store, a game, an app or an agent in mind?', 15, L, 336, fill=MUTED)
    p2, _, _ = text('body', 'Links below. Let\'s build it, frame by frame.', 15, L, 358, fill=MUTED)
    s += [appear(nb + eb, .2), t1, t2, appear(p1 + p2, 1.9)]
    # reel card
    fx, fy, fw, fh = 720, 70, 420, 260
    f1, _, _ = text('anton', 'MAKE IT', 56, fx + 34, fy + 120)
    f2, _, _ = text('anton', 'FEEL REAL.', 56, fx + 34, fy + 180, fill=RED2)
    s.append(appear(f'<rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" rx="4" fill="url(#feel)"/><rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" fill="url(#scan)"/>{f1}{f2}'
                    f'<circle cx="{fx + fw - 38}" cy="{fy + fh - 38}" r="22" fill="{RED}"/><path d="M{fx + fw - 43} {fy + fh - 46}l13 8-13 8z" fill="#fff"/>', .8, .6))
    # ring of agents
    cx, cy, rx, ry = fx + fw / 2, fy + fh / 2, fw * .62, fh * .7
    ring = f'M{cx + rx} {cy}A{rx} {ry} 0 1 1 {cx - rx} {cy}A{rx} {ry} 0 1 1 {cx + rx} {cy}'
    for i in range(8):
        off = -i / 8 * 9
        s.append(f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{1.6 + i * .1:.1f}s" dur=".4s" fill="freeze"/>'
                 f'<g><animateMotion path="{ring}" dur="9s" begin="{off:.2f}s" repeatCount="indefinite"/>'
                 f'<path d="{ARROW}" fill="{COLORS[i]}" stroke="#000" stroke-opacity=".55" stroke-width="1.1" stroke-linejoin="round"/></g></g>')
    s.append(frame_close())
    save('contact.svg', ''.join(s))

# =====================================================================
# BUTTONS + FOOTER
# =====================================================================
def button(fname, label, primary):
    w = int(width('bold', label, 13, .06) + 64); h = 46
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">']
    s.append(f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="4" fill="{RED if primary else BG}" stroke="{RED if primary else "#3a3a44"}"/>')
    p, _, _ = text('bold', label, 13, w / 2, 28, fill='#fff', anchor='middle', ls=.06)
    s.append(p + '</svg>')
    save(fname, ''.join(s))

def footer():
    W, H = 1200, 70
    s = [frame_open(W, H)]
    a, _, _ = text('mono', '© 2026 MUHAMMAD TAKI AHMED', 10.5, 60, 41, fill=MUTED, ls=.12)
    b, _, _ = text('mono', 'MADE FRAME BY FRAME', 10.5, W - 60, 41, fill=MUTED, anchor='end', ls=.12)
    lg, _, lw = text('anton', 'TAKI', 22, W / 2 - 20, 44)
    d, _, _ = text('anton', '.', 22, W / 2 - 20 + lw, 44, fill=RED)
    s += [a, b, lg, d, frame_close()]
    save('footer.svg', ''.join(s))

hero()
header('h-work.svg', '01', 'Selected work', 'WORK THAT', 'SPEAKS.', COLORS[0], 'HOVER A CARD · CLICK TO OPEN')
header('h-toolkit.svg', '02', 'Toolkit', 'TOOLS OF', 'THE TRADE.', COLORS[1])
header('h-journey.svg', '03', 'The journey', 'KEEP MOVING.', 'KEEP MAKING.', COLORS[2])
card('card-titan.svg', '01', 'AI agent · Python', 'TITAN', 'Local, privacy-first AI operator for PC + Android.', 'REPO →', COLORS[3], 0, accent='#E3262E')
card('card-nyxeris.svg', '02', 'E-commerce · Website', 'Nyxeris Store', 'Online store for tech, home, auto and office essentials.', 'VISIT →', COLORS[0], 2.2, accent='#FF4D5A')
card('card-lastcharge.svg', '03', 'Game · Android', 'Last Charge', 'Endless runner for Android. Live on Google Play.', 'PLAY →', COLORS[2], 4.4, accent='#E3262E')
card('card-checkfirst.svg', '04', 'App', 'CheckFirst', 'Check a number, wallet or site before you pay.', 'OPEN →', COLORS[5], 6.6, accent='#FF4D5A')
toolkit()
journey()
contact()
button('btn-email.svg', 'EMAIL ME  →', True)
button('btn-takiapps.svg', 'TAKIAPPS.COM  →', False)
button('btn-titan.svg', 'TITAN ON GITHUB  →', False)
footer()
