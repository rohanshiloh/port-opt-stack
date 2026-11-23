/* Benchmark the shim itself: load a problem written by bench/model.py, then
 *   1. setup + cold solve
 *   2. F fills: each moves w0 part-way to the target on 1% of names and spends
 *      the turnover it used; update l/u (the trade rows and the turnover row)
 *      and re-solve warm, the way opt.q does on every batch of execs
 *   3. the first three fills re-solved cold (fresh setup) for comparison
 * usage: bench file n k F eps polish [rho]   -> one JSON line                     */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#define KXVER 3
#include "k.h"
K qp_setup(K,K,K,K,K,K), qp_solve(K), qp_update(K,K,K,K), qp_free(K);
K nil(void), dget(K,const char*);
static double now(void){ struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return t.tv_sec+1e-9*t.tv_nsec; }
static long rssKB(void){ FILE* f=fopen("/proc/self/status","r"); char b[256]; long v=0;   /* current RSS, kB */
  while(fgets(b,sizeof b,f)){ if(!strncmp(b,"VmRSS:",6)){ v=atol(b+6); break; } }
  fclose(f); return v; }
static K rdJ(FILE*f,J n){ K x=ktn(KJ,n); if(fread(kJ(x),8,n,f)!=(size_t)n) exit(2); return x; }
static K rdF(FILE*f,J n){ K x=ktn(KF,n); if(fread(kF(x),8,n,f)!=(size_t)n) exit(2); return x; }
static double RHO=0.1;
static K sett(double eps,int pol){ K k=ktn(KS,5); kS(k)[0]=ss("eps_abs"); kS(k)[1]=ss("eps_rel");
  kS(k)[2]=ss("polishing"); kS(k)[3]=ss("max_iter"); kS(k)[4]=ss("rho"); K v=ktn(KF,5);
  kF(v)[0]=eps; kF(v)[1]=eps; kF(v)[2]=pol; kF(v)[3]=200000; kF(v)[4]=RHO; return xD(k,v); }
static int cmp(const void*a,const void*b){ double x=*(double*)a,y=*(double*)b; return (x>y)-(x<y); }

int main(int c, char** v){
  if(c<7){ fprintf(stderr,"usage: bench file n k F eps polish\n"); return 1; }
  FILE* f=fopen(v[1],"rb"); J hdr[4]; if(fread(hdr,8,4,f)!=4) return 2;
  J N=hdr[0], M=hdr[1], nP=hdr[2], nA=hdr[3]; J n=atoll(v[2]), k=atoll(v[3]); int nF=atoi(v[4]);
  double eps=atof(v[5]); int pol=atoi(v[6]); if(c>7) RHO=atof(v[7]);
  /* read in file order: C leaves argument evaluation order unspecified */
  K Pp=rdJ(f,N+1), Pi=rdJ(f,nP), Px=rdF(f,nP), Ap=rdJ(f,N+1), Ai=rdJ(f,nA), Ax=rdF(f,nA);
  K q=rdF(f,N); K l=rdF(f,M); K u=rdF(f,M); fclose(f);
  K P=knk(5,kj(N),kj(N),Pp,Pi,Px), A=knk(5,kj(M),kj(N),Ap,Ai,Ax);
  long rss0=rssKB();
  double t0=now(); K h=qp_setup(P,q,A,l,u,sett(eps,pol)); double tSetup=now()-t0;
  if(h->t==-128){ printf("setup error %s\n",h->s); return 3; }
  t0=now(); K r=qp_solve(h); double tCold=now()-t0; J itCold=dget(r,"iter")->j;
  long rss1=rssKB();
  const char* st=dget(r,"status")->s; double* x=kF(dget(r,"x"));
  J rT=k, rO=k+1+4*n;
  double* w0=kF(l)+rT; double* tgt=malloc(n*8); memcpy(tgt,x,n*8);
  srand(11); double* wt=malloc(nF*8); double* wc=malloc(nF*8); J itw=0, itc=0; int coldN=nF<3?nF:3;
  K l2=ktn(KF,M), u2=ktn(KF,M); memcpy(kF(l2),kF(l),M*8); memcpy(kF(u2),kF(u),M*8);
  for(int e=0;e<nF;e++){
    double used=0; J m=n/100>1? n/100:1;
    for(J j=0;j<m;j++){ J a=rand()%n; double d=0.25*(tgt[a]-kF(l2)[rT+a]);
      kF(l2)[rT+a]+=d; kF(u2)[rT+a]+=d; used+=fabs(d); }
    kF(u2)[rO]=fmax(0,kF(u2)[rO]-used);              /* spend the turnover the fills used */
    t0=now(); qp_update(h,nil(),l2,u2); K rr=qp_solve(h); wt[e]=now()-t0; itw+=dget(rr,"iter")->j;
    memcpy(tgt,kF(dget(rr,"x")),n*8);
    if(e<coldN){ t0=now(); K h2=qp_setup(P,q,A,l2,u2,sett(eps,pol)); K r2=qp_solve(h2); wc[e]=now()-t0;
      itc+=dget(r2,"iter")->j; qp_free(h2); }
  }
  qsort(wt,nF,8,cmp); qsort(wc,coldN,8,cmp);
  (void)w0;
  printf("{\"rho\":%g,\"n\":%lld,\"k\":%lld,\"vars\":%lld,\"rows\":%lld,\"nnzA\":%lld,\"eps\":%g,\"polish\":%d,"
         "\"status\":\"%s\",\"setup_ms\":%.1f,\"cold_ms\":%.1f,\"cold_iter\":%lld,"
         "\"warm_med_ms\":%.2f,\"warm_p90_ms\":%.2f,\"warm_avg_iter\":%.1f,"
         "\"recold_med_ms\":%.1f,\"recold_avg_iter\":%.1f,\"rss_solver_MB\":%.1f}\n",
         RHO,n,k,N,M,nA,eps,pol,st,1e3*tSetup,1e3*tCold,itCold,
         1e3*wt[nF/2],1e3*wt[(int)(0.9*nF)],(double)itw/nF,1e3*wc[coldN/2],(double)itc/coldN,(rss1-rss0)/1024.0);
  return 0;
}
