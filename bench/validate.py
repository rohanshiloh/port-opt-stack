import numpy as np, scipy.sparse as sp, osqp, clarabel, time
from model import *
def solve_osqp(P,q,A,l,u,**kw):
    m=osqp.OSQP(); m.setup(sp.triu(P).tocsc(),q,A.tocsc(),l,u,verbose=False,**kw); r=m.solve(); return r
def solve_clarabel(P,q,A,l,u):
    # l<=Ax<=u  ->  [A;-A]x <= [u;-l], equality rows where l==u
    eq=np.isclose(l,u); fin_u=(u<1e29)&~eq; fin_l=(l>-1e29)&~eq
    Aeq=A[eq]; Au=A[fin_u]; Al=-A[fin_l]
    G=sp.vstack([Aeq,Au,Al]).tocsc(); h=np.r_[u[eq],u[fin_u],-l[fin_l]]
    cones=[clarabel.ZeroConeT(int(eq.sum())), clarabel.NonnegativeConeT(int(fin_u.sum()+fin_l.sum()))]
    s=clarabel.DefaultSettings(); s.verbose=False
    r=clarabel.DefaultSolver(sp.triu(P).tocsc(),q,G,h,cones,s).solve(); return np.array(r.x), r.obj_val
d=universe(800)
P,q,A,l,u,ix=single(d); n,k=ix["n"],ix["k"]
r=solve_osqp(P,q,A,l,u,eps_abs=1e-7,eps_rel=1e-7,max_iter=200000,polishing=True)
xc,oc=solve_clarabel(P,q,A,l,u)
x=r.x; w,y,b,s=x[:n],x[n:n+k],x[n+k:2*n+k],x[2*n+k:]
print("osqp",r.info.status,"iter",r.info.iter,"obj",r.info.obj_val,"| clarabel obj",oc)
print("max|w_osqp-w_clarabel|",np.abs(w-xc[:n]).max())
print("budget",w.sum(),"min w",w.min(),"max w",w.max(),"hi",d["hi"][0])
print("xp == X'h :",np.abs(y-d["X"].T@w).max())
print("h-h0 == b-s:",np.abs((w-d["h0"])-(b-s)).max()," max b*s",(b*s).max())
print("turnover",(b+s).sum(),"tau",d["tau"], " names held",(w>1e-6).sum())
# objective re-computed by hand from the economics
risk=d["lam"]*(w@(d["Delta"]*w)+y@d["F"]@y); cost=d["kappa"]@(b+s)+d["eta"]@(b*b+s*s)
print("hand obj", -d["alpha"]@w+risk+cost, " vs osqp", r.info.obj_val)
# H=1 MPO and S=1 MSO reduce to the single-period problem
P1,q1,A1,l1,u1,_=mpc(d,1); r1=solve_osqp(P1,q1,A1,l1,u1,eps_abs=1e-7,eps_rel=1e-7,max_iter=200000)
print("mpc H=1 obj",r1.info.obj_val)
P2,q2,A2,l2,u2,ix2=multistrat(d,[d["alpha"]],[1.0],[d["h0"]],[d["hi"]]); r2=solve_osqp(P2,q2,A2,l2,u2,eps_abs=1e-7,eps_rel=1e-7,max_iter=200000)
print("multistrat S=1 obj",r2.info.obj_val, "net w diff", np.abs(r2.x[ix2["co"]:ix2["co"]+n]-w).max())
# MPO H=4: first period vs single period (should trade less, alpha decays)
P4,q4,A4,l4,u4,ix4=mpc(d,4); r4=solve_osqp(P4,q4,A4,l4,u4,eps_abs=1e-7,eps_rel=1e-7,max_iter=200000)
x4=r4.x; N1=ix4["N1"]
for t in range(4):
    wt=x4[t*N1:t*N1+n]; bt=x4[t*N1+n+k:t*N1+2*n+k]; st=x4[t*N1+2*n+k:t*N1+3*n+k]
    print(f" mpc t={t+1} turnover {(bt+st).sum():.4f} alpha'w {d['alpha']@wt:.5f}")
xm,om=solve_clarabel(P4,q4,A4,l4,u4); print("mpc H=4 osqp obj",r4.info.obj_val," clarabel",om)
