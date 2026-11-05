import sys, html
BG, CARD, BORDER = "#0d1017", "#161a23", "#2a303d"
TEXT, MUTED, LINE = "#e6e9ef", "#8a93a6", "#9aa4b8"
BLUE, PURPLE, AMBER, TEAL = "#3b82f6", "#a855f7", "#f59e0b", "#14b8a6"
GREEN, ROSE, SLATE = "#22c55e", "#f43f5e", "#64748b"
FONT = "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Helvetica, Arial, sans-serif"
WIDTH, HEIGHT = 1620, 2470
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
add(f'<text x="40" y="62" fill="{TEXT}" font-size="30" font-weight="700" letter-spacing="0.3">ASSAS — Subject Assignment Activity Diagram</text>')
add(f'<text x="40" y="92" fill="{MUTED}" font-size="15">Source: backend/core/rule_engine.py  ·  RuleEngine.run() · subject assignment for one student</text>')

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

def card(x, y, w, hh, title):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{hh}" rx="12" fill="{CARD}" stroke="{BORDER}"/>'
        f'<text x="{x+20}" y="{y+30}" fill="{TEXT}" font-size="14.5" font-weight="700" letter-spacing="0.6">{esc(title)}</text>'
        f'<line x1="{x}" y1="{y+44}" x2="{x+w}" y2="{y+44}" stroke="{BORDER}"/>')

add(f'<rect x="40" y="120" width="{WIDTH-80}" height="{HEIGHT-160}" rx="14" fill="{PURPLE}" fill-opacity="0.03" stroke="{PURPLE}" stroke-opacity="0.25"/>')
S = 600
start(S, 175)
a1 = action(S, 250, 340, 70, "Start assignment for student", "student · semester code · optional max subjects")
path([(S, 189), (S, a1["t"])])
a2 = action(S, 360, 380, 74, "Load academic history", "passed subjects · failed subjects (not since passed)\nsubjects already assigned this semester")
path([(S, a1["b"]), (S, a2["t"])])
d0 = decision(S, 480, ["Student on", "probation?"], w=230, h=88, rule="R5")
path([(S, a2["b"]), (S, d0["t"])])
cl = action(330, 590, 260, 64, "Cap = probation cap", "programme.probation_credit_cap")
cr = action(870, 590, 260, 64, "Cap = normal cap", "programme.max_credits_per_sem")
path([(d0["l"], 480), (330, 480), (330, cl["t"])]); tag(d0["l"] - 8, 472, "yes", YES, "end")
path([(d0["r"], 480), (870, 480), (870, cr["t"])]); tag(d0["r"] + 8, 472, "no", NO)
mg = merge(S, 690)
path([(330, cl["b"]), (330, 690), (mg["l"], 690)]); path([(870, cr["b"]), (870, 690), (mg["r"], 690)])
a4 = action(S, 800, 400, 74, "Build candidate subject list", "failed subjects first (R4 repeats), then current-semester\nsubjects · only those with a timetable slot this semester")
path([(S, mg["b"]), (S, a4["t"])])
a5 = action(S, 915, 400, 66, "Resolve time-slot clashes", "overlapping pair → keep higher credit hours · loser set aside")
path([(S, a4["b"]), (S, a5["t"])])
m2 = merge(S, 1010); conn(S + 44, 1010, "A", PURPLE)
nodes.append(f'<text x="{S+64}" y="1014" fill="{MUTED}" font-size="12">next subject</text>')
path([(S, a5["b"]), (S, m2["t"])])
d3 = decision(S, 1110, ["Subjects left", "to evaluate?"])
path([(S, m2["b"]), (S, d3["t"])])

