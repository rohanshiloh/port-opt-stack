"""Python mirror of port.q's problem builders (Barra notation: X F Delta h0, as port.q), used to validate the formulation
against an independent solver and to write problems for the C benchmark.
Every block, offset and sign here matches port.q line for line."""
import numpy as np
import scipy.sparse as sp

INF = 1e30

def universe(n, k=50, seed=7):
    """A synthetic factor-model universe. Annual units: alpha and variances per year."""
    g = np.random.default_rng(seed)
    E = g.normal(0, 1, (n, k)) * 0.3
    E[:, 0] = g.normal(1.0, 0.3, n)                      # market beta
    fv = np.r_[0.18, g.uniform(0.02, 0.08, k - 1)]       # factor vols
    L = g.normal(0, 0.2, (k, k)); R = np.eye(k) + 0.1 * (L @ L.T)
    d = 1 / np.sqrt(np.diag(R)); R = R * d[:, None] * d[None, :]
    C = R * fv[:, None] * fv[None, :]
    D = g.uniform(0.15, 0.45, n) ** 2                    # specific variance
    alpha = g.normal(0, 0.03, n)
    w0 = np.full(n, 1.0 / n) * g.uniform(0.5, 1.5, n); w0 /= w0.sum()
    hi = np.full(n, max(0.02, 15.0 / n)); lo = np.zeros(n)
    kappa = g.uniform(2, 8, n) * 1e-4                    # half-spread + fee, per unit weight
    eta = g.uniform(0.5, 2.0, n) * 0.5                   # quadratic impact
    return dict(alpha=alpha, X=E, F=C, Delta=D, h0=w0, lo=lo, hi=hi, kappa=kappa, eta=eta,
                lam=2.0, tau=0.10, tmax=np.full(n, INF), fl=np.full(k, -INF), fu=np.full(k, INF), budget=1.0)

STYLES = ["market", "size", "value", "momentum", "volatility"]

def _std(cw, x):
    x = x - cw @ x
    return np.clip(x / x.std(), -5, 5)

def mfm(n, n_ind=10, seed=7):
    """Named-factor universe. Mirrors .po.mfm (same recipe, numpy's generator):
    five styles standardised the vendor way, then n_ind industries, 5% of names split 65/35."""
    g = np.random.default_rng(seed)
    z = g.normal(0, 1, (6, n))
    cap = np.exp(23 + 1.2 * z[0]); cw = cap / cap.sum()
    size = _std(cw, np.log(cap))
    val = _std(cw, -0.2 * size + np.sqrt(0.96) * z[1])
    mom = _std(cw, z[2])
    vol = _std(cw, -0.4 * size + np.sqrt(0.84) * z[3])
    beta = np.clip(1 + 0.15 * vol + 0.2 * z[4], 0.3, 2.0)
    ind = g.integers(0, n_ind, n)
    IE = (ind[:, None] == np.arange(n_ind)[None, :]).astype(float)
    cg = np.where(g.uniform(size=n) < 0.05)[0]
    j2 = (ind[cg] + 1 + g.integers(0, n_ind - 1, len(cg))) % n_ind
    IE[cg] = 0; IE[cg, ind[cg]] = 0.65; IE[cg, j2] = 0.35
    E = np.column_stack([beta, size, val, mom, vol, IE]); k = 5 + n_ind
    RS = np.array([[1, -.1, 0, -.1, .5], [-.1, 1, .2, 0, -.3], [0, .2, 1, -.3, -.1], [-.1, 0, -.3, 1, 0], [.5, -.3, -.1, 0, 1]])
    R = np.zeros((k, k)); R[:5, :5] = RS; R[5:, 5:] = 0.25 + 0.75 * np.eye(n_ind)
    fv = np.r_[0.16, 0.03, 0.025, 0.04, 0.035, 0.04 + 0.04 * g.uniform(size=n_ind)]
    C = R * fv[:, None] * fv[None, :]
    sv = np.clip(0.22 * np.exp(0.25 * vol - 0.15 * size) * np.exp(0.2 * z[5]), 0.08, 0.8)
    d = universe(n, k, seed)
    d.update(X=E, F=C, Delta=sv ** 2, fl=np.full(k, -INF), fu=np.full(k, INF))
    d.update(fnames=STYLES + [f"ind{j}" for j in range(n_ind)], cap=cap, bench=cw, ind=ind)
    return d

