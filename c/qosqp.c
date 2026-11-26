/* port-opt-stack : qosqp.c — OSQP 1.x for q, through the C API (2:)
 *
 * q holds every solver behind a small integer handle, so one process can keep
 * many problems warm at once (one per strategy, one per horizon, ...).
 * A sparse matrix crosses the boundary as a 5-item general list
 *     (m; n; p; i; x)     rows, cols, column pointers, row indices, values
 * in compressed-sparse-column order, with p and i as longs and x as floats.
 * OSQP is built with OSQP_USE_LONG (c/osqp_configure.h), so OSQPInt is a 64-bit J and the index
 * vectors are passed straight through without a copy. osqp_setup copies the
 * data it keeps, so nothing here points into q memory after a call returns.
 * P must be the UPPER triangle of the quadratic term (OSQP's convention).
 *
 * q side (qp.q):
 *   .qp.setup  [P;q;A;l;u;settings]  -> handle (long)
 *   .qp.solve  [h]                   -> dict: status, iter, obj, x, y, timings
 *   .qp.update [h;q;l;u]             -> 0; pass (::) for "unchanged"
 *   .qp.updmat [h;Px;Ax]             -> 0; same sparsity, new values
 *   .qp.warm   [h;x;y]               -> 0; pass (::) for "unchanged"
 *   .qp.set    [h;settings]          -> 0; the settings OSQP allows after setup
 *   .qp.free   [h]                   -> 0
 *   .qp.ver    [x]                   -> OSQP version string
 */
#include <string.h>
#include "osqp.h"
#define KXVER 3
#include "k.h"

#define NSLOT 256
static OSQPSolver* slot[NSLOT];
static OSQPInt     dimN[NSLOT], dimM[NSLOT], nnzP[NSLOT], nnzA[NSLOT];

/* ── helpers ─────────────────────────────────────────────────────────────── */
static int isnil(K x){ return x->t==101; }                /* (::) */

static K handle(K h, OSQPSolver** s, J* ix){
  if(h->t!=-KJ && h->t!=-KI) return krr("type: handle must be a long");
  J i = h->t==-KJ ? h->j : h->i;
  if(i<0 || i>=NSLOT || !slot[i]) return krr("handle: no such solver");
  *s=slot[i]; *ix=i; return (K)0;
}

/* (m;n;p;i;x) -> OSQPCscMatrix, pointing at the q vectors (no copy) */
static K csc(K x, OSQPCscMatrix* M){
  if(x->t!=0 || x->n!=5) return krr("csc: expected (m;n;p;i;x)");
  K* k=kK(x);
  if(k[0]->t!=-KJ || k[1]->t!=-KJ) return krr("csc: m and n must be long atoms");
  if(k[2]->t!=KJ || k[3]->t!=KJ)   return krr("csc: p and i must be long vectors");
  if(k[4]->t!=KF)                  return krr("csc: x must be a float vector");
  J m=k[0]->j, n=k[1]->j;
  if(k[2]->n!=n+1)                 return krr("csc: count p must be n+1");
  if(k[3]->n!=k[4]->n)             return krr("csc: count i must equal count x");
  if(kJ(k[2])[n]!=k[4]->n)         return krr("csc: last p must equal count x");
  OSQPCscMatrix_set_data(M, m, n, k[4]->n, kF(k[4]), (OSQPInt*)kJ(k[3]), (OSQPInt*)kJ(k[2]));
  return (K)0;
}

static K fvec(K x, J n, const char* who, OSQPFloat** out){
  if(isnil(x)){ *out=OSQP_NULL; return (K)0; }
  if(x->t!=KF) return krr((S)who);
  if(x->n!=n)  return krr("length");
  *out=kF(x); return (K)0;
}

/* settings dictionary: symbol keys, numeric atom values; unknown keys error */
static K settings(K d, OSQPSettings* s){
  if(isnil(d)) return (K)0;
  if(d->t!=99) return krr("settings: expected a dictionary");
  K ks_=kK(d)[0], vs=kK(d)[1];
  if(ks_->t!=KS) return krr("settings: keys must be symbols");
  for(J i=0;i<ks_->n;i++){
    S key=kS(ks_)[i]; F v; K e;
    if(vs->t==0){ e=kK(vs)[i];
      v = e->t==-KF? e->f : e->t==-KJ? (F)e->j : e->t==-KI? (F)e->i : e->t==-KB? (F)e->g : -1e300; }
    else if(vs->t==KF) v=kF(vs)[i];
    else if(vs->t==KJ) v=(F)kJ(vs)[i];
    else return krr("settings: values must be numeric");
    if(v==-1e300) return krr("settings: values must be numeric");
#define SETF(f) if(!strcmp(key,#f)){ s->f=(OSQPFloat)v; continue; }
#define SETI(f) if(!strcmp(key,#f)){ s->f=(OSQPInt)v;   continue; }
    SETF(eps_abs) SETF(eps_rel) SETF(eps_prim_inf) SETF(eps_dual_inf)
    SETF(rho) SETF(sigma) SETF(alpha) SETF(time_limit) SETF(delta)
    SETI(max_iter) SETI(polishing) SETI(warm_starting) SETI(verbose) SETI(scaling)
    SETI(adaptive_rho) SETI(check_termination) SETI(polish_refine_iter) SETI(scaled_termination)
    return krr("settings: unknown key");
  }
  return (K)0;
}

