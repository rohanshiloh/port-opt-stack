"""Draw the 'One Run in Pictures' charts as plain SVG from bench/results.jsonl,
bench/default_rho_run.jsonl and bench/multistrat.json, in the house style of
Anatomy of a Fill: 460x280, CSS variables for colour, no charting library."""
import json, math, os
H = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(H, "..", "bench")
tuned = [json.loads(l) for l in open(os.path.join(B, "results.jsonl"))]
default = [json.loads(l) for l in open(os.path.join(B, "default_rho_run.jsonl"))]
ms = json.load(open(os.path.join(B, "multistrat.json")))
single = [r for r in tuned if r["kind"] == "single"]
mpc = [r for r in tuned if r["kind"] == "mpc"]
X0, X1, Y0, Y1 = 58, 364, 30, 236
MONO = 'font-family="JetBrains Mono,monospace"'; SANS = 'font-family="Schibsted Grotesk,sans-serif"'

def axis_log(vmin, vmax, label, ticks):
    lo, hi = math.log10(vmin), math.log10(vmax)
    f = lambda v: Y1 - (math.log10(v) - lo) / (hi - lo) * (Y1 - Y0)
    s = [f'<text x="52" y="18" {SANS} font-size="10.5" fill="var(--muted)">{label}</text>']
    for t, txt in ticks:
        y = f(t); s.append(f'<line x1="{X0}" y1="{y:.1f}" x2="{X1}" y2="{y:.1f}" stroke="var(--line)"/>'
                          f'<text x="{X0-6}" y="{y+3.5:.1f}" text-anchor="end" {MONO} font-size="9.5" fill="var(--muted)">{txt}</text>')
    return f, "".join(s)

def axis_lin(vmin, vmax, label, ticks):
    f = lambda v: Y1 - (v - vmin) / (vmax - vmin) * (Y1 - Y0)
    s = [f'<text x="52" y="18" {SANS} font-size="10.5" fill="var(--muted)">{label}</text>']
    for t in ticks:
        y = f(t); s.append(f'<line x1="{X0}" y1="{y:.1f}" x2="{X1}" y2="{y:.1f}" stroke="var(--line)"/>'
                          f'<text x="{X0-6}" y="{y+3.5:.1f}" text-anchor="end" {MONO} font-size="9.5" fill="var(--muted)">{t:g}</text>')
    return f, "".join(s)

def xcats(cats, xlabel):
    step = (X1 - X0) / len(cats); xs = [X0 + step * (i + 0.5) for i in range(len(cats))]
    s = "".join(f'<text x="{x:.1f}" y="251" text-anchor="middle" {MONO} font-size="9.5" fill="var(--muted)">{c}</text>' for x, c in zip(xs, cats))
    s += f'<text x="{X1}" y="267" text-anchor="end" {SANS} font-size="10.5" fill="var(--muted)">{xlabel}</text>'
    return xs, s

def line(xs, ys, color, dash=""):
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    d = f' stroke-dasharray="{dash}"' if dash else ""
    c = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="var({color})"/>' for x, y in zip(xs, ys))
    return f'<polyline points="{pts}" fill="none" stroke="var({color})" stroke-width="2"{d}/>' + c

def lab(x, y, text, color):
    return f'<text x="{x:.1f}" y="{y:.1f}" {SANS} font-size="10.5" font-weight="600" fill="var({color})">{text}</text>'

def svg(body, aria):
    return f'<svg viewBox="0 0 460 280" role="img" aria-label="{aria}">{body}</svg>'

