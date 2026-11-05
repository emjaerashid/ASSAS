import sys, html
BG, CARD, BORDER = "#0d1017", "#161a23", "#2a303d"
TEXT, MUTED, LINE = "#e6e9ef", "#8a93a6", "#9aa4b8"
BLUE, PURPLE, AMBER, TEAL = "#3b82f6", "#a855f7", "#f59e0b", "#14b8a6"
GREEN, ROSE, SLATE = "#22c55e", "#f43f5e", "#64748b"
FONT = "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Helvetica, Arial, sans-serif"
WIDTH, HEIGHT = 2300, 2740
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
add(f'<text x="40" y="62" fill="{TEXT}" font-size="30" font-weight="700" letter-spacing="0.3">ASSAS — Rule Engine Activity Diagram</text>')
add(f'<text x="40" y="92" fill="{MUTED}" font-size="15">Source: backend/core/rule_engine.py  ·  semester subject assignment, per student</text>')

# swimlanes
for x0, x1, col, title, sub in LANES:
    add(f'<rect x="{x0}" y="120" width="{x1-x0}" height="{HEIGHT-160}" rx="14" fill="{col}" fill-opacity="0.035" stroke="{col}" stroke-opacity="0.28"/>')
    add(f'<path d="M{x0},{170} V{134} a14,14 0 0 1 14,-14 H{x1-14} a14,14 0 0 1 14,14 V170 Z" fill="{col}" fill-opacity="0.18"/>')
    add(f'<line x1="{x0}" y1="170" x2="{x1}" y2="170" stroke="{col}" stroke-width="2"/>')
    add(f'<text x="{x0+20}" y="151" fill="{TEXT}" font-size="16" font-weight="700" letter-spacing="0.4">{esc(title)}</text>')
    add(f'<text x="{x1-18}" y="151" fill="{MUTED}" font-size="11.5" text-anchor="end" font-family="ui-monospace, Menlo, monospace">{esc(sub)}</text>')

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

# ---------------- Lane 1
A = 260
start(A, 205)
a1 = action(A, 285, 320, 70, "Admin runs semester assignment", "semester code · max subjects · programme / faculty", BLUE)
path([(A, 219), (A, a1["t"])])
a2 = action(A, 395, 320, 64, "Select eligible students", "status = active or probation", BLUE)
path([(A, a1["b"]), (A, a2["t"])])
m1 = merge(A, 480, BLUE); conn(A + 44, 480, "B", BLUE)
nodes.append(f'<text x="{A+64}" y="{484}" fill="{MUTED}" font-size="12">next student</text>')
path([(A, a2["b"]), (A, m1["t"])])
d1 = decision(A, 590, ["Enrolments already exist", "for this semester?"], col=BLUE)
path([(A, m1["b"]), (A, d1["t"])])
d2 = decision(A, 715, ["Every required subject", "already assigned?"], col=BLUE)
path([(A, d1["b"]), (A, d2["t"])]); tag(A + 10, d1["b"] + 17, "yes", YES)
a3 = action(560, 715, 220, 64, "Return existing result", "skipped = true", SLATE)
path([(d2["r"], 715), (a3["l"], 715)]); tag(d2["r"] + 6, 708, "yes", YES)
path([(560, a3["b"]), (560, 795 - 13)]); conn(560, 795, "B", BLUE)
a4 = action(A, 845, 300, 64, "Clear stale exceptions", "delete student’s pending ExceptionLogs", BLUE)
path([(A, d2["b"]), (A, a4["t"])]); tag(A + 10, d2["b"] + 17, "no", NO)
path([(d1["l"], 590), (95, 590), (95, 845), (a4["l"], 845)]); tag(d1["l"] - 8, 582, "no", NO, "end")
a5 = action(A, 960, 320, 74, "Initialise rule engine", "credit cap = probation cap if on probation,\nelse programme max credits / semester", BLUE)
path([(A, a4["b"]), (A, a5["t"])])

