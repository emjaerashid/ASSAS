import sys, html
W, H_HDR, ROW = 300, 38, 26
C = [60, 470, 880, 1290, 1700]
BG, CARD, BORDER, ROWLINE = "#0d1017", "#161a23", "#2a303d", "#20252f"
TEXT, MUTED, LINE = "#e6e9ef", "#8a93a6", "#9aa4b8"
GROUPS = {
  "academic":   ("#3b82f6", "Academic structure"),
  "curriculum": ("#14b8a6", "Curriculum"),
  "students":   ("#a855f7", "Students & registration"),
  "schedule":   ("#f59e0b", "Scheduling"),
}
KEYC = {"PK": "#f5c451", "FK": "#60a5fa", "UK": "#c084fc"}

# name -> (x, y, group, junction, fields[(name, type, key, nullable)])
E = {}
def ent(name, x, y, group, fields, junction=False):
    E[name] = dict(x=x, y=y, group=group, junction=junction,
                   fields=[(f + (None, False))[:4] if len(f) < 4 else f for f in fields])
def F(n, t, k=None, null=False): return (n, t, k, null)

ent("PROGRAMME", C[1], 170, "academic", [F("programme_code","varchar","PK"),F("programme_name","varchar"),F("faculty_code","varchar","FK",True),F("total_credits","int"),F("max_credits_per_sem","int"),F("probation_credit_cap","int"),F("total_semesters","int")])
ent("FACULTY", C[0], 222, "academic", [F("faculty_code","varchar","PK"),F("faculty_name","varchar")])
ent("RULE", C[0], 360, "academic", [F("id","int","PK"),F("rule_type","varchar"),F("rule_value","int"),F("programme_code","varchar","FK",True),F("is_active","bool")])
ent("SUBJECT_PROGRAMMES", C[2], 170, "curriculum", [F("id","int","PK"),F("subject_code","varchar","FK"),F("programme_code","varchar","FK")], True)
ent("SUBJECT", C[3], 196, "curriculum", [F("subject_code","varchar","PK"),F("subject_name","varchar"),F("credit_hours","int"),F("semester","int")])
ent("PREREQUISITE", C[4], 196, "curriculum", [F("id","int","PK"),F("subject_code","varchar","FK"),F("prerequisite_subject_code","varchar","FK")])
ent("STUDENT", C[1], 470, "students", [F("id","int","PK"),F("user_id","int","FK UK"),F("programme_code","varchar","FK"),F("photo","image",None,True),F("current_semester","int"),F("status","varchar"),F("total_credits_earned","int"),F("cgpa","decimal"),F("is_repeat","bool"),F("is_transfer","bool")])
ent("USER", C[1], 840, "students", [F("id","int","PK"),F("student_id","varchar","UK"),F("full_name","varchar"),F("ic_passport","varchar"),F("role","varchar"),F("is_active","bool"),F("is_staff","bool"),F("date_joined","datetime")])
ent("ENROLMENT", C[2], 470, "students", [F("id","int","PK"),F("student_id","int","FK"),F("subject_code","varchar","FK"),F("semester","varchar"),F("status","varchar"),F("grade","varchar",None,True),F("is_repeat","bool"),F("assigned_at","datetime")])
ent("EXCEPTION_LOG", C[2], 790, "students", [F("id","int","PK"),F("student_id","int","FK"),F("subject_code","varchar","FK"),F("enrolment_id","int","FK",True),F("reason","varchar"),F("details","text"),F("status","varchar"),F("reviewed_by","int","FK",True),F("reviewed_at","datetime",None,True),F("created_at","datetime")])
ent("ADD_DROP_REQUEST", C[2], 1158, "students", [F("id","int","PK"),F("student_id","int","FK"),F("subject_code","varchar","FK"),F("action","varchar"),F("reason","text"),F("status","varchar"),F("semester","varchar"),F("reviewed_by","int","FK",True),F("reviewed_at","datetime",None,True),F("admin_remarks","text"),F("created_at","datetime")])
ent("TIME_SLOT", C[3], 470, "schedule", [F("id","int","PK"),F("timetable_id","int","FK"),F("subject_code","varchar","FK"),F("day_of_week","varchar"),F("start_time","time"),F("end_time","time"),F("venue","varchar")])
ent("VENUE", C[4], 626, "schedule", [F("name","varchar","PK"),F("capacity","int")])
ent("TIMETABLE", C[3], 790, "schedule", [F("id","int","PK"),F("title","varchar"),F("semester","varchar"),F("file","file",None,True),F("uploaded_by","int","FK",True),F("uploaded_at","datetime")])
ent("TIMETABLE_PROGRAMMES", C[4], 764, "schedule", [F("id","int","PK"),F("timetable_id","int","FK"),F("programme_code","varchar","FK")], True)