def cold():
    cats = ["1k", "2k", "5k", "10k"]; xs, xa = xcats(cats, "names in the book (50 factors)")
    f, ya = axis_log(30, 40000, "cold solve, ms (log scale)", [(100, "100"), (1000, "1 s"), (10000, "10 s")])
    d = [r["cold_ms"] for r in default]; t = [r["cold_ms"] for r in single]; c = [r["clarabel_ms"] for r in single]
    b = xa + ya + line(xs[:3], [f(v) for v in d], "--bad", "5 4") + line(xs, [f(v) for v in t], "--s0") + line(xs, [f(v) for v in c], "--sh")
    b += lab(xs[0] - 30, f(d[0]) - 34, "OSQP, default ρ", "--bad") + lab(xs[2] + 6, f(t[2]) - 14, "OSQP, ρ = n/70", "--s0") + lab(xs[2] + 10, f(c[2]) + 22, "Clarabel", "--sh")
    return svg(b, "Cold solve time against book size. OSQP with its default rho takes 0.52, 2.8 and 21 seconds at 1,000, 2,000 and 5,000 names. With rho set to n over 70 it takes 0.07, 0.31, 2.1 and 9.3 seconds up to 10,000 names. Clarabel takes 0.07, 0.19, 0.66 and 2.0 seconds.")

def warm():
    cats = ["1k", "2k", "5k", "10k"]; xs, xa = xcats(cats, "names in the book")
    f, ya = axis_log(2, 3000, "one re-solve after a fill, ms (log)", [(10, "10"), (100, "100"), (1000, "1 s")])
    m = [r["warm_med_ms"] for r in single]; p = [r["warm_p90_ms"] for r in single]; c = [r["clarabel_ms"] for r in single]
    b = xa + ya + line(xs, [f(v) for v in c], "--sh", "5 4") + line(xs, [f(v) for v in p], "--sig") + line(xs, [f(v) for v in m], "--s0")
    b += lab(xs[0] - 30, f(c[0]) - 44, "Clarabel, every re-solve cold", "--sh") + lab(xs[2] + 6, f(p[2]) + 22, "OSQP warm, 90th pct", "--sig") + lab(xs[2] + 4, f(m[2]) + 30, "OSQP warm, median", "--s0")
    return svg(b, "Time to re-solve after a fill. OSQP warm-started has a median of 3.5, 8.6, 24 and 59 milliseconds from 1,000 to 10,000 names, and a 90th percentile of 48, 11, 300 and 393. Clarabel cannot warm-start, so each re-solve costs its cold time, 69 to 1,973 milliseconds.")

def iters():
    cats = ["1k", "2k", "5k", "10k"]; xs, xa = xcats(cats, "names in the book")
    f, ya = axis_log(10, 40000, "ADMM iterations (log)", [(100, "100"), (1000, "1,000"), (10000, "10,000")])
    d = [r["cold_iter"] for r in default]; t = [r["cold_iter"] for r in single]; w = [r["warm_avg_iter"] for r in single]
    b = xa + ya + line(xs[:3], [f(v) for v in d], "--bad", "5 4") + line(xs, [f(v) for v in t], "--s0") + line(xs, [f(v) for v in w], "--ok")
    b += lab(xs[1] + 4, f(d[1]) + 22, "cold, default ρ", "--bad") + lab(xs[1] + 20, f(t[1]) + 22, "cold, ρ = n/70", "--s0") + lab(xs[1] - 10, f(w[1]) + 20, "warm, mean", "--ok")
    return svg(b, "Iterations. Cold solves with the default rho take 3,675, 9,725 and 24,925 iterations; with rho n over 70, 575, 1,025, 2,475 and 4,900. Warm re-solves after a fill average 69, 28, 66 and 462.")

def mem():
    ns = [r["n"] for r in single]; m = [r["rss_solver_MB"] for r in single]
    fx = lambda v: X0 + 10 + v / 10000 * (X1 - X0 - 20)
    f, ya = axis_lin(0, 60, "solver memory, MB (resident, after setup + solve)", [0, 20, 40, 60])
    xa = "".join(f'<text x="{fx(v):.1f}" y="251" text-anchor="middle" {MONO} font-size="9.5" fill="var(--muted)">{v//1000}k</text>' for v in [2000, 5000, 10000])
    xa += f'<text x="{X1}" y="267" text-anchor="end" {SANS} font-size="10.5" fill="var(--muted)">names in the book (to scale)</text>'
    b = xa + ya + line([fx(v) for v in ns], [f(v) for v in m], "--s0")
    b += "".join(f'<text x="{fx(x)-6:.1f}" y="{f(v)-9:.1f}" text-anchor="end" {MONO} font-size="10" fill="var(--fg)">{v:.1f}</text>' for x, v in zip(ns, m))
    return svg(b, "Solver memory grows linearly with the book: 5.8, 11.4, 28.2 and 56.3 megabytes at 1,000, 2,000, 5,000 and 10,000 names, about 5.6 megabytes per thousand names.")

