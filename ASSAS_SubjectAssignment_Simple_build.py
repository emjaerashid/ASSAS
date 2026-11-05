import sys, html
BG, CARD, BORDER = "#0d1017", "#161a23", "#2a303d"
TEXT, MUTED, LINE = "#e6e9ef", "#8a93a6", "#9aa4b8"
BLUE, PURPLE, AMBER, TEAL = "#3b82f6", "#a855f7", "#f59e0b", "#14b8a6"
GREEN, ROSE, SLATE = "#22c55e", "#f43f5e", "#64748b"
FONT = "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Helvetica, Arial, sans-serif"
WIDTH, HEIGHT = 1060, 1440
LANES = [(40, 700, BLUE, "1 · Batch run & pre-check", "run_assignment_for_all / _for_student"),
         (720, 1480, PURPLE, "2 · Per-subject rule checks", "RuleEngine.run → _evaluate_subject"),
         (1500, 2260, AMBER, "3 · Exceptions & auto-replacement", "_flag_exception · _handle_*")]
o = []
def esc(s): return html.escape(s)
def add(s): o.append(s)

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" font-family="{FONT}">')
add(f'<defs><pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#1b202b"/></pattern>'
    f'<filter id="sh" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="6" stdDeviation="8" flood-color="#000" flood-opacity="0.45"/></filter>'
    f'<marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path d="M0,1 L10,5 L0,9 z" fill="{LINE}"/></marker></defs>')
add(f'<rect width="100%" height="100%" fill="{BG}"/><rect width="100%" height="100%" fill="url(#dots)"/>')
add(f'<text x="40" y="62" fill="{TEXT}" font-size="28" font-weight="700" letter-spacing="0.3">ASSAS — Subject Assignment</text>')
add(f'<text x="40" y="92" fill="{MUTED}" font-size="15">Simplified activity diagram · how the rule engine assigns subjects to a student</text>')

edges, nodes = [], []
def path(pts, arrow=True, dashed=False, color=LINE):
    d = "M" + " L".join(f"{x},{y}" for x, y in pts)
    m = ' marker-end="url(#arr)"' if arrow else ""
    da = ' stroke-dasharray="7 6"' if dashed else ""
    edges.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.8" stroke-linejoin="round"{m}{da}/>')
def tag(x, y, t, col, anchor="start"):
    edges.append(f'<text x="{x}" y="{y}" fill="{col}" font-size="12" font-weight="700" text-anchor="{anchor}">{esc(t)}</text>')
def pill(x, y, t, col=None):
    w = len(t) * 6.4 + 18
    c = col or "#c7cede"
    edges.append(f'<rect x="{x-w/2}" y="{y-10}" width="{w}" height="20" rx="10" fill="#1d2230" stroke="{col or BORDER}" stroke-opacity="{0.6 if col else 1}"/>'
                 f'<text x="{x}" y="{y+4}" fill="{c}" font-size="11.5" text-anchor="middle" font-family="ui-monospace, Menlo, monospace">{esc(t)}</text>')

def action(cx, cy, w, h, title, sub="", col=PURPLE):
    x, y = cx - w/2, cy - h/2
    s = [f'<g filter="url(#sh)"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{CARD}" stroke="{col}" stroke-opacity="0.55"/></g>',
         f'<rect x="{x}" y="{y+12}" width="3.5" height="{h-24}" rx="1.75" fill="{col}"/>']
    lines = sub.split("\n") if sub else []
    ty = cy - (len(lines) * 16) / 2 + 5
    s.append(f'<text x="{cx}" y="{ty}" fill="{TEXT}" font-size="14" font-weight="650" text-anchor="middle">{esc(title)}</text>')
    for i, l in enumerate(lines):
        s.append(f'<text x="{cx}" y="{ty + 19 + i*16}" fill="{MUTED}" font-size="12" text-anchor="middle">{esc(l)}</text>')
    nodes.append("".join(s))
    return dict(l=x, r=x+w, t=y, b=y+h, cx=cx, cy=cy)

def decision(cx, cy, lines, w=270, h=96, rule=None, col=PURPLE):
    pts = f"{cx},{cy-h/2} {cx+w/2},{cy} {cx},{cy+h/2} {cx-w/2},{cy}"
    s = [f'<g filter="url(#sh)"><polygon points="{pts}" fill="{CARD}" stroke="{col}" stroke-opacity="0.75" stroke-width="1.4"/></g>']
    n = len(lines) + (1 if rule else 0)
    ty = cy - (n - 1) * 8 + 4.5
    if rule:
        s.append(f'<text x="{cx}" y="{ty}" fill="{TEAL}" font-size="11" font-weight="800" letter-spacing="0.8" text-anchor="middle">{esc(rule)}</text>'); ty += 16
    for i, l in enumerate(lines):
        s.append(f'<text x="{cx}" y="{ty + i*16}" fill="{TEXT}" font-size="12.5" font-weight="600" text-anchor="middle">{esc(l)}</text>')
    nodes.append("".join(s))
    return dict(l=cx-w/2, r=cx+w/2, t=cy-h/2, b=cy+h/2, cx=cx, cy=cy)

