"""Lab C3: the same problem through Cvxportfolio and through port-opt-stack's builder.
Cvxportfolio 1.5.0, all data user-provided (market_data=None), so its policy is
exactly the problem written below and nothing is estimated from history.

  ours                                     Cvxportfolio
  -alpha'w                                 ReturnsForecast(r_hat=alpha)
  lambda (w'Dw + y'Cy), y = E'w            lambda * FactorModelCovariance(F=E, Sigma_F=C, d=D)
  kappa'|w - w0|                           TransactionCost(a=kappa, b=None)
  1'w = 1                                  NoCash()
  0 <= w <= hi                             LongOnly(), MaxWeights(hi)
  1'|w - w0| <= tau                        TurnoverLimit(tau/2)    (theirs is half the l1 norm)
  H periods, alpha * decay^t               MultiPeriodOptimization, one objective per step
Impact is left out of both (eta = 0): Cvxportfolio's impact term is a 3/2 power
of the trade scaled by volatility and volume, ours is quadratic, and the point
here is the formulation, not the cost model.
usage: python3 bench/cvxp_check.py [n] [k]"""
import os, sys, json
import numpy as np, pandas as pd, scipy.sparse as sp, osqp
import cvxportfolio as cvx
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import universe, single, mpc

def ours(d, H=1, decay=0.7):
    P, q, A, l, u, ix = single(d) if H == 1 else mpc(d, H, decay)
    m = osqp.OSQP(); m.setup(sp.triu(P).tocsc(), q, A.tocsc(), l, u, verbose=False,
                             eps_abs=1e-8, eps_rel=1e-8, max_iter=400000)
    r = m.solve(); n = len(d["alpha"])
    return r.x[:n] - d["h0"], r.info.status, r.info.iter          # first-period trade

def theirs(d, H=1, decay=0.7, V=1e8):
    n = len(d["alpha"]); names = [f"A{i:04d}" for i in range(n)]
    s = lambda v: pd.Series(v, index=names)
    risk = cvx.FactorModelCovariance(F=pd.DataFrame(d["X"].T, columns=names), Sigma_F=pd.DataFrame(d["F"]), d=s(d["Delta"]))
    tc = cvx.TransactionCost(a=s(d["kappa"]), b=None)
    cons = [cvx.NoCash(), cvx.LongOnly(), cvx.MaxWeights(s(d["hi"])), cvx.TurnoverLimit(d["tau"] / 2)]
    obj = lambda t: cvx.ReturnsForecast(r_hat=s(d["alpha"] * decay ** t)) - d["lam"] * risk - tc
    if H == 1:
        pol = cvx.SinglePeriodOptimization(obj(0), cons, include_cash_return=False, solver="CLARABEL")
    else:
        pol = cvx.MultiPeriodOptimization([obj(t) for t in range(H)], [cons] * H,
                                          include_cash_return=False, planning_horizon=H, solver="CLARABEL")
    h = pd.Series(np.r_[d["h0"] * V, 0.0], index=names + ["USDOLLAR"])
    u, t, _ = pol.execute(h, market_data=None, t=pd.Timestamp("2026-11-20"))
    return u.values[:n] / V                                       # trade, in weights

def compare(n=300, k=10, H=1):
    d = universe(n, k); d["eta"] = np.zeros(n)
    zo, st, it = ours(d, H); zc = theirs(d, H)
    err = np.abs(zo - zc).max() * n                               # in average weights
    return dict(n=n, k=k, H=H, osqp_status=st, osqp_iter=int(it), max_trade_diff_avg_weights=float(err),
                turnover_ours=float(np.abs(zo).sum()), turnover_cvxportfolio=float(np.abs(zc).sum()),
                names_traded_ours=int((np.abs(zo) > 1e-6).sum()), names_traded_cvxportfolio=int((np.abs(zc) > 1e-6).sum()))

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300; k = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    out = [compare(n, k, H) for H in (1, 2, 4)]
    for r in out: print(json.dumps(r))
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cvxp_check.json"), "w"), indent=1)