# ---------------- Lane 2
Bx = 1100
b1 = action(Bx, 960, 340, 74, "Build candidate subject list", "failed subjects first (repeats), then this semester’s\nsubjects — only those with a timetable slot", PURPLE)
path([(a5["r"], 960), (b1["l"], 960)])
b2 = action(Bx, 1075, 340, 66, "Resolve time-slot clashes", "overlap → keep higher credit hours, set loser aside", PURPLE)
path([(Bx, b1["b"]), (Bx, b2["t"])])
m2 = merge(Bx, 1165); conn(Bx + 44, 1165, "A", PURPLE)
nodes.append(f'<text x="{Bx+64}" y="1169" fill="{MUTED}" font-size="12">next subject</text>')
path([(Bx, b2["b"]), (Bx, m2["t"])])
d3 = decision(Bx, 1265, ["Subjects left", "to evaluate?"])
path([(Bx, m2["b"]), (Bx, d3["t"])])

chain = [
  (1380, ["Already passed?"], "R1", "yes", "skip"),
  (1490, ["Already assigned", "this semester?"], "R6", "yes", "skip"),
  (1600, ["All prerequisites", "passed?"], "R2", "no", "prerequisite_unmet"),
  (1710, ["Credits would", "exceed cap?"], "R3 · R5", "yes", "credit_limit | probation_cap"),
  (1820, ["Subject count", "limit reached?"], "LIMIT", "yes", "subject_limit_exceeded"),
  (1930, ["Class full?", "(venue seats)"], "R7", "yes", "class_full"),
]
prev = d3; prev_label = ("yes", YES)
FLAG_BUS = 1570
for cy, lines, rule, out, outcome in chain:
    d = decision(Bx, cy, lines, rule=rule)
    path([(Bx, prev["b"]), (Bx, d["t"])]); tag(Bx + 10, prev["b"] + 17, *prev_label)
    cont = "no" if out == "yes" else "yes"
    prev_label = (cont, YES if cont == "yes" else NO)
    tag(d["r"] + 8, cy - 8, out, YES if out == "yes" else NO)
    if outcome == "skip":
        path([(d["r"], cy), (1325, cy)])
        chip(1360, cy, "skip", SLATE); path([(1390, cy), (1412, cy)]); conn(1426, cy, "A", PURPLE)
    elif outcome == "class_full":
        path([(d["r"], cy), (1720, cy)]); pill(1395, cy, outcome, AMBER)
    else:
        path([(d["r"], cy), (FLAG_BUS, cy)], arrow=False); pill(1400, cy, outcome, ROSE)
    prev = d
b3 = action(Bx, 2050, 340, 82, "Assign subject", "create Enrolment (assigned) · is_repeat if failed\nbefore (R4) · add credit hours", GREEN)
path([(Bx, prev["b"]), (Bx, b3["t"])]); tag(Bx + 10, prev["b"] + 17, *prev_label)
path([(Bx, b3["b"]), (Bx, 2135 - 13)]); conn(Bx, 2135, "A", PURPLE)

m3 = merge(Bx, 2215); conn(Bx + 44, 2215, "C", PURPLE)
nodes.append(f'<text x="{Bx+64}" y="2219" fill="{MUTED}" font-size="12">next clash loser</text>')
path([(d3["l"], 1265), (780, 1265), (780, 2215), (m3["l"], 2215)]); tag(d3["l"] - 8, 1257, "no", NO, "end")
d10 = decision(Bx, 2320, ["Clash losers", "left?"], rule="R6")
path([(Bx, m3["b"]), (Bx, d10["t"])])
b4 = action(Bx, 2445, 340, 66, "Return student summary", "assigned codes · credits · exceptions", PURPLE)
path([(Bx, d10["b"]), (Bx, b4["t"])]); tag(Bx + 10, d10["b"] + 17, "no", NO)
path([(d10["r"], 2320), (1590, 2320), (1590, 1930)]); tag(d10["r"] + 8, 2312, "yes", YES); pill(1395, 2320, "conflict", AMBER)

# ---------------- Lane 1 (end)
d11 = decision(A, 2445, ["More students?"], w=230, h=84, col=BLUE)
path([(b4["l"], 2445), (d11["r"], 2445)])
path([(d11["l"], 2445), (65, 2445), (65, 480), (m1["l"], 480)]); tag(d11["l"] - 8, 2437, "yes", YES, "end")
a6 = action(A, 2565, 300, 64, "Return results for all students", "list of per-student summaries", BLUE)
path([(A, d11["b"]), (A, a6["t"])]); tag(A + 10, d11["b"] + 17, "no", NO)
end(A, 2660); path([(A, a6["b"]), (A, 2660 - 18)])