def h(n): return H_HDR + ROW * len(E[n]["fields"])
def L(n): return E[n]["x"]
def R(n): return E[n]["x"] + W
def T(n): return E[n]["y"]
def B(n): return E[n]["y"] + h(n)
def ry(n, i): return E[n]["y"] + H_HDR + ROW * i + ROW / 2
def cx(n, dx=150): return E[n]["x"] + dx

# Edges: points (polyline, parent end first), parent cardinality, child cardinality, label, dashed
# card: "one" = exactly one, "zone" = zero or one, "many" = zero or many
EDGES = [
  ([(R("FACULTY"), 273), (L("PROGRAMME"), 273)], "zone", "many", "offers", False),
  ([(cx("PROGRAMME",40), B("PROGRAMME")), (cx("PROGRAMME",40), ry("RULE",3)), (R("RULE"), ry("RULE",3))], "zone", "many", "governed by", False),
  ([(cx("PROGRAMME"), B("PROGRAMME")), (cx("PROGRAMME"), T("STUDENT"))], "one", "many", "enrols", False),
  ([(R("PROGRAMME"), 273), (L("SUBJECT_PROGRAMMES"), 273)], "one", "many", "includes", False),
  ([(L("SUBJECT"), 247), (R("SUBJECT_PROGRAMMES"), 247)], "one", "many", "belongs to", False),
  ([(R("SUBJECT"), 273), (L("PREREQUISITE"), 273)], "one", "many", "requires", False),
  ([(R("SUBJECT"), 299), (L("PREREQUISITE"), 299)], "one", "many", "prerequisite of", "below"),
  ([(cx("PROGRAMME",250), T("PROGRAMME")), (cx("PROGRAMME",250), 130), (2050, 130), (2050, ry("TIMETABLE_PROGRAMMES",2)), (R("TIMETABLE_PROGRAMMES"), ry("TIMETABLE_PROGRAMMES",2))], "one", "many", "uses", False),
  ([(L("TIMETABLE"), ry("TIMETABLE",0)), (L("TIMETABLE"), ry("TIMETABLE",0))], None, None, None, False),
  ([(R("TIMETABLE"), ry("TIMETABLE",0)), (L("TIMETABLE_PROGRAMMES"), ry("TIMETABLE",0))], "one", "many", "serves", False),
  ([(R("STUDENT"), ry("ENROLMENT",1)), (L("ENROLMENT"), ry("ENROLMENT",1))], "one", "many", "takes", False),
  ([(L("SUBJECT"), 280), (1205, 280), (1205, ry("ENROLMENT",2)), (R("ENROLMENT"), ry("ENROLMENT",2))], "one", "many", "enrolled in", False),
  ([(cx("ENROLMENT"), B("ENROLMENT")), (cx("ENROLMENT"), T("EXCEPTION_LOG"))], "zone", "many", "flagged by", False),
  ([(R("STUDENT"), 715), (850, 715), (850, ry("EXCEPTION_LOG",1)), (L("EXCEPTION_LOG"), ry("EXCEPTION_LOG",1))], "one", "many", "raises", False),
  ([(L("SUBJECT"), 305), (1235, 305), (1235, ry("EXCEPTION_LOG",2)), (R("EXCEPTION_LOG"), ry("EXCEPTION_LOG",2))], "one", "many", "concerns", False),
  ([(R("USER"), ry("EXCEPTION_LOG",7)), (L("EXCEPTION_LOG"), ry("EXCEPTION_LOG",7))], "zone", "many", "reviews", False),
  ([(R("STUDENT"), 741), (820, 741), (820, ry("ADD_DROP_REQUEST",1)), (L("ADD_DROP_REQUEST"), ry("ADD_DROP_REQUEST",1))], "one", "many", "submits", False),
  ([(L("SUBJECT"), 330), (1265, 330), (1265, ry("ADD_DROP_REQUEST",2)), (R("ADD_DROP_REQUEST"), ry("ADD_DROP_REQUEST",2))], "one", "many", "targets", False),
  ([(R("USER"), 1060), (795, 1060), (795, ry("ADD_DROP_REQUEST",7)), (L("ADD_DROP_REQUEST"), ry("ADD_DROP_REQUEST",7))], "zone", "many", "reviews", False),
  ([(cx("USER"), B("USER")), (cx("USER"), 1545), (cx("TIMETABLE"), 1545), (cx("TIMETABLE"), B("TIMETABLE"))], "zone", "many", "uploads", False),
  ([(cx("USER"), T("USER")), (cx("USER"), B("STUDENT"))], "one", "zone", "has profile", False),
  ([(cx("SUBJECT"), B("SUBJECT")), (cx("SUBJECT"), T("TIME_SLOT"))], "one", "many", "scheduled in", False),
  ([(cx("TIMETABLE"), T("TIMETABLE")), (cx("TIMETABLE"), B("TIME_SLOT"))], "one", "many", "contains", False),
  ([(L("VENUE"), ry("TIME_SLOT",6)), (R("TIME_SLOT"), ry("TIME_SLOT",6))], "zone", "many", "hosts · by name", True),
]
EDGES = [e for e in EDGES if e[1]]