def blocks(d, co, ro, first=True):
    """One period's triplets. co/ro: column and row offsets. Mirrors .po.blocks."""
    n = len(d["alpha"]); k = len(d["F"])
    cy, cb, cs = co + n, co + n + k, co + 2 * n + k
    rF, rT, rB, rX, rS, rO, rY = ro, ro + k, ro + k + n, ro + k + n + 1, ro + k + 1 + 2 * n, ro + k + 1 + 4 * n, ro + k + 2 + 4 * n
    I, J, V = [], [], []
    def add(i, j, v): I.append(np.asarray(i)); J.append(np.asarray(j)); V.append(np.asarray(v, float))
    a = np.repeat(np.arange(n), k); f = np.tile(np.arange(k), n)
    add(rF + f, co + a, d["X"].ravel())                        # E'w
    add(rF + np.arange(k), cy + np.arange(k), -np.ones(k))     # - y
    add(rT + np.arange(n), co + np.arange(n), np.ones(n))      # w - b + s = w0
    add(rT + np.arange(n), cb + np.arange(n), -np.ones(n))
    add(rT + np.arange(n), cs + np.arange(n), np.ones(n))
    add(np.full(n, rB), co + np.arange(n), np.ones(n))         # 1'w = budget
    add(rX + np.arange(n), co + np.arange(n), np.ones(n))      # lo <= w <= hi
    add(rS + np.arange(2 * n), cb + np.arange(2 * n), np.ones(2 * n))   # 0 <= b,s <= tmax
    add(np.full(2 * n, rO), cb + np.arange(2 * n), np.ones(2 * n))      # 1'(b+s) <= tau
    add(rY + np.arange(k), cy + np.arange(k), np.ones(k))      # fl <= y <= fu
    lam = d["lam"]
    PI, PJ, PV = [co + np.arange(n)], [co + np.arange(n)], [2 * lam * d["Delta"]]
    fg = np.array([(x, y) for x in range(k) for y in range(k) if x <= y])
    PI.append(cy + fg[:, 0]); PJ.append(cy + fg[:, 1]); PV.append(2 * lam * d["F"][fg[:, 0], fg[:, 1]])
    PI.append(cb + np.arange(2 * n)); PJ.append(cb + np.arange(2 * n)); PV.append(2 * np.r_[d["eta"], d["eta"]])
    q = np.r_[-d["alpha"], np.zeros(k), d["kappa"], d["kappa"]]
    w0 = d["h0"] if first else np.zeros(n)
    l = np.r_[np.zeros(k), w0, d["budget"], d["lo"], np.zeros(2 * n), 0.0, d["fl"]]
    u = np.r_[np.zeros(k), w0, d["budget"], d["hi"], np.r_[d["tmax"], d["tmax"]], d["tau"], d["fu"]]
    return (np.concatenate(I), np.concatenate(J), np.concatenate(V),
            np.concatenate(PI), np.concatenate(PJ), np.concatenate(PV), q, l, u,
            dict(n=n, k=k, N=3 * n + k, M=2 + 2 * k + 4 * n, rT=rT))

def single(d):
    I, J, V, PI, PJ, PV, q, l, u, ix = blocks(d, 0, 0)
    N, M = ix["N"], ix["M"]
    A = sp.csc_matrix((V, (I, J)), shape=(M, N)); P = sp.csc_matrix((PV, (PI, PJ)), shape=(N, N))
    return P, q, A, l, u, ix

