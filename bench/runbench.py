"""Run the benchmarks in the document and write bench/results.jsonl.
OSQP runs through the q shim itself (c/qosqp.c, driven by c/test/bench.c over
the mock runtime); Clarabel runs through its Python binding as the cold-solve
comparison. One process at a time, on a 2-core cloud VM."""
import json, subprocess, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import *
here = os.path.dirname(os.path.abspath(__file__))
out = open(os.path.join(here, "results.jsonl"), "w")
def emit(r): print(json.dumps(r), flush=True); out.write(json.dumps(r) + "\n"); out.flush()
CL = r'''
import sys, time, resource, json
sys.path.insert(0, "%s"); from model import *; from validate_cl import solve_clarabel
n=int(sys.argv[1]); H=int(sys.argv[2]); d=universe(n)
P,q,A,l,u,ix = single(d) if H==1 else mpc(d,H)
r0=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
t=time.time(); x,o=solve_clarabel(P,q,A,l,u); t=time.time()-t
r1=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
print(json.dumps(dict(clarabel_ms=round(1e3*t,1), clarabel_rss_MB=round((r1-r0)/1024,1))))
''' % here
def osqp_run(f, n, rho):
    return json.loads(subprocess.run([os.path.join(here, "..", "c", "test", "qbench"), f, str(n), "50", "40", "1e-5", "0", str(rho)],
                                     capture_output=True, text=True).stdout)
def clarabel_run(n, H):
    return json.loads(subprocess.run([sys.executable, "-c", CL, str(n), str(H)], capture_output=True, text=True).stdout)
for n in [1000, 2000, 5000, 10000]:
    d = universe(n); P, q, A, l, u, ix = single(d); f = f"/tmp/p{n}.bin"; write(f, P, q, A, l, u)
    r = osqp_run(f, n, round(n / 70)); r.update(clarabel_run(n, 1)); r["kind"] = "single"; emit(r)
for H in [2, 4, 8]:
    n = 2000; d = universe(n); P, q, A, l, u, ix = mpc(d, H); f = f"/tmp/m{H}.bin"; write(f, P, q, A, l, u)
    r = osqp_run(f, n, round(n / 70)); r.update(clarabel_run(n, H)); r["kind"] = "mpc"; r["H"] = H; emit(r)