# ---------------- Lane 3
Cx = 1880
# flag group frame
add(f'<rect x="1540" y="1555" width="680" height="300" rx="12" fill="none" stroke="{ROSE}" stroke-opacity="0.45" stroke-dasharray="6 5"/>')
add(f'<text x="1560" y="1578" fill="{ROSE}" font-size="12" font-weight="700" letter-spacing="0.6">FLAG FOR ADMIN REVIEW</text>')
c1 = action(Cx, 1710, 320, 82, "Log exception", "ExceptionLog · status = pending\nreason as flagged · added to report", ROSE)
path([(FLAG_BUS, 1600), (FLAG_BUS, 1820)], arrow=False)
path([(FLAG_BUS, 1710), (c1["l"], 1710)])
path([(Cx, c1["b"]), (Cx, 1810 - 13)]); conn(Cx, 1810, "A", PURPLE)

add(f'<rect x="1540" y="1875" width="700" height="725" rx="12" fill="none" stroke="{AMBER}" stroke-opacity="0.45" stroke-dasharray="6 5"/>')
add(f'<text x="1560" y="1898" fill="{AMBER}" font-size="12" font-weight="700" letter-spacing="0.6">AUTO-REPLACEMENT SUB-PROCESS</text>')
c3 = action(Cx, 1945, 320, 66, "Log exception (pending)", "reason = class_full or conflict", AMBER)
d12 = decision(Cx, 2070, ["Safe to", "auto-replace?"], col=AMBER)
nodes.append(f'<text x="{Cx-150}" y="2066" fill="{MUTED}" font-size="11.5" text-anchor="end">no prerequisite links</text>'
             f'<text x="{Cx-150}" y="2082" fill="{MUTED}" font-size="11.5" text-anchor="end">not semester 7–9</text>')
path([(Cx, c3["b"]), (Cx, d12["t"])])
c4 = action(Cx, 2200, 320, 90, "Find clash-free replacements", "same programme · scheduled this semester\nnot passed / assigned · no time overlap\nseats left · ordered by semester, code", AMBER)
path([(Cx, d12["b"]), (Cx, c4["t"])]); tag(Cx + 10, d12["b"] + 17, "yes", YES)
d13 = decision(Cx, 2330, ["Replacement", "found?"], w=230, h=88, col=AMBER)
path([(Cx, c4["b"]), (Cx, d13["t"])])
c5 = action(Cx, 2450, 320, 82, "Enrol replacement", "first candidate · exception → approved\n(auto-resolved) · add credit hours", GREEN)
path([(Cx, d13["b"]), (Cx, c5["t"])]); tag(Cx + 10, d13["b"] + 17, "yes", YES)
c6 = action(2155, 2330, 150, 74, "Leave pending", "for admin\nreview", ROSE)
path([(d12["r"], 2070), (2155, 2070), (2155, c6["t"])]); tag(d12["r"] + 8, 2062, "no", NO)
path([(d13["r"], 2330), (c6["l"], 2330)]); tag(d13["r"] + 8, 2322, "no", NO)
rw = chip(Cx, 2555, "return  →  A if class full  ·  C if clash", SLATE)
path([(Cx, c5["b"]), (Cx, 2555 - 13)])
path([(2155, c6["b"]), (2155, 2555), (Cx + rw/2, 2555)])

# ---------------- info cards (empty lane tops)
def card(x, y, w, hh, title):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{hh}" rx="12" fill="{CARD}" stroke="{BORDER}"/>'
        f'<text x="{x+20}" y="{y+30}" fill="{TEXT}" font-size="14.5" font-weight="700" letter-spacing="0.6">{esc(title)}</text>'
        f'<line x1="{x}" y1="{y+44}" x2="{x+w}" y2="{y+44}" stroke="{BORDER}"/>')
card(760, 205, 680, 640, "RULE ORDER  ·  fixed, Chapter 3 §3.7.5")
rules = [("R1", "Already passed check", "subject passed before → skip"),
         ("R2", "Prerequisite validation", "any prerequisite not passed → flag"),
         ("R3", "Credit limit check", "assigned + credit hours > cap → flag"),
         ("R4", "Repeat subject handling", "failed subjects ordered first, is_repeat = true"),
         ("R5", "Probation cap enforcement", "cap = probation_credit_cap when on probation"),
         ("R6", "Conflict detection", "already assigned → skip · time-slot clash → loser"),
         ("R7", "Class capacity check", "venue seats used up → class_full"),
         ("LIMIT", "Subject count limit", "optional max_subjects for the semester")]