def mpc(d, H, decay=0.7, gamma=1.0):
    """H stacked periods; alpha decays by `decay` per period; only period 1 sees w0.
    Mirrors .po.mpo: period t's trade rows also carry -w_{t-1}."""
    n = len(d["alpha"]); k = len(d["F"]); N1, M1 = 3 * n + k, 2 + 2 * k + 4 * n
    parts = []
    for t in range(H):
        dt = dict(d); dt["alpha"] = d["alpha"] * decay ** t * gamma ** t
        dt["kappa"] = d["kappa"] * gamma ** t; dt["eta"] = d["eta"] * gamma ** t
        dt["lam"] = d["lam"] * gamma ** t
        parts.append(blocks(dt, t * N1, t * M1, first=(t == 0)))
    I = [p[0] for p in parts]; J = [p[1] for p in parts]; V = [p[2] for p in parts]
    for t in range(1, H):                                      # - w_{t-1} on period t's trade rows
        rT = parts[t][9]["rT"]
        I.append(rT + np.arange(n)); J.append((t - 1) * N1 + np.arange(n)); V.append(-np.ones(n))
    A = sp.csc_matrix((np.concatenate(V), (np.concatenate(I), np.concatenate(J))), shape=(H * M1, H * N1))
    P = sp.csc_matrix((np.concatenate([p[5] for p in parts]),
                       (np.concatenate([p[3] for p in parts]), np.concatenate([p[4] for p in parts]))), shape=(H * N1, H * N1))
    q = np.concatenate([p[6] for p in parts]); l = np.concatenate([p[7] for p in parts]); u = np.concatenate([p[8] for p in parts])
    return P, q, A, l, u, dict(n=n, k=k, N1=N1, M1=M1, H=H, rT=parts[0][9]["rT"])

def multistrat(d, alphas, caps, w0s, his):
    """S strategies, one net book. x = (w_1..w_S, w, y, b, s).
    Rows: per strategy budget + box; w - sum c_s w_s = 0; then the firm block
    (factor, trade, firm box, trade bounds, turnover, factor bounds) on w.
    Costs and risk sit on the NET book only: an internal cross is free."""
    n = len(d["alpha"]); k = len(d["F"]); S = len(alphas)
    co = S * n                                                 # the firm block starts after the strategies
    fd = dict(d); fd["alpha"] = np.zeros(n); fd["budget"] = 1.0
    fd["lo"] = np.zeros(n); fd["hi"] = np.full(n, 1.0)         # firm box: long-only net
    I, J, V, PI, PJ, PV, q, l, u, ix = blocks(fd, co, 0)
    M1 = ix["M"]; I, J, V = [I], [J], [V]; ql = [np.zeros(0)]
    L, U = [l], [u]
    r = M1
    qs = []
    for s_ in range(S):
        c = s_ * n
        I.append(np.full(n, r)); J.append(c + np.arange(n)); V.append(np.ones(n)); L.append([1.0]); U.append([1.0]); r += 1
        I.append(r + np.arange(n)); J.append(c + np.arange(n)); V.append(np.ones(n)); L.append(np.zeros(n)); U.append(his[s_]); r += n
        qs.append(-caps[s_] * alphas[s_])
    # net definition: w - sum c_s w_s = 0
    I.append(r + np.arange(n)); J.append(co + np.arange(n)); V.append(np.ones(n))
    for s_ in range(S):
        I.append(r + np.arange(n)); J.append(s_ * n + np.arange(n)); V.append(-caps[s_] * np.ones(n))
    L.append(np.zeros(n)); U.append(np.zeros(n)); r += n
    N = co + ix["N"]
    A = sp.csc_matrix((np.concatenate(V), (np.concatenate(I), np.concatenate(J))), shape=(r, N))
    P = sp.csc_matrix((PV, (PI, PJ)), shape=(N, N))
    qq = np.r_[np.concatenate(qs), q]
    w0 = sum(c * w for c, w in zip(caps, w0s)); l = np.concatenate([np.atleast_1d(x) for x in L]); u = np.concatenate([np.atleast_1d(x) for x in U])
    l[ix["rT"]:ix["rT"] + n] = w0; u[ix["rT"]:ix["rT"] + n] = w0
    return P, qq, A, l, u, dict(n=n, k=k, S=S, co=co, rT=ix["rT"])

def write(path, P, q, A, l, u):
    """Binary layout read by bench.c: n m nnzP nnzA, then P(p,i,x), A(p,i,x), q, l, u."""
    P = sp.triu(P).tocsc(); P.sort_indices(); A = A.tocsc(); A.sort_indices()
    n, m = P.shape[0], A.shape[0]
    with open(path, "wb") as f:
        np.array([n, m, P.nnz, A.nnz], np.int64).tofile(f)
        for M in (P, A):
            M.indptr.astype(np.int64).tofile(f); M.indices.astype(np.int64).tofile(f); M.data.astype(np.float64).tofile(f)
        for v in (q, l, u): np.asarray(v, np.float64).tofile(f)