WIDTH, HEIGHT = 2110, 1600
o = []
o.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" font-family="-apple-system, BlinkMacSystemFont, \'Inter\', \'Segoe UI\', Helvetica, Arial, sans-serif">')
o.append(f'<defs><pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#1b202b"/></pattern>'
         f'<filter id="sh" x="-10%" y="-10%" width="120%" height="120%"><feDropShadow dx="0" dy="6" stdDeviation="8" flood-color="#000" flood-opacity="0.45"/></filter></defs>')
o.append(f'<rect width="100%" height="100%" fill="{BG}"/><rect width="100%" height="100%" fill="url(#dots)"/>')

# Title
o.append(f'<text x="60" y="62" fill="{TEXT}" font-size="30" font-weight="700" letter-spacing="0.3">ASSAS — Entity Relationship Diagram</text>')
o.append(f'<text x="60" y="92" fill="{MUTED}" font-size="15">Source: backend/core/models.py  ·  15 tables  ·  crow’s-foot notation</text>')
gx = 1240
for key, (col, label) in GROUPS.items():
    o.append(f'<rect x="{gx}" y="52" width="14" height="14" rx="3" fill="{col}"/><text x="{gx+22}" y="64" fill="{TEXT}" font-size="14">{label}</text>')
    gx += 32 + len(label) * 7.6 + 18

def esc(s): return html.escape(s)

# ---- edges (drawn first, each with a background halo so later lines "hop" over earlier ones)
def unit(a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    n = (dx*dx+dy*dy) ** .5 or 1
    return dx/n, dy/n

def marker(p, d, kind):
    # p: point on box edge, d: unit vector pointing away from the box along the line
    px, py = p; dx, dy = d; nx, ny = -dy, dx
    s = []
    def at(t, k=0): return (px + dx*t + nx*k, py + dy*t + ny*k)
    def bar(t):
        a, b = at(t, -8), at(t, 8)
        s.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}"/>')
    def circ(t):
        c = at(t); s.append(f'<circle cx="{c[0]}" cy="{c[1]}" r="5.5" fill="{BG}"/>')
    if kind == "one":
        bar(9); bar(16)
    elif kind == "zone":
        bar(9); circ(23)
    elif kind == "many":
        tip = at(15)
        for k in (-9, 0, 9):
            e = at(0, k); s.append(f'<line x1="{tip[0]}" y1="{tip[1]}" x2="{e[0]}" y2="{e[1]}"/>')
        circ(23)
    return "".join(s)