chain = [
  (1225, ["Already passed?"], "R1", "yes", "skip"),
  (1335, ["Already assigned", "this semester?"], "R6", "yes", "skip"),
  (1445, ["All prerequisites", "passed?"], "R2", "no", "prerequisite_unmet"),
  (1555, ["Credits would", "exceed cap?"], "R3 · R5", "yes", "credit_limit | probation_cap"),
  (1665, ["Subject count", "limit reached?"], "LIMIT", "yes", "subject_limit_exceeded"),
  (1775, ["Class full?", "(venue seats)"], "R7", "yes", "class_full"),
]
BUS = 1030
prev = d3; prev_label = ("yes", YES)
for cy, lines, rule, out, outcome in chain:
    d = decision(S, cy, lines, rule=rule)
    path([(S, prev["b"]), (S, d["t"])]); tag(S + 10, prev["b"] + 17, *prev_label)
    cont = "no" if out == "yes" else "yes"
    prev_label = (cont, YES if cont == "yes" else NO)
    tag(d["r"] + 8, cy - 8, out, YES if out == "yes" else NO)
    if outcome == "skip":
        path([(d["r"], cy), (835, cy)]); chip(870, cy, "skip", SLATE)
        path([(900, cy), (922, cy)]); conn(936, cy, "A", PURPLE)
    elif outcome == "class_full":
        path([(d["r"], cy), (1180, cy)]); pill(895, cy, outcome, AMBER)
    else:
        path([(d["r"], cy), (BUS, cy)], arrow=False); pill(895, cy, outcome, ROSE)
    prev = d
fl = action(1340, 1555, 320, 82, "Flag exception", "ExceptionLog · status = pending\nreason recorded · added to report", ROSE)
path([(BUS, 1445), (BUS, 1665)], arrow=False); path([(BUS, 1555), (fl["l"], 1555)])
path([(1340, fl["b"]), (1340, 1640 - 13)]); conn(1340, 1640, "A", PURPLE)
ar = action(1340, 1800, 320, 106, "Try auto-replacement", "log class_full / conflict (pending)\nif safe and a clash-free subject with seats\nexists → enrol it, exception approved\nelse leave pending for admin", AMBER)
rw = chip(1340, 1900, "return → A (full) · C (clash)", SLATE)
path([(1340, ar["b"]), (1340, 1900 - 13)])

b3 = action(S, 1895, 400, 82, "Assign subject", "create Enrolment (status = assigned)\nis_repeat if failed before (R4) · add credit hours", GREEN)
path([(S, prev["b"]), (S, b3["t"])]); tag(S + 10, prev["b"] + 17, *prev_label)
path([(S, b3["b"]), (S, 1975 - 13)]); conn(S, 1975, "A", PURPLE)

m3 = merge(S, 2055); conn(S + 44, 2055, "C", PURPLE)
nodes.append(f'<text x="{S+64}" y="2059" fill="{MUTED}" font-size="12">next clash loser</text>')
path([(d3["l"], 1110), (200, 1110), (200, 2055), (m3["l"], 2055)]); tag(d3["l"] - 8, 1102, "no", NO, "end")
d10 = decision(S, 2160, ["Clash losers", "left?"], rule="R6")
path([(S, m3["b"]), (S, d10["t"])])
path([(d10["r"], 2160), (1060, 2160), (1060, 1775)]); tag(d10["r"] + 8, 2152, "yes", YES); pill(895, 2160, "conflict", AMBER)
b4 = action(S, 2285, 400, 66, "Return assignment summary", "assigned subject codes · total credits · exceptions")
path([(S, d10["b"]), (S, b4["t"])]); tag(S + 10, d10["b"] + 17, "no", NO)
end(S, 2385); path([(S, b4["b"]), (S, 2385 - 18)])

card(1100, 160, 460, 600, "RULES APPLIED")
rules = [("R1", "Already passed", "skip if passed before"),
         ("R2", "Prerequisites", "flag if any not passed"),
         ("R3", "Credit limit", "flag if over the cap"),
         ("R4", "Repeat subjects", "failed first · is_repeat = true"),
         ("R5", "Probation cap", "lower cap when on probation"),
         ("R6", "Conflicts", "duplicates skipped · clashes resolved"),
         ("R7", "Class capacity", "venue seats used up → class_full"),
         ("LIMIT", "Subject count", "optional max subjects")]
