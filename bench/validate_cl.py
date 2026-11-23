import numpy as np, scipy.sparse as sp, clarabel
def solve_clarabel(P,q,A,l,u):
    # l<=Ax<=u  ->  [A;-A]x <= [u;-l], equality rows where l==u
    eq=np.isclose(l,u); fin_u=(u<1e29)&~eq; fin_l=(l>-1e29)&~eq
    Aeq=A[eq]; Au=A[fin_u]; Al=-A[fin_l]
    G=sp.vstack([Aeq,Au,Al]).tocsc(); h=np.r_[u[eq],u[fin_u],-l[fin_l]]
    cones=[clarabel.ZeroConeT(int(eq.sum())), clarabel.NonnegativeConeT(int(fin_u.sum()+fin_l.sum()))]
    s=clarabel.DefaultSettings(); s.verbose=False
    r=clarabel.DefaultSolver(sp.triu(P).tocsc(),q,G,h,cones,s).solve(); return np.array(r.x), r.obj_val