labels = []
for pts, pc, cc, label, dashed in EDGES:
    d = "M" + " L".join(f"{x},{y}" for x, y in pts)
    o.append(f'<path d="{d}" fill="none" stroke="{BG}" stroke-width="9"/>')
    dash = ' stroke-dasharray="7 6"' if dashed is True else ""
    o.append(f'<g stroke="{LINE}" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="{d}"{dash}/>'
             + marker(pts[0], unit(pts[0], pts[1]), pc) + marker(pts[-1], unit(pts[-1], pts[-2]), cc) + '</g>')
    # label on the longest segment
    segs = list(zip(pts, pts[1:]))
    a, b = max(segs, key=lambda s: abs(s[0][0]-s[1][0]) + abs(s[0][1]-s[1][1]))
    mx, my = (a[0]+b[0])/2, (a[1]+b[1])/2
    seglen = abs(a[0]-b[0]) + abs(a[1]-b[1])
    w = len(label) * 6.6 + 16
    if seglen < 170:
        if a[1] == b[1]: my += 21 if dashed == "below" else -21
        else: mx += w/2 + 10
    mx, my = {"raises": (850, 800), "submits": (820, 905)}.get(label, (mx, my))
    labels.append((mx, my, label))

for x, y, t in labels:
    w = len(t) * 6.6 + 16
    labels_svg = (f'<rect x="{x-w/2}" y="{y-10}" width="{w}" height="20" rx="10" fill="#1d2230" stroke="{BORDER}"/>'
                  f'<text x="{x}" y="{y+4.5}" fill="#c7cede" font-size="12" text-anchor="middle" font-style="italic">{esc(t)}</text>')
    o.append(labels_svg)

# ---- entities
for n, e in E.items():
    x, y = e["x"], e["y"]; hh = h(n); col = GROUPS[e["group"]][0]
    dash = ' stroke-dasharray="5 4"' if e["junction"] else ""
    o.append(f'<g filter="url(#sh)"><rect x="{x}" y="{y}" width="{W}" height="{hh}" rx="10" fill="{CARD}" stroke="{BORDER}"{dash}/></g>')
    o.append(f'<path d="M{x},{y+H_HDR} V{y+10} a10,10 0 0 1 10,-10 H{x+W-10} a10,10 0 0 1 10,10 V{y+H_HDR} Z" fill="{col}" fill-opacity="0.22"/>')
    o.append(f'<rect x="{x}" y="{y}" width="4" height="{H_HDR}" fill="{col}"/>' if False else "")
    o.append(f'<line x1="{x}" y1="{y+H_HDR}" x2="{x+W}" y2="{y+H_HDR}" stroke="{col}" stroke-width="2"/>')
    o.append(f'<circle cx="{x+18}" cy="{y+H_HDR/2}" r="5" fill="{col}"/>')
    o.append(f'<text x="{x+32}" y="{y+24}" fill="{TEXT}" font-size="14.5" font-weight="700" letter-spacing="0.6">{n}</text>')
    if e["junction"] and len(n) < 20:
        o.append(f'<text x="{x+W-14}" y="{y+24}" fill="{MUTED}" font-size="11" text-anchor="end">link table</text>')
    for i, (fn, ft, fk, nul) in enumerate(e["fields"]):
        yy = y + H_HDR + ROW * i
        if i: o.append(f'<line x1="{x+10}" y1="{yy}" x2="{x+W-10}" y2="{yy}" stroke="{ROWLINE}"/>')
        cy = yy + ROW/2 + 4.5
        kx = x + 12
        if fk:
            for k in fk.split():
                kc = KEYC[k]
                o.append(f'<rect x="{kx}" y="{yy+6}" width="24" height="14" rx="3" fill="{kc}" fill-opacity="0.16" stroke="{kc}" stroke-opacity="0.6"/>'
                         f'<text x="{kx+12}" y="{yy+16.5}" fill="{kc}" font-size="9.5" font-weight="700" text-anchor="middle">{k}</text>')
                kx += 27
        weight = ' font-weight="600"' if fk and "PK" in fk else ""
        o.append(f'<text x="{x+68}" y="{cy}" fill="{TEXT}" font-size="13"{weight}>{esc(fn)}</text>')
        tt = ft + ("?" if nul else "")
        o.append(f'<text x="{x+W-12}" y="{cy}" fill="{MUTED}" font-size="12" text-anchor="end" font-family="ui-monospace, SFMono-Regular, Menlo, monospace">{esc(tt)}</text>')