def eps():
    # n=2000, measured against Clarabel's solution (bench/validate.py and the rho sweep in Lab D1)
    pts = [(3350, 1.433, "ε 1e-3"), (7375, 0.660, "ε 1e-4"), (9725, 0.079, "ε 1e-5"), (900, 0.074, "ε 1e-5, ρ 30")]
    lo, hi = math.log10(500), math.log10(20000)
    fx = lambda v: X0 + (math.log10(v) - lo) / (hi - lo) * (X1 - X0)
    f, ya = axis_log(0.03, 3, "largest weight error, in average weights (log)", [(0.1, "0.1"), (1, "1")])
    xa = "".join(f'<text x="{fx(v):.1f}" y="251" text-anchor="middle" {MONO} font-size="9.5" fill="var(--muted)">{t}</text>' for v, t in [(1000, "1k"), (3000, "3k"), (10000, "10k")])
    xa += f'<text x="{X1}" y="267" text-anchor="end" {SANS} font-size="10.5" fill="var(--muted)">iterations to stop (log)</text>'
    b = xa + ya + line([fx(p[0]) for p in pts[:3]], [f(p[1]) for p in pts[:3]], "--bad", "5 4")
    x, y = fx(pts[3][0]), f(pts[3][1]); b += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="var(--s0)"/>'
    for p, c, dx, dy in [(pts[0], "--bad", -62, 4), (pts[1], "--bad", 10, 4), (pts[2], "--bad", 10, 4), (pts[3], "--s0", -10, 22)]:
        b += lab(fx(p[0]) + dx, f(p[1]) + dy, p[2], c)
    y1 = f(0.1); b += f'<line x1="{X0}" y1="{y1:.1f}" x2="{X1}" y2="{y1:.1f}" stroke="var(--ok)" stroke-dasharray="2 3"/>' + f'<text x="{X1}" y="{y1-5:.1f}" text-anchor="end" {SANS} font-size="9.5" fill="var(--ok)">a tenth of a weight</text>'
    return svg(b, "Accuracy against iterations at 2,000 names, measured against Clarabel. With the default rho, tolerance 1e-3 stops after 3,350 iterations with weights off by 1.4 average weights; 1e-4 after 7,375, off by 0.66; 1e-5 after 9,725, off by 0.08. With rho 30, tolerance 1e-5 stops after 900 iterations, off by 0.07.")

def net():
    cats = ["independent", "overlap 0.4", "overlap 0.8"]; xs, xa = xcats(cats, "how much the four strategies' alphas share")
    f, ya = axis_lin(0, 200, "firm utility, bps (alpha − risk − cost of the net trade)", [0, 50, 100, 150, 200])
    b = xa + ya; w = 22
    for x, r in zip(xs, ms):
        for dx, key, col in [(-w - 2, "separate", "--muted"), (2, "joint", "--s0")]:
            v = r[key]["utility_bps"]; y = f(v)
            b += f'<rect x="{x+dx:.1f}" y="{y:.1f}" width="{w}" height="{Y1-y:.1f}" fill="var({col})" fill-opacity="{0.45 if key=="separate" else 1}"/>'
            b += f'<text x="{x+dx+w/2:.1f}" y="{y-5:.1f}" text-anchor="middle" {MONO} font-size="9.5" fill="var(--fg)">{v:.0f}</text>'
    b += f'<rect x="70" y="34" width="10" height="10" fill="var(--muted)" fill-opacity=".45"/><text x="84" y="43" {SANS} font-size="10.5" fill="var(--fg)">optimise, then net</text>'
    b += f'<rect x="200" y="34" width="10" height="10" fill="var(--s0)"/><text x="214" y="43" {SANS} font-size="10.5" fill="var(--fg)">net, then optimise</text>'
    a = ", ".join(f"{r['separate']['utility_bps']:.0f} against {r['joint']['utility_bps']:.0f}" for r in ms)
    return svg(b, f"Firm utility in basis points for four strategies on 1,000 names, optimising separately then netting, against one joint problem with costs on the net trade: {a}, for independent, 0.4 and 0.8 overlap in alpha.")