/* ── the API ─────────────────────────────────────────────────────────────── */
K qp_setup(K P, K q, K A, K l, K u, K s){
  OSQPCscMatrix Pm, Am; K e; OSQPFloat *qv=OSQP_NULL,*lv=OSQP_NULL,*uv=OSQP_NULL;
  if((e=csc(P,&Pm))) return e;
  if((e=csc(A,&Am))) return e;
  J n=Pm.n, m=Am.m;
  if(Pm.m!=n)  return krr("setup: P must be n x n");
  if(Am.n!=n)  return krr("setup: A must have n columns");
  if(isnil(q)||isnil(l)||isnil(u)) return krr("setup: q, l, u are required");
  if((e=fvec(q,n,"type: q must be floats",&qv))) return e;
  if((e=fvec(l,m,"type: l must be floats",&lv))) return e;
  if((e=fvec(u,m,"type: u must be floats",&uv))) return e;
  OSQPSettings st; osqp_set_default_settings(&st);
  st.verbose=0;                                    /* q owns the console */
  if((e=settings(s,&st))) return e;
  J i=0; while(i<NSLOT && slot[i]) i++;
  if(i==NSLOT) return krr("setup: too many solvers; .qp.free some");
  OSQPSolver* sv=OSQP_NULL;
  OSQPInt rc=osqp_setup(&sv,&Pm,qv,&Am,lv,uv,m,n,&st);
  if(rc){ if(sv) osqp_cleanup(sv); return krr((S)osqp_error_message(rc)); }
  slot[i]=sv; dimN[i]=n; dimM[i]=m; nnzP[i]=Pm.p[n]; nnzA[i]=Am.p[n];
  return kj(i);
}

K qp_solve(K h){
  OSQPSolver* s=OSQP_NULL; J i=0; K e;
  if((e=handle(h,&s,&i))) return e;
  OSQPInt rc=osqp_solve(s);
  if(rc) return krr((S)osqp_error_message(rc));
  OSQPInfo* f=s->info; OSQPSolution* z=s->solution;
  K x=ktn(KF,dimN[i]); memcpy(kF(x),z->x,dimN[i]*sizeof(F));
  K y=ktn(KF,dimM[i]); memcpy(kF(y),z->y,dimM[i]*sizeof(F));
  K keys=ktn(KS,13);
  const char* nm[]={"status","statusVal","iter","obj","primRes","dualRes",
                    "setupTime","solveTime","runTime","rhoUpdates","rhoEstimate","x","y"};
  for(int j=0;j<13;j++) kS(keys)[j]=ss((S)nm[j]);
  K vals=knk(13, ks(f->status), kj(f->status_val), kj(f->iter), kf(f->obj_val),
             kf(f->prim_res), kf(f->dual_res), kf(f->setup_time), kf(f->solve_time),
             kf(f->run_time), kj(f->rho_updates), kf(f->rho_estimate), x, y);
  return xD(keys,vals);
}

K qp_update(K h, K q, K l, K u){
  OSQPSolver* s=OSQP_NULL; J i=0; K e; OSQPFloat *qv=OSQP_NULL,*lv=OSQP_NULL,*uv=OSQP_NULL;
  if((e=handle(h,&s,&i))) return e;
  if((e=fvec(q,dimN[i],"type: q must be floats",&qv))) return e;
  if((e=fvec(l,dimM[i],"type: l must be floats",&lv))) return e;
  if((e=fvec(u,dimM[i],"type: u must be floats",&uv))) return e;
  OSQPInt rc=osqp_update_data_vec(s,qv,lv,uv);
  return rc? krr("update: l > u somewhere, or bad data") : kj(0);
}

K qp_updmat(K h, K Px, K Ax){
  OSQPSolver* s=OSQP_NULL; J i=0; K e;
  if((e=handle(h,&s,&i))) return e;
  OSQPFloat *pv=OSQP_NULL,*av=OSQP_NULL; OSQPInt np=0,na=0;
  /* whole-vector replacement only: the values must line up with the setup's nonzeros */
  if(!isnil(Px)){
    if(Px->t!=KF)      return krr("type: Px must be floats");
    if(Px->n!=nnzP[i]) return krr("updmat: count Px must equal the nonzeros of P at setup");
    pv=kF(Px); np=Px->n; }
  if(!isnil(Ax)){
    if(Ax->t!=KF)      return krr("type: Ax must be floats");
    if(Ax->n!=nnzA[i]) return krr("updmat: count Ax must equal the nonzeros of A at setup");
    av=kF(Ax); na=Ax->n; }
  OSQPInt rc=osqp_update_data_mat(s,pv,OSQP_NULL,np,av,OSQP_NULL,na);
  return rc? krr("updmat: values must match the setup sparsity (same nnz)") : kj(0);
}

K qp_warm(K h, K x, K y){
  OSQPSolver* s=OSQP_NULL; J i=0; K e; OSQPFloat *xv=OSQP_NULL,*yv=OSQP_NULL;
  if((e=handle(h,&s,&i))) return e;
  if((e=fvec(x,dimN[i],"type: x must be floats",&xv))) return e;
  if((e=fvec(y,dimM[i],"type: y must be floats",&yv))) return e;
  return osqp_warm_start(s,xv,yv)? krr("warm") : kj(0);
}

K qp_set(K h, K d){
  OSQPSolver* s=OSQP_NULL; J i=0; K e;
  if((e=handle(h,&s,&i))) return e;
  OSQPSettings st; memcpy(&st,s->settings,sizeof st);
  if((e=settings(d,&st))) return e;
  return osqp_update_settings(s,&st)? krr("set: that setting cannot change after setup") : kj(0);
}

K qp_free(K h){
  OSQPSolver* s=OSQP_NULL; J i=0; K e;
  if((e=handle(h,&s,&i))) return e;
  osqp_cleanup(s); slot[i]=OSQP_NULL; return kj(0);
}

K qp_ver(K x){ (void)x; return kp((S)osqp_version()); }