# ---- legend (bottom of column 0)
lx, ly, lw = C[0], 600, W
o.append(f'<rect x="{lx}" y="{ly}" width="{lw}" height="310" rx="10" fill="{CARD}" stroke="{BORDER}"/>')
o.append(f'<text x="{lx+18}" y="{ly+30}" fill="{TEXT}" font-size="14.5" font-weight="700" letter-spacing="0.6">LEGEND</text>')
o.append(f'<line x1="{lx}" y1="{ly+44}" x2="{lx+lw}" y2="{ly+44}" stroke="{BORDER}"/>')
rows = [("one", "Exactly one"), ("zone", "Zero or one"), ("many", "Zero or many")]
yy = ly + 74
for kind, txt in rows:
    a, b = (lx+18, yy), (lx+98, yy)
    o.append(f'<g stroke="{LINE}" stroke-width="1.8" fill="none" stroke-linecap="round"><line x1="{a[0]}" y1="{yy}" x2="{b[0]}" y2="{yy}"/>{marker(b, (-1, 0), kind)}</g>')
    o.append(f'<text x="{lx+116}" y="{yy+4.5}" fill="{TEXT}" font-size="13">{txt}</text>')
    yy += 34
o.append(f'<line x1="{lx+18}" y1="{yy}" x2="{lx+98}" y2="{yy}" stroke="{LINE}" stroke-width="1.8"/><text x="{lx+116}" y="{yy+4.5}" fill="{TEXT}" font-size="13">Foreign-key relationship</text>'); yy += 30
o.append(f'<line x1="{lx+18}" y1="{yy}" x2="{lx+98}" y2="{yy}" stroke="{LINE}" stroke-width="1.8" stroke-dasharray="7 6"/><text x="{lx+116}" y="{yy+4.5}" fill="{TEXT}" font-size="13">Logical match (no FK)</text>'); yy += 30
o.append(f'<rect x="{lx+18}" y="{yy-11}" width="80" height="22" rx="5" fill="none" stroke="{BORDER}" stroke-dasharray="5 4"/><text x="{lx+116}" y="{yy+4.5}" fill="{TEXT}" font-size="13">Many-to-many link table</text>'); yy += 36
kx = lx + 18
for k, txt in (("PK", "Primary"), ("FK", "Foreign"), ("UK", "Unique")):
    kc = KEYC[k]
    o.append(f'<rect x="{kx}" y="{yy-8}" width="24" height="14" rx="3" fill="{kc}" fill-opacity="0.16" stroke="{kc}" stroke-opacity="0.6"/><text x="{kx+12}" y="{yy+2.5}" fill="{kc}" font-size="9.5" font-weight="700" text-anchor="middle">{k}</text><text x="{kx+30}" y="{yy+3.5}" fill="{TEXT}" font-size="12.5">{txt}</text>')
    kx += 92
yy += 30
o.append(f'<text x="{lx+18}" y="{yy+3.5}" fill="{MUTED}" font-size="12.5"><tspan font-family="ui-monospace, Menlo, monospace">type?</tspan>  = nullable column</text>')

o.append('</svg>')
svg = "\n".join(o)
open(sys.argv[1], "w").write(svg)
open(sys.argv[2], "w").write(f'<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;background:{BG}}}</style></head><body>{svg}</body></html>')