def merge(cx, cy, col=PURPLE):
    nodes.append(f'<polygon points="{cx},{cy-16} {cx+20},{cy} {cx},{cy+16} {cx-20},{cy}" fill="{CARD}" stroke="{col}" stroke-width="1.4"/>')
    return dict(l=cx-20, r=cx+20, t=cy-16, b=cy+16, cx=cx, cy=cy)

def conn(cx, cy, letter, col):
    nodes.append(f'<circle cx="{cx}" cy="{cy}" r="13" fill="{col}" fill-opacity="0.2" stroke="{col}" stroke-width="1.5"/>'
                 f'<text x="{cx}" y="{cy+4.5}" fill="{TEXT}" font-size="13" font-weight="800" text-anchor="middle">{letter}</text>')

def chip(cx, cy, t, col):
    w = len(t) * 7 + 22
    nodes.append(f'<rect x="{cx-w/2}" y="{cy-13}" width="{w}" height="26" rx="13" fill="{col}" fill-opacity="0.16" stroke="{col}" stroke-opacity="0.7"/>'
                 f'<text x="{cx}" y="{cy+4.5}" fill="{TEXT}" font-size="12.5" font-weight="650" text-anchor="middle">{esc(t)}</text>')
    return w

def start(cx, cy):
    nodes.append(f'<circle cx="{cx}" cy="{cy}" r="14" fill="{TEXT}"/>')
def end(cx, cy):
    nodes.append(f'<circle cx="{cx}" cy="{cy}" r="17" fill="none" stroke="{TEXT}" stroke-width="2"/><circle cx="{cx}" cy="{cy}" r="10" fill="{TEXT}"/>')

YES, NO = GREEN, ROSE


S = 440
add(f'<rect x="40" y="120" width="{WIDTH-80}" height="{HEIGHT-160}" rx="14" fill="{PURPLE}" fill-opacity="0.03" stroke="{PURPLE}" stroke-opacity="0.25"/>')
start(S, 170)
a1 = action(S, 245, 300, 56, "Select student & semester")
path([(S, 184), (S, a1["t"])])
a2 = action(S, 345, 300, 64, "Get subject list", "repeat subjects first · scheduled only")
path([(S, a1["b"]), (S, a2["t"])])
a3 = action(S, 450, 300, 64, "Remove time clashes", "keep the subject with more credits")
path([(S, a2["b"]), (S, a3["t"])])
m = merge(S, 535)
path([(S, a3["b"]), (S, m["t"])])
nodes.append(f'<text x="{S+32}" y="539" fill="{MUTED}" font-size="12">for each subject</text>')

d1 = decision(S, 640, ["Already passed", "or assigned?"], w=250, h=88)
d2 = decision(S, 755, ["Prerequisites", "passed?"], w=250, h=88)
d3 = decision(S, 870, ["Within credit &", "subject limit?"], w=250, h=88)
d4 = decision(S, 985, ["Seat", "available?"], w=250, h=88)
path([(S, m["b"]), (S, d1["t"])])
path([(S, d1["b"]), (S, d2["t"])]); tag(S + 10, d1["b"] + 17, "no", NO)
path([(S, d2["b"]), (S, d3["t"])]); tag(S + 10, d2["b"] + 17, "yes", YES)
path([(S, d3["b"]), (S, d4["t"])]); tag(S + 10, d3["b"] + 17, "yes", YES)
a4 = action(S, 1100, 300, 56, "Assign subject", "", GREEN)
path([(S, d4["b"]), (S, a4["t"])]); tag(S + 10, d4["b"] + 17, "yes", YES)
d5 = decision(S, 1205, ["More subjects?"], w=230, h=80)
path([(S, a4["b"]), (S, d5["t"])])

# skip branch
path([(d1["r"], 640), (900, 640), (900, 1205), (d5["r"], 1205)])
tag(d1["r"] + 8, 632, "yes", YES); chip(760, 640, "Skip", SLATE)
# flag branch
BUS = 615
for d in (d2, d3, d4):
    path([(d["r"], d["cy"]), (BUS, d["cy"])], arrow=False); tag(d["r"] + 8, d["cy"] - 8, "no", NO)
path([(BUS, 755), (BUS, 985)], arrow=False)
fl = action(760, 870, 220, 72, "Log exception", "for admin review", ROSE)
path([(BUS, 870), (fl["l"], 870)])
path([(760, fl["b"]), (760, 1205)], arrow=False)

# loop back
path([(d5["l"], 1205), (110, 1205), (110, 535), (m["l"], 535)]); tag(d5["l"] - 8, 1197, "yes", YES, "end")
a5 = action(S, 1310, 300, 56, "Show assignment summary")
path([(S, d5["b"]), (S, a5["t"])]); tag(S + 10, d5["b"] + 17, "no", NO)
end(S, 1385); path([(S, a5["b"]), (S, 1385 - 18)])

o.extend(edges); o.extend(nodes); o.append("</svg>")
svg = "\n".join(o)
open(sys.argv[1], "w").write(svg)
open(sys.argv[2], "w").write(f'<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;background:{BG}}}</style></head><body>{svg}</body></html>')