def horizon():
    cats = ["H = 1", "H = 2", "H = 4"]; xs, xa = xcats(cats, "periods in the horizon, 2,000 names")
    f, ya = axis_log(5, 80000, "solve time, ms (log)", [(10, "10"), (100, "100"), (1000, "1 s"), (10000, "10 s")])
    s1 = single[1]; o = [s1["cold_ms"]] + [r["cold_ms"] for r in mpc]; c = [s1["clarabel_ms"]] + [r["clarabel_ms"] for r in mpc]
    w = [s1["warm_med_ms"]] + [r["warm_med_ms"] for r in mpc]
    b = xa + ya + line(xs, [f(v) for v in o], "--bad", "5 4") + line(xs, [f(v) for v in c], "--sh") + line(xs, [f(v) for v in w], "--s0")
    b += lab(xs[2] + 10, f(o[2]) + 4, "OSQP cold", "--bad") + lab(xs[2] - 52, f(c[2]) + 16, "Clarabel", "--sh") + lab(xs[2] + 10, f(w[2]) + 4, "OSQP warm, median", "--s0")
    return svg(b, "Multi-period problems at 2,000 names. OSQP cold takes 0.31, 3.7 and 45 seconds for horizons of 1, 2 and 4 periods; Clarabel 0.19, 0.96 and 9.7 seconds; OSQP warm re-solves after a fill 8.6, 36 and 76 milliseconds.")

CHARTS = dict(cold=cold, warm=warm, iters=iters, mem=mem, eps=eps, net=net, horizon=horizon)
if __name__ == "__main__":
    for k, fn in CHARTS.items(): print(k, len(fn()))

story = json.load(open(os.path.join(B, "story.json")))

def fills_story():
    """Small multiples: one rebalance, fill by fill. Hollow dot = the book h0, filled = the target h*."""
    st = story["fills"]["steps"]; nm = len(st[0]["h0"]); P = len(st)
    W, H0, top, rowh = 960, 330, 64, 22
    pw = W / P; xmax = max(max(s["h0"] + s["h"]) for s in st) * 1.08
    o = []
    for p, s in enumerate(st):
        x0 = p * pw + 18; x1 = (p + 1) * pw - 10
        fx = lambda v: x0 + v / xmax * (x1 - x0)
        o.append(f'<rect x="{p*pw+4:.1f}" y="6" width="{pw-8:.1f}" height="{H0-12}" rx="6" fill="{"var(--s0-bg)" if p else "var(--sheet)"}" stroke="var(--line)"/>')
        o.append(f'<text x="{x0:.1f}" y="28" {SANS} font-size="13" font-weight="600" fill="var(--fg)" letter-spacing=".04em">{s["label"].upper()}</text>')
        o.append(f'<text x="{x0:.1f}" y="46" {SANS} font-size="11" fill="var(--muted)">turnover left {100*s["tau_left"]:.1f}%</text>')
        for i in range(nm):
            y = top + i * rowh; a, b = fx(s["h0"][i]), fx(s["h"][i])
            o.append(f'<line x1="{x0:.1f}" y1="{y}" x2="{x1:.1f}" y2="{y}" stroke="var(--line)" stroke-dasharray="1 3"/>')
            o.append(f'<line x1="{a:.1f}" y1="{y}" x2="{b:.1f}" y2="{y}" stroke="var(--accent)" stroke-width="2" stroke-opacity=".45"/>')
            o.append(f'<circle cx="{b:.1f}" cy="{y}" r="4.5" fill="var(--accent)"/>')
            o.append(f'<circle cx="{a:.1f}" cy="{y}" r="4.5" fill="var(--sheet)" stroke="var(--fg)" stroke-width="1.3"/>')
        y = top + nm * rowh + 4
        o.append(f'<line x1="{x0:.1f}" y1="{y}" x2="{x1:.1f}" y2="{y}" stroke="var(--muted)"/>')
        o.append(f'<text x="{x0:.1f}" y="{y+14}" {MONO} font-size="9.5" fill="var(--muted)">0</text><text x="{x1:.1f}" y="{y+14}" text-anchor="end" {MONO} font-size="9.5" fill="var(--muted)">{100*xmax:.1f}%</text>')
    aria = "One rebalance, fill by fill, for the ten names that trade most out of 400. In each panel a hollow dot is the current book and a filled dot the target. Each fill executes 35 percent of what is left of every trade, so the hollow dots walk toward the filled ones while the targets barely move, and the turnover left falls from 10 percent to " + f'{100*st[-1]["tau_left"]:.1f}' + " percent."
    return f'<svg viewBox="0 0 {W} {H0}" role="img" aria-label="{aria}">' + "".join(o) + "</svg>"

