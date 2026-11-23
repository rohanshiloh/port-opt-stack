/* Exercise every qosqp.c entry point through the mock runtime. */
#include <stdio.h>
#include <math.h>
#include <string.h>
#define KXVER 3
#include "k.h"
K qp_setup(K,K,K,K,K,K), qp_solve(K), qp_update(K,K,K,K), qp_updmat(K,K,K),
  qp_warm(K,K,K), qp_set(K,K), qp_free(K), qp_ver(K);
K nil(void), fv(J,const double*), jvec(J,const long long*), dget(K,const char*);
static int fails=0;
#define CHECK(c,msg) do{ if(c) printf("ok   %s\n",msg); else { printf("FAIL %s\n",msg); fails++; } }while(0)
static int iserr(K x){ return x->t==-128; }
static K mat(J m,J n,J nz,const long long*p,const long long*i,const double*x){
  return knk(5,kj(m),kj(n),jvec(n+1,p),jvec(nz,i),fv(nz,x)); }
static K sdict(void){ K k=ktn(KS,3); kS(k)[0]=ss("eps_abs"); kS(k)[1]=ss("eps_rel"); kS(k)[2]=ss("polishing");
  double v[]={1e-9,1e-9,1}; return xD(k,fv(3,v)); }

int main(void){
  printf("osqp %s\n", kC(qp_ver(nil())));
  /* OSQP's own demo: min ½x'Px+q'x  s.t. l<=Ax<=u ; answer x=(0.3,0.7) */
  long long Pp[]={0,1,3}, Pi[]={0,0,1}; double Px[]={4,1,2};
  long long Ap[]={0,2,4}, Ai[]={0,1,0,2}; double Ax[]={1,1,1,1};
  double q[]={1,1}, l[]={1,0,0}, u[]={1,0.7,0.7};
  K P=mat(2,2,3,Pp,Pi,Px), A=mat(3,2,4,Ap,Ai,Ax);
  K h=qp_setup(P,fv(2,q),A,fv(3,l),fv(3,u),sdict());
  CHECK(!iserr(h) && h->j==0, "setup returns handle 0");
  K r=qp_solve(h); K x=dget(r,"x");
  CHECK(!strcmp(dget(r,"status")->s,"solved"), "status solved");
  CHECK(fabs(kF(x)[0]-0.3)<1e-6 && fabs(kF(x)[1]-0.7)<1e-6, "x = (0.3, 0.7)");
  CHECK(fabs(dget(r,"obj")->f-1.88)<1e-6, "objective 1.88");
  CHECK(dget(r,"y")->n==3, "y has one multiplier per constraint");

  /* new q, warm: min 2x0^2+x0x1+x1^2 + 2x0 + 0x1 with x0+x1=1, box .7 */
  double q2[]={2,0};
  CHECK(!iserr(qp_update(h,fv(2,q2),nil(),nil())), "update q only, l u unchanged");
  r=qp_solve(h); x=dget(r,"x");
  /* by hand: x1=1-x0, f=2x0^2+x0(1-x0)+(1-x0)^2+2x0 = 2x0^2+x0+1 -> x0=-1/4 clipped to [0,.7] -> 0 ; x1=1 > .7 -> x0=.3 */
  CHECK(fabs(kF(x)[0]-0.3)<1e-6 && fabs(kF(x)[1]-0.7)<1e-6, "re-solve after q update respects the box");
  double u3[]={1,0.7,1.0};
  qp_update(h,nil(),nil(),fv(3,u3));
  r=qp_solve(h); x=dget(r,"x");
  CHECK(fabs(kF(x)[0])<1e-6 && fabs(kF(x)[1]-1)<1e-6, "loosen the box: x = (0, 1)");
  CHECK(dget(r,"iter")->j < 200, "warm re-solve converges quickly");

  /* matrix values, same sparsity: P doubled */
  double Px2[]={8,2,4};
  CHECK(!iserr(qp_updmat(h,fv(3,Px2),nil())), "updmat P, same nnz");
  r=qp_solve(h); CHECK(!strcmp(dget(r,"status")->s,"solved"), "solves after updmat");
  double badP[]={1,2};
  CHECK(iserr(qp_updmat(h,fv(2,badP),nil())), "updmat with the wrong number of values is an error");

  /* warm start from a given point */
  double x0[]={0.5,0.5};
  CHECK(!iserr(qp_warm(h,fv(2,x0),nil())), "warm start x only");
  /* settings after setup */
  K k=ktn(KS,1); kS(k)[0]=ss("max_iter"); double mi[]={4000};
  CHECK(!iserr(qp_set(h,xD(k,fv(1,mi)))), "set max_iter after setup");

  /* errors come back as q errors, never a crash */
  K k2=ktn(KS,1); kS(k2)[0]=ss("nonsense"); double z[]={1};
  CHECK(iserr(qp_setup(P,fv(2,q),A,fv(3,l),fv(3,u),xD(k2,fv(1,z)))), "unknown setting is an error");
  CHECK(iserr(qp_update(h,fv(1,q),nil(),nil())), "wrong length q is an error");
  CHECK(iserr(qp_solve(kj(99))), "unknown handle is an error");
  double lbad[]={2,0,0};  /* l > u in row 0 */
  CHECK(iserr(qp_update(h,nil(),fv(3,lbad),nil())), "l > u is an error");
  K badA=knk(5,kj(3),kj(2),jvec(3,Ap),jvec(4,Ai),fv(3,Ax));
  CHECK(iserr(qp_setup(P,fv(2,q),badA,fv(3,l),fv(3,u),nil())), "malformed csc is an error");

  /* two solvers side by side, then free and reuse */
  K h2=qp_setup(P,fv(2,q),A,fv(3,l),fv(3,u),nil());
  CHECK(h2->j==1, "second solver gets handle 1");
  qp_free(h);
  CHECK(iserr(qp_solve(h)), "freed handle is an error");
  K h3=qp_setup(P,fv(2,q),A,fv(3,l),fv(3,u),nil());
  CHECK(h3->j==0, "freed slot is reused");
  r=qp_solve(h2); CHECK(!strcmp(dget(r,"status")->s,"solved"), "the other solver is untouched");
  printf(fails? "\n%d FAILED\n" : "\nall passed\n", fails);
  return fails!=0;
}
