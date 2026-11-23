/* A tiny stand-in for the q runtime: just the k.h calls qosqp.c makes, so the
 * shim can be exercised from C with no q process. Never ships; tests only. */
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stdio.h>
#define KXVER 3
#include "k.h"

static int sz(int t){ switch(t<0?-t:t){case 0:return sizeof(K);case KB:case KG:case KC:return 1;
  case KH:return 2;case KI:case KE:return 4;case KS:return sizeof(S);default:return 8;} }
K ktn(I t, J n){ K x=calloc(1,sizeof(struct k0)+(n?n:1)*sz(t)); x->t=t; x->n=n; x->r=0; return x; }
static K atom(I t){ K x=calloc(1,sizeof(struct k0)); x->t=t; return x; }
K kj(J j){ K x=atom(-KJ); x->j=j; return x; }
K kf(F f){ K x=atom(-KF); x->f=f; return x; }
S ss(const S s){ return strdup(s); }
K ks(const S s){ K x=atom(-KS); x->s=ss(s); return x; }
K kp(const S s){ J n=strlen(s); K x=ktn(KC,n); memcpy(kC(x),s,n); return x; }
K knk(I n, ...){ va_list a; va_start(a,n); K x=ktn(0,n); for(I i=0;i<n;i++) kK(x)[i]=va_arg(a,K); va_end(a); return x; }
K xD(K k, K v){ K d=ktn(0,2); d->t=99; kK(d)[0]=k; kK(d)[1]=v; return d; }
static char errbuf[256];
K krr(const S s){ strncpy(errbuf,s,255); K x=atom(-128); x->s=errbuf; return x; }
V r0(K x){ (void)x; }
/* test helpers */
K nil(void){ return atom(101); }
K fv(J n, const double* v){ K x=ktn(KF,n); memcpy(kF(x),v,n*8); return x; }
K jvec(J n, const long long* v){ K x=ktn(KJ,n); memcpy(kJ(x),v,n*8); return x; }
K dget(K d, const char* key){ K k=kK(d)[0]; for(J i=0;i<k->n;i++) if(!strcmp(kS(k)[i],key)) return kK(kK(d)[1])[i]; return 0; }