def roll_story():
    """Small multiples: the H-period plan, re-made each period. Bars = turnover planned per period."""
    st = story["roll"]["steps"]; H = story["roll"]["H"]; P = len(st); T = P + H - 1
    W, H0, base, top = 960, 318, 250, 70
    pw = W / P; ymax = max(max(s["plan"]) for s in st) * 1.12
    o = []
    for p, s in enumerate(st):
        x0 = p * pw + 22; x1 = (p + 1) * pw - 12; bw = (x1 - x0) / T
        fy = lambda v: base - v / ymax * (base - top)
        o.append(f'<rect x="{p*pw+4:.1f}" y="6" width="{pw-8:.1f}" height="{H0-40}" rx="6" fill="var(--sheet)" stroke="var(--line)"/>')
        o.append(f'<text x="{x0:.1f}" y="28" {SANS} font-size="13" font-weight="600" fill="var(--fg)" letter-spacing=".04em">PLAN AT PERIOD {s["t"]}</text>')
        o.append(f'<text x="{x0:.1f}" y="46" {SANS} font-size="11" fill="var(--muted)">expected α of the book {100*s["alpha"]:.2f}%</text>')
        for q in range(p):                                   # what earlier plans executed
            v = st[q]["plan"][0]; x = x0 + q * bw
            o.append(f'<rect x="{x+3:.1f}" y="{fy(v):.1f}" width="{bw-6:.1f}" height="{base-fy(v):.1f}" fill="var(--accent)" fill-opacity=".22"/>')
        for j, v in enumerate(s["plan"]):
            x = x0 + (p + j) * bw
            o.append(f'<rect x="{x+3:.1f}" y="{fy(v):.1f}" width="{bw-6:.1f}" height="{base-fy(v):.1f}" fill="{"var(--accent)" if j==0 else "var(--muted)"}" fill-opacity="{1 if j==0 else .35}"/>')
        o.append(f'<line x1="{x0:.1f}" y1="{base}" x2="{x1:.1f}" y2="{base}" stroke="var(--muted)"/>')
        for t in range(T):
            o.append(f'<text x="{x0+(t+.5)*bw:.1f}" y="{base+15}" text-anchor="middle" {MONO} font-size="9.5" fill="var(--muted)">{t+1}</text>')
        v = s["plan"][0]; o.append(f'<text x="{x0+(p+.5)*bw:.1f}" y="{fy(v)-6:.1f}" text-anchor="middle" {MONO} font-size="9.5" fill="var(--accent)">{100*v:.0f}%</text>')
    o.append(f'<text x="{W-14}" y="{H0-8}" text-anchor="end" {SANS} font-size="10.5" fill="var(--muted)">period · bar = turnover planned · blue = executed now · pale = executed earlier · grey = planned, never sent</text>')
    plans = "; ".join(f'period {s["t"]}: ' + ", ".join(f"{100*v:.0f}" for v in s["plan"]) for s in st)
    return f'<svg viewBox="0 0 {W} {H0}" role="img" aria-label="The four-period plan re-made each period, with alpha decaying by 0.7 a period. Turnover planned per period, in percent, {plans}. Only the first period of each plan is executed.">' + "".join(o) + "</svg>"