yy = 290
for code, name, desc in rules:
    add(f'<rect x="784" y="{yy-17}" width="58" height="24" rx="6" fill="{TEAL}" fill-opacity="0.15" stroke="{TEAL}" stroke-opacity="0.6"/>'
        f'<text x="813" y="{yy}" fill="{TEAL}" font-size="11.5" font-weight="800" text-anchor="middle" letter-spacing="0.6">{code}</text>'
        f'<text x="860" y="{yy-2}" fill="{TEXT}" font-size="14" font-weight="600">{esc(name)}</text>'
        f'<text x="860" y="{yy+16}" fill="{MUTED}" font-size="12">{esc(desc)}</text>')
    yy += 68

card(1540, 205, 680, 640, "LEGEND")
lx, ly = 1564, 290
start(lx + 14, ly); add(f'<text x="{lx+50}" y="{ly+4.5}" fill="{TEXT}" font-size="13">Start</text>')
end(lx + 14 + 300, ly); add(f'<text x="{lx+350}" y="{ly+4.5}" fill="{TEXT}" font-size="13">End</text>')
ly += 60
add(f'<rect x="{lx}" y="{ly-20}" width="120" height="40" rx="12" fill="{CARD}" stroke="{PURPLE}" stroke-opacity="0.6"/><text x="{lx+140}" y="{ly+4.5}" fill="{TEXT}" font-size="13">Action</text>')
add(f'<polygon points="{lx+360},{ly-22} {lx+410},{ly} {lx+360},{ly+22} {lx+310},{ly}" fill="{CARD}" stroke="{PURPLE}"/><text x="{lx+430}" y="{ly+4.5}" fill="{TEXT}" font-size="13">Decision</text>')
ly += 60
add(f'<polygon points="{lx+20},{ly-14} {lx+38},{ly} {lx+20},{ly+14} {lx+2},{ly}" fill="{CARD}" stroke="{PURPLE}"/><text x="{lx+56}" y="{ly+4.5}" fill="{TEXT}" font-size="13">Merge / loop entry</text>')
add(f'<line x1="{lx+310}" y1="{ly}" x2="{lx+400}" y2="{ly}" stroke="{LINE}" stroke-width="1.8" marker-end="url(#arr)"/><text x="{lx+430}" y="{ly+4.5}" fill="{TEXT}" font-size="13">Control flow</text>')
ly += 62
for i, (letter, col, txt) in enumerate([("A", PURPLE, "go to: next subject"), ("B", BLUE, "go to: next student"), ("C", PURPLE, "go to: next clash loser")]):
    conn(lx + 14, ly + i * 40, letter, col)
    add(f'<text x="{lx+42}" y="{ly + i*40 + 4.5}" fill="{TEXT}" font-size="13">{txt}</text>')
ly += 140
add(f'<text x="{lx}" y="{ly}" fill="{MUTED}" font-size="12" font-weight="700" letter-spacing="0.6">OUTCOMES</text>')
ly += 30
for i, (col, txt) in enumerate([(GREEN, "Subject assigned (Enrolment created)"), (ROSE, "Flagged — ExceptionLog pending"), (AMBER, "Auto-replacement attempted"), (SLATE, "Skipped / no change")]):
    yy2 = ly + i * 34
    add(f'<rect x="{lx}" y="{yy2-9}" width="28" height="18" rx="5" fill="{col}" fill-opacity="0.2" stroke="{col}"/><text x="{lx+42}" y="{yy2+4.5}" fill="{TEXT}" font-size="13">{esc(txt)}</text>')
add(f'<text x="{lx+330}" y="{ly+4.5}" fill="{TEXT}" font-size="13"><tspan fill="{GREEN}" font-weight="700">yes</tspan> / <tspan fill="{ROSE}" font-weight="700">no</tspan>  decision branches</text>')
add(f'<text x="{lx+330}" y="{ly+38.5}" fill="{MUTED}" font-size="12">exception reasons shown in</text>')
add(f'<text x="{lx+330}" y="{ly+56}" fill="{MUTED}" font-size="12" font-family="ui-monospace, Menlo, monospace">monospace pills</text>')

o.extend(edges); o.extend(nodes); o.append("</svg>")
svg = "\n".join(o)
open(sys.argv[1], "w").write(svg)
open(sys.argv[2], "w").write(f'<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;background:{BG}}}</style></head><body>{svg}</body></html>')
