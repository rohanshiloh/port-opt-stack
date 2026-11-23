"""Lab C2's experiment: four strategies, optimise-then-net against net-then-optimise.
Both are scored on the firm: alpha earned, risk of the net book, and the cost of
the trade the firm actually sends (the net one). Clarabel solves both, so the
comparison is about the formulation, not solver tolerance."""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import *
from validate_cl import solve_clarabel

def run(n=1000, S=4, overlap=0.4, seed=3):
    d = universe(n); g = np.random.default_rng(seed)
    common = g.normal(0, 0.03, n)
    alphas = [overlap * common + np.sqrt(1 - overlap**2) * g.normal(0, 0.03, n) for _ in range(S)]
    caps = np.full(S, 1.0 / S)
    w0s = []
    for s in range(S):                                  # each book: its optimum on yesterday's view
        ds = dict(d); ds["alpha"] = alphas[s] + g.normal(0, 0.02, n); ds["tau"] = 1e30; ds["h0"] = d["h0"]
        x, _ = solve_clarabel(*single(ds)[:5]); w0s.append(np.clip(x[:n], 0, None) / np.clip(x[:n], 0, None).sum())
    Sig = lambda w: w @ (d["Delta"] * w) + (d["X"].T @ w) @ d["F"] @ (d["X"].T @ w)
    cost = lambda t: d["kappa"] @ np.abs(t) + d["eta"] @ (t * t)
    def score(ws):
        w = sum(c * x for c, x in zip(caps, ws)); w0 = sum(c * x for c, x in zip(caps, w0s))
        tnet = w - w0; ts = [c * (x - x0) for c, x, x0 in zip(caps, ws, w0s)]
        a = sum(c * al @ x for c, al, x in zip(caps, alphas, ws)); r = d["lam"] * Sig(w)
        return dict(alpha_bps=1e4 * a, risk_bps=1e4 * r, netCost_bps=1e4 * cost(tnet),
                    grossCost_bps=1e4 * sum(cost(t) for t in ts),
                    netTurnover=float(np.abs(tnet).sum()), grossTurnover=float(sum(np.abs(t).sum() for t in ts)),
                    utility_bps=1e4 * (a - r - cost(tnet)))
    # optimise-then-net: each strategy alone, its own risk, costs and turnover
    sep = []
    for s in range(S):
        ds = dict(d); ds["alpha"] = alphas[s]; ds["h0"] = w0s[s]; ds["eta"] = caps[s] * d["eta"]
        x, _ = solve_clarabel(*single(ds)[:5]); sep.append(x[:n])
    A = score(sep)
    # net-then-optimise: one problem, the firm's risk, costs on the net trade, same firm turnover
    P, q, Am, l, u, ix = multistrat(d, alphas, caps, w0s, [d["hi"]] * S)
    x, _ = solve_clarabel(P, q, Am, l, u)
    B = score([x[s * n:(s + 1) * n] for s in range(S)])
    return dict(n=n, S=S, overlap=overlap, separate=A, joint=B)

if __name__ == "__main__":
    out = [run(overlap=o) for o in (0.0, 0.4, 0.8)]
    for r in out: print(json.dumps(r))
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "multistrat.json"), "w"), indent=1)