CHARTS.update(fills=fills_story, roll=roll_story)

# ── live runs: bench/live_<mode>.csv, written by optDump[] in the OPT tab ──
import csv as _csv
def _live(mode):
    f = os.path.join(B, f"live_{mode}.csv")
    if not os.path.exists(f): return None
    rows = list(_csv.DictReader(open(f)))
    def secs(t):
        h, m, s = t.replace("0D", "").split(":"); return int(h) * 3600 + int(m) * 60 + float(s)
    t0 = min(secs(r["time"]) for r in rows); by = {}
    for r in rows:
        v = lambda k: float(r[k]) if r[k] != "" else None
        by.setdefault(r["sym"], []).append((secs(r["time"]) - t0, v("h0"), v("h"), v("e1"), v("e2"), v("e3"), v("e4")))
    return by

def live_chart(mode):
    by = _live(mode)
    if by is None: return '<p class="notice">Run this mode and <code>optDump[]</code> to draw this chart.</p>'
    syms = ["AAPL", "MSFT", "NVDA", "AMZN", "TSLA", "META", "GOOGL", "JPM"]
    step = 5                                                   # one point every 5 seconds
    ser = {s: [p for i, p in enumerate(by[s]) if i % step == 0] for s in syms}
    tmax = max(p[0] for s in syms for p in ser[s]) / 60
    vals = [x for s in syms for p in ser[s] for x in p[1:3] if x is not None]
    if mode == "mpo": vals += [p[4] for s in syms for p in ser[s] if p[4] is not None]
    lo = min(-0.05, min(vals)); hi = max(0.35, max(vals)); lo = math.floor(lo * 20) / 20; hi = math.ceil(hi * 20) / 20
    W, PH, PW, top = 960, 190, 240, 8
    o = []
    for k, s in enumerate(syms):
        r, c = divmod(k, 4); x0 = c * PW + 44; x1 = (c + 1) * PW - 10; y0 = top + r * PH + 30; y1 = top + (r + 1) * PH - 26
        fx = lambda t: x0 + t / 60 / tmax * (x1 - x0); fy = lambda v: y1 - (v - lo) / (hi - lo) * (y1 - y0)
        feat = s in ("NVDA", "JPM") + {"single": ("MSFT", "META"), "mpo": ("MSFT", "META"), "mso": ("GOOGL",)}[mode]   # the two you asked about, and the ones each caption discusses
        o.append(f'<rect x="{c*PW+4}" y="{top+r*PH+2}" width="{PW-8}" height="{PH-6}" rx="6" fill="var(--sheet)" stroke="{"var(--accent)" if feat else "var(--line)"}" stroke-width="{1.4 if feat else 1}"/>')
        gap = sum(abs(p[2] - p[1]) for p in by[s]) / len(by[s])
        o.append(f'<text x="{x0}" y="{top+r*PH+22}" {SANS} font-size="13" font-weight="600" fill="var(--fg)">{s}</text>'
                 f'<text x="{x1}" y="{top+r*PH+22}" text-anchor="end" {SANS} font-size="10.5" fill="var(--muted)">mean gap {100*gap:.1f}%</text>')
        for v in [0, 0.3] + ([-0.1] if lo <= -0.1 else []) + ([0.4] if hi >= 0.4 else []):
            dash = ' stroke-dasharray="4 3"' if v == 0.3 else ""
            o.append(f'<line x1="{x0}" y1="{fy(v):.1f}" x2="{x1}" y2="{fy(v):.1f}" stroke="{"var(--rose)" if v==0.3 else "var(--line)"}"{dash}/>'
                     f'<text x="{x0-5}" y="{fy(v)+3.5:.1f}" text-anchor="end" {MONO} font-size="9" fill="var(--muted)">{100*v:.0f}%</text>')
        P = ser[s]
        band = " ".join(f"{fx(p[0]):.1f},{fy(p[2]):.1f}" for p in P) + " " + " ".join(f"{fx(p[0]):.1f},{fy(p[1]):.1f}" for p in reversed(P))
        o.append(f'<polygon points="{band}" fill="var(--accent)" fill-opacity=".18"/>')
        if mode == "mso":
            for j in range(3, 7):
                pts = " ".join(f"{fx(p[0]):.1f},{fy(p[j]):.1f}" for p in P if p[j] is not None)
                o.append(f'<polyline points="{pts}" fill="none" stroke="var(--mauve)" stroke-width="1" stroke-opacity=".45"/>')
        if mode == "mpo":
            pts = " ".join(f"{fx(p[0]):.1f},{fy(p[4]):.1f}" for p in P if p[4] is not None)
            o.append(f'<polyline points="{pts}" fill="none" stroke="#d97706" stroke-width="1.3" stroke-dasharray="4 3"/>')
        o.append('<polyline points="' + " ".join(f"{fx(p[0]):.1f},{fy(p[1]):.1f}" for p in P) + '" fill="none" stroke="var(--fg)" stroke-width="1.3" stroke-opacity=".7"/>')
        o.append('<polyline points="' + " ".join(f"{fx(p[0]):.1f},{fy(p[2]):.1f}" for p in P) + '" fill="none" stroke="var(--accent)" stroke-width="2"/>')
        o.append(f'<text x="{x1}" y="{y1+14}" text-anchor="end" {MONO} font-size="9" fill="var(--muted)">{tmax:.0f} min</text><text x="{x0}" y="{y1+14}" {MONO} font-size="9" fill="var(--muted)">0</text>')
    ly = top + 2 * PH + 14
    leg = [("var(--fg)", "", "book held, h₀ (moved by the feed's fills)"), ("var(--accent)", "", "target, h")]
    if mode == "mpo": leg.append(("#d97706", "4 3", "planned book two periods ahead, h₃"))
    if mode == "mso": leg.append(("var(--mauve)", "", "the four strategy books"))
    leg.append(("var(--rose)", "4 3", "30% limit per name"))
    x = 10
    for col, dash, txt in leg:
        d = f' stroke-dasharray="{dash}"' if dash else ""
        o.append(f'<line x1="{x}" y1="{ly}" x2="{x+22}" y2="{ly}" stroke="{col}" stroke-width="2"{d}/><text x="{x+28}" y="{ly+4}" {SANS} font-size="11" fill="var(--fg)">{txt}</text>')
        x += 40 + len(txt) * 5.6
    o.append(f'<rect x="{x}" y="{ly-6}" width="22" height="12" fill="var(--accent)" fill-opacity=".18"/><text x="{x+28}" y="{ly+4}" {SANS} font-size="11" fill="var(--fg)">shaded: the trade the optimiser wants</text>')
    gaps = ", ".join(f"{s} {100*sum(abs(p[2]-p[1]) for p in by[s])/len(by[s]):.1f}%" for s in syms)
    aria = (f"Live {mode} run, {tmax:.0f} minutes, one panel per name. Each panel shows the book held over time, moved by the feed's fills, "
            f"and the optimiser's target; the shaded band between them is the trade it wants. Mean gap between book and target: {gaps}.")
    return f'<svg viewBox="0 0 {W} {ly+16}" role="img" aria-label="{aria}">' + "".join(o) + "</svg>"

CHARTS.update(live_single=lambda: live_chart("single"), live_mpo=lambda: live_chart("mpo"), live_mso=lambda: live_chart("mso"))