yy = 240
for code, name, desc in rules:
    add(f'<rect x="1122" y="{yy-17}" width="58" height="24" rx="6" fill="{TEAL}" fill-opacity="0.15" stroke="{TEAL}" stroke-opacity="0.6"/>'
        f'<text x="1151" y="{yy}" fill="{TEAL}" font-size="11.5" font-weight="800" text-anchor="middle" letter-spacing="0.6">{code}</text>'
        f'<text x="1196" y="{yy-2}" fill="{TEXT}" font-size="14" font-weight="600">{esc(name)}</text>'
        f'<text x="1196" y="{yy+16}" fill="{MUTED}" font-size="12">{esc(desc)}</text>')
    yy += 64
card(1100, 790, 460, 560, "LEGEND")
lx, ly = 1124, 870
start(lx + 14, ly); add(f'<text x="{lx+44}" y="{ly+4.5}" fill="{TEXT}" font-size="13">Start</text>')
end(lx + 234, ly); add(f'<text x="{lx+264}" y="{ly+4.5}" fill="{TEXT}" font-size="13">End</text>')
ly += 56
add(f'<rect x="{lx}" y="{ly-18}" width="90" height="36" rx="12" fill="{CARD}" stroke="{PURPLE}" stroke-opacity="0.6"/><text x="{lx+104}" y="{ly+4.5}" fill="{TEXT}" font-size="13">Action</text>')
add(f'<polygon points="{lx+250},{ly-20} {lx+295},{ly} {lx+250},{ly+20} {lx+205},{ly}" fill="{CARD}" stroke="{PURPLE}"/><text x="{lx+310}" y="{ly+4.5}" fill="{TEXT}" font-size="13">Decision</text>')
ly += 54
add(f'<polygon points="{lx+20},{ly-14} {lx+38},{ly} {lx+20},{ly+14} {lx+2},{ly}" fill="{CARD}" stroke="{PURPLE}"/><text x="{lx+52}" y="{ly+4.5}" fill="{TEXT}" font-size="13">Merge / loop</text>')
add(f'<line x1="{lx+205}" y1="{ly}" x2="{lx+290}" y2="{ly}" stroke="{LINE}" stroke-width="1.8" marker-end="url(#arr)"/><text x="{lx+310}" y="{ly+4.5}" fill="{TEXT}" font-size="13">Flow</text>')
ly += 52
for i, (letter, txt) in enumerate([("A", "go to: next subject"), ("C", "go to: next clash loser")]):
    conn(lx + 14, ly + i * 38, letter, PURPLE)
    add(f'<text x="{lx+42}" y="{ly + i*38 + 4.5}" fill="{TEXT}" font-size="13">{txt}</text>')
ly += 100
add(f'<text x="{lx}" y="{ly}" fill="{MUTED}" font-size="12" font-weight="700" letter-spacing="0.6">OUTCOMES</text>')
ly += 30
for i, (col, txt) in enumerate([(GREEN, "Subject assigned"), (ROSE, "Flagged — exception pending"), (AMBER, "Auto-replacement attempted"), (SLATE, "Skipped / return")]):
    yy2 = ly + i * 32
    add(f'<rect x="{lx}" y="{yy2-9}" width="28" height="18" rx="5" fill="{col}" fill-opacity="0.2" stroke="{col}"/><text x="{lx+42}" y="{yy2+4.5}" fill="{TEXT}" font-size="13">{esc(txt)}</text>')
add(f'<text x="{lx}" y="{ly+150}" fill="{TEXT}" font-size="13"><tspan fill="{GREEN}" font-weight="700">yes</tspan> / <tspan fill="{ROSE}" font-weight="700">no</tspan>  decision branches</text>')

o.extend(edges); o.extend(nodes); o.append("</svg>")
svg = "\n".join(o)
open(sys.argv[1], "w").write(svg)
open(sys.argv[2], "w").write(f'<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;background:{BG}}}</style></head><body>{svg}</body></html>')
