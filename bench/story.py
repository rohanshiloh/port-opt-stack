"""Data for the two small-multiples figures, written to bench/story.json.
  fills: one rebalance, fill by fill. Each fill executes 35% of what is left of
         every name's trade; the problem's h0 and turnover move, and OSQP re-solves warm.
  roll:  the multi-period plan, period by period. Plan H periods, execute the first,
         age the signal one period (alpha * decay), plan again from the new book.
Runs with either OSQP Python API (0.6 'polish' or 1.x 'polishing')."""
import json, os, sys
import numpy as np, scipy.sparse as sp, osqp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import universe, single, mpc

def solver(P, q, A, l, u, n):
    m = osqp.OSQP()
    m.setup(sp.triu(P).tocsc(), q, A.tocsc(), l, u, verbose=False, eps_abs=1e-6, eps_rel=1e-6,
            max_iter=200000, rho=max(0.1, n / 70))
    return m

def fills(n=400, k=10, nfill=4, frac=0.35, show=10):
    d = universe(n, k); P, q, A, l, u, ix = single(d); rT, rO = ix["rT"], k + 1 + 4 * n
    m = solver(P, q, A, l, u, n); r = m.solve()
    w0 = d["h0"].copy(); tgt = r.x[:n].copy(); tau = d["tau"]
    names = np.argsort(-np.abs(tgt - w0))[:show]                 # the names that trade most
    steps = [dict(label="start", h0=w0[names].tolist(), h=tgt[names].tolist(), tau_left=tau, iters=int(r.info.iter))]
    for f in range(nfill):
        dw = frac * (tgt - w0); dw[np.abs(dw) < 1e-9] = 0
        w0 = w0 + dw; tau = max(0.0, tau - np.abs(dw).sum())
        l[rT:rT + n] = w0; u[rT:rT + n] = w0; u[rO] = tau
        m.update(l=l, u=u); r = m.solve(); tgt = r.x[:n].copy()
        steps.append(dict(label=f"fill {f+1}", h0=w0[names].tolist(), h=tgt[names].tolist(), tau_left=tau, iters=int(r.info.iter)))
    return dict(n=n, k=k, names=[int(i) for i in names], steps=steps)

def roll(n=400, k=10, H=4, decay=0.7, periods=4, tau=0.6):
    d = universe(n, k); d["tau"] = tau; out = []          # a budget loose enough that the plan has a shape
    for t in range(periods):
        P, q, A, l, u, ix = mpc(d, H, decay); N1 = ix["N1"]
        r = solver(P, q, A, l, u, n).solve(); x = r.x
        plan = [float(np.abs(x[s*N1+n+k: s*N1+3*n+k]).sum()) for s in range(H)]   # turnover planned per period
        out.append(dict(t=t + 1, plan=plan, alpha=float(d["alpha"] @ x[:n]), iters=int(r.info.iter)))
        d = dict(d); d["h0"] = x[:n].copy(); d["alpha"] = d["alpha"] * decay      # execute period 1; the signal ages
    return dict(n=n, k=k, H=H, decay=decay, tau=tau, steps=out)

if __name__ == "__main__":
    s = dict(fills=fills(), roll=roll())
    json.dump(s, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "story.json"), "w"), indent=1)
    for st in s["fills"]["steps"]: print(st["label"], round(st["tau_left"], 4), st["iters"])
    for st in s["roll"]["steps"]: print(st["t"], [round(v, 4) for v in st["plan"]], round(st["alpha"], 5), st["iters"])
