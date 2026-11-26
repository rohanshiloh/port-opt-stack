/ port-opt-stack : write optimiser diagnostics to optData.txt
/ usage, in the OPT tab:   \l dump.q      then   optDump[]
/ (or in any q session started from the repo root: it loads qp.q and port.q itself)
/ Each query is trapped, so one failure prints its error and the rest still run.
/ First the live optimiser (if opt.q is loaded here): its inputs, its solve log,
/ its target. Then every lab, on fresh solver handles so the live one is never
/ touched. Then checks on the other processes over handles. It takes about a
/ minute; fills that arrive meanwhile queue and are applied after it returns.
/ Names made here start with dmp, so nothing of opt.q's is overwritten.

if[not `po in key `; system"l qp.q"; system"l port.q"];

/ ── helpers ─────────────────────────────────────────────────────────────
/ a query on another process by port, over a short-lived handle
rq:{[port;qry] h:hopen port; r:@[h;qry;{`$"remote error: ",x}]; hclose h; r };
/ percentiles: pct[v;0.9] or pct[v;0 .5 .9]
pct:{[v;p] s:asc v; s floor p*count[s]-1 };
/ fills in the RDB, for comparison with nFill
rdbFills:{ rq[5011;"count select from execs where execType=\"F\""] };
/ one fill in Lab B1: 1% of names move a quarter of the way to target, then a warm re-solve
/ state: (problem; handle; target; ms; iterations; status; turnover left)
dmpFill:{[n;st;e] b:st 0; hs:st 1; tgt:st 2;
  a:neg[1|n div 100]?n;
  dh:@[n#0f;a;:;0.25*(tgt a)-(b`l) b[`rT]+a];
  b:.po.fill[b;dh]; .qp.update[hs;::;b`l;b`u];
  t0:.z.p; r:.qp.solve hs; ms:1e-6*`long$.z.p-t0;
  (b; hs; n#r`x; ms; r`iter; r`status; (b`u) b`rO) };
/ one cold solve on its own handle, freed afterwards
dmpCold:{[b;s] hs:.po.setup[b;s]; t0:.z.p; r:.qp.solve hs; ms:1e-6*`long$.z.p-t0; .qp.free hs;
  `rho`iter`ms`status`obj!(s`rho; r`iter; ms; r`status; r`obj) };
/ a cold solve of a fresh universe of n names
dmpSize:{[n] d:.po.universe[n;50;7]; b:.po.single d; (`n`vars`rows`nnzA!(n;b`N;b`M;count b[`A;4])),dmpCold[b;.qp.S n] };
/ one tolerance in Lab D2: (eps; iterations; weights)
dmpEps:{[b;e] hs:.po.setup[b;(.qp.S b`n),`eps_abs`eps_rel!(e;e)]; r:.qp.solve hs; .qp.free hs; (e; r`iter; (b`n)#r`x) };

optQueries:(
  ".z.P";
  "(.z.K;.z.k;.z.o)";
  ".qp.ver[::]";
  "1_string .qp.lib";
  ".qp.S 2000";
  / ── the live optimiser (errors here just mean opt.q is not loaded in this process)
  "`uni`NAV`nFill`rdbFills`timerMs`rebal!(uni;NAV;nFill;rdbFills[];system\"t\";REBAL)";
  "count solves";
  "-10#solves";
  "select n:count i, medMs:med totalMs, p90Ms:pct[totalMs;0.9], maxMs:max totalMs, avgIter:avg iter, maxIter:max iter, minTauLeft:min turnoverLeft by status from solves";
  "select n:count i, p50Ms:pct[totalMs;0.5], p90Ms:pct[totalMs;0.9], p99Ms:pct[totalMs;0.99], avgIter:avg iter, retries:sum retried, notSolved:sum not status=`solved, lastFills:last nfills by 0D00:01 xbar time from solves";
  "select n:count i by iterBucket:100*iter div 100 from solves";
  "pct[solves`totalMs;0 .1 .25 .5 .75 .9 .99 1]";
  / ── solve health: retries, both attempts, residuals against OSQP's own thresholds, adaptive rho
  "select n:count i, firstFailed:sum retried, retrySolved:sum retried and status=`solved, avgMs1:avg ms1, avgMs2:avg ms2 by status1 from solves";
  "select from solves where retried";
  "select n:count i, maxPrimRatio:max primRes%epsPrim, maxDualRatio:max dualRes%epsDual, over1:sum (primRes>epsPrim) or dualRes>epsDual by status from solves";
  "select rhoUpdates:sum rhoUpdates, solvesWithUpdate:sum rhoUpdates>0, msWithUpdate:avg totalMs where rhoUpdates>0, msWithout:avg totalMs where rhoUpdates=0, lastRhoEstimate:last rhoEstimate from solves";
  "select n:count i, avgMs:avg totalMs, avgIter:avg iter by rhoUpdates from solves";
  "count widen";
  "select n:count i, avgBefore:avg tauLeftBefore, avgAfter:avg tauAfter, maxAfter:max tauAfter, atReset:sum windowReset from widen";
  "select n:count i, maxAfter:max tauAfter by 0D00:01 xbar time from widen";
  "MODE";
  "target[]";
  "exposures[]";
  "$[MODE=`mpo; plan[]; MODE=`mso; books[]; `single]";
  ".po.parts[d;cur]";
  "`turnoverLeft`budgetLo`budgetHi!((b`u) b`rO;(b`l) b`rB;(b`u) b`rB)";
  "pend";
  "px";
  "b`n`k`N`M";
  / ── the live history behind the Lab charts (hist, once a second)
  "`rows`seconds`names!(count hist; `long$1e-9*(max hist`time)-min hist`time; count distinct hist`sym)";
  "select meanGap:avg abs h-h0, maxGap:max abs h-h0, h0Min:min h0, h0Max:max h0, hMin:min h, hMax:max h, atCap:avg h>=0.2999, atZero:avg h<=1e-4 by sym from hist";
  "select h0Total:avg h0Sum, h0Min:min h0Sum, h0Max:max h0Sum, hTotal:avg hSum from select h0Sum:sum h0, hSum:sum h by time from hist";
  "select n:count i, avgMs:avg totalMs, avgIter:avg iter by fillsInBatch:5 xbar 0^deltas nfills from solves";
  "$[MODE=`mpo; select planGap2:avg abs e1-h, planGap3:avg abs e2-h, plan3vsBook:avg abs e2-h0 by sym from hist; `na]";
  "$[MODE=`mso; select gross:0.25*(sum abs 1_deltas e1)+(sum abs 1_deltas e2)+(sum abs 1_deltas e3)+sum abs 1_deltas e4, net:sum abs 1_deltas h by sym from hist; `na]";
  "$[MODE=`mso; select booksAtCap:avg (e1>=0.2999)+(e2>=0.2999)+(e3>=0.2999)+e4>=0.2999, booksAtZero:avg (e1<=1e-4)+(e2<=1e-4)+(e3<=1e-4)+e4<=1e-4 by sym from hist; `na]";
  / ── Lab A1: OSQP's demo problem, by hand
  "dmpP:.qp.csc[2;2;0 0 1;0 1 1;4 1 2f]";
  "dmpA:.qp.csc[3;2;0 1 0 2;0 0 1 1;1 1 1 1f]";
  "dmpH:.qp.setup[dmpP;1 1f;dmpA;1 0 0f;1 0.7 0.7;::]";
  "`status`iter`obj`x#.qp.solve dmpH";
  ".qp.free dmpH";
  / ── Lab A2: build, solve, check
  "\\t dmpD:.po.universe[2000;50;7]";
  "\\t dmpB:.po.single dmpD";
  "dmpB`n`k`N`M`rT`rB`rO";
  "`nnzA`nnzE`nnzP!(count dmpB[`A;4]; 2000*50; count dmpB[`P;4])";
  "\\t dmpH:.po.setup[dmpB;.qp.S 2000]";
  "\\t dmpR:.qp.solve dmpH";
  "`status`iter`obj`primRes`dualRes`setupTime`solveTime`runTime#dmpR";
  "dmpZ:.po.split[dmpB;dmpR`x]; .po.parts[dmpD;dmpZ]";
  "`budget`xpGap`bsMax`turnover`minH`maxH!(sum dmpZ`h; max abs (dmpZ`xp)-(flip dmpD`X) mmu dmpZ`h; max (dmpZ`b)*dmpZ`s; sum (dmpZ`b)+dmpZ`s; min dmpZ`h; max dmpZ`h)";
  "`buys`sells`namesBought`namesSold`namesHeld`atUpperBound!(sum dmpZ`b; sum dmpZ`s; sum 1e-6<dmpZ`b; sum 1e-6<dmpZ`s; sum 1e-6<dmpZ`h; sum (dmpZ`h)>=0.999*dmpD`hi)";
  "pct[dmpZ`h;0 .1 .25 .5 .75 .9 .99 1]";
  "pct[(dmpZ`h)-dmpD`h0;0 .01 .1 .5 .9 .99 1]";
  "abs (.po.parts[dmpD;dmpZ]`objective)-dmpR`obj";
  / ── Lab B1: forty fills, each followed by a warm re-solve
  "dmpS:dmpFill[2000]\\[(dmpB;dmpH;dmpZ`h;0n;0;`;0n);til 40]";
  "dmpFT:([] fill:1+til 40; ms:dmpS[;3]; iter:dmpS[;4]; status:dmpS[;5]; tauLeft:dmpS[;6])";
  "dmpFT";
  "select n:count i, medMs:med totalMs, p90Ms:pct[totalMs;0.9], maxMs:max totalMs, avgIter:avg iter, maxIter:max iter by status from dmpFT";
  "dmpB:dmpS[39;0]";
  "\\t dmpR2:.qp.solve dmpH2:.po.setup[dmpB;.qp.S 2000]";
  "`status`iter#dmpR2";
  ".qp.free dmpH2";
  / ── Lab B2: a new alpha, a new lambda, a wrong-length update
  "dmpB:.po.alpha[dmpB;dmpD[`alpha]+0.005*.po.nrm 2000]; .qp.update[dmpH;dmpB`q;::;::]";
  "\\t dmpR:.qp.solve dmpH";
  "`status`iter`obj#dmpR";
  "dmpB:.po.lambda[dmpB;dmpD;4f]; .qp.updmat[dmpH;dmpB[`P;4];::]";
  "\\t dmpR:.qp.solve dmpH";
  "`status`iter`obj#dmpR";
  ".po.parts[dmpD,enlist[`lambda]!enlist 4f;.po.split[dmpB;dmpR`x]]";
  "@[.qp.updmat[dmpH;;::];-1_dmpB[`P;4];{\"refused: \",x}]";
  ".qp.free dmpH";
  / ── Lab C1: four periods, 800 names
  "dmpD8:.po.universe[800;50;7]";
  "\\t dmpM:.po.mpo[dmpD8;4;0.7]";
  "dmpM`N`M`H";
  "\\t dmpRM:.qp.solve dmpHM:.po.setup[dmpM;.qp.S 800]";
  "`status`iter`obj#dmpRM";
  "{[m;d;v;t] p:.po.period[m;v;t]; `period`turnover`alpha`names!(t+1; sum (p`b)+p`s; (d`alpha) wsum p`h; sum 1e-6<p`h)}[dmpM;dmpD8;dmpRM`x] each til 4";
  ".qp.free dmpHM";
  "dmpH1:.po.setup[.po.mpo[dmpD8;1;0.7];.qp.S 800]; dmpHs1:.po.setup[.po.single dmpD8;.qp.S 800]";
  "`mpoH1`single!((.qp.solve dmpH1)`obj;(.qp.solve dmpHs1)`obj)";
  ".qp.free each (dmpH1;dmpHs1)";
  / ── Lab C2: four strategies, one net book, 1,000 names
  "dmpDm:.po.universe[1000;50;7]; dmpAl:{0.03*.po.nrm x} each 4#1000";
  "\\t dmpMs:.po.mso[dmpDm;dmpAl;4#0.25;4#enlist dmpDm`h0;4#enlist dmpDm`hi]";
  "dmpMs`N`M`S";
  "\\t dmpRs:.qp.solve dmpHs:.po.setup[dmpMs;.qp.S 1000]";
  "`status`iter`obj#dmpRs";
  "dmpBk:.po.books[dmpMs;dmpRs`x]";
  "dmpGross:sum {sum abs x} each 0.25*(4#dmpBk)-\\:dmpDm`h0";
  "dmpNet:sum abs (last dmpBk)-dmpDm`h0";
  "`gross`net`crossedShare!(dmpGross;dmpNet;1-dmpNet%dmpGross)";
  "0.25*dmpAl wsum' 4#dmpBk";
  ".qp.free dmpHs";
  / ── Lab D1: cold solves, by rho and by size
  "dmpB0:.po.single dmpD";
  "dmpCold[dmpB0] each {(.qp.S 2000),enlist[`rho]!enlist x} each 0.1 1 10 28.6 100f";
  "dmpSize each 1000 2000 5000";
  / ── Lab D2: tolerance, measured in weights against the tightest solve
  "dmpE:dmpEps[dmpB0] each 1e-3 1e-4 1e-5 1e-7";
  "([] eps:dmpE[;0]; iter:dmpE[;1]; errAvgWeights:{2000*max abs x-y}[;last dmpE[;2]] each dmpE[;2])";
  / ── the other processes
  "rq[5010;\"`date`messages!(.u.d;.u.i)\"]";
  "rq[5010;\"count each .u.w\"]";
  "rq[5013;\"count each .u.w\"]";
  "rq[5011;\"tables[]!count each value each tables[]\"]";
  "rq[5014;\"count execs\"]");

optDump:{[]
  file:hsym `$getenv[`HOME],"/Code/port-opt-stack/optData.txt";
  c:system"c"; system"c 2000 2000";                 / wide console so tables are not truncated
  run:{[q] "q)",q,"\n",@[{.Q.s value x};q;{"'",x,"\n"}],"\n"};
  out:raze run each optQueries;
  system"c ",(" " sv string c);                     / restore the console size
  file 0: "\n" vs out;
  -1"wrote ",(1_string file);
  file };

/ the live history, for the Lab charts: one CSV per mode in bench/
histDump:{[]
  if[not `hist in key `.; :"no hist: opt.q is not loaded here"];
  f:hsym `$getenv[`HOME],"/Code/port-opt-stack/bench/live_",string[MODE],".csv";
  f 0: csv 0: hist;
  -1"wrote ",(1_string f)," · ",string[count hist]," rows";
  / the solve log and the tau widenings, for the solve-health charts
  g:{[t;nm] p:hsym `$getenv[`HOME],"/Code/port-opt-stack/bench/",nm,"_",string[MODE],".csv"; p 0: csv 0: t;
     -1"wrote ",(1_string p)," · ",string[count t]," rows"; p};
  g[solves;"solves"]; if[`widen in key `.; g[widen;"widen"]];
  f };
optDump0:optDump;
optDump:{[] r:optDump0[]; if[`hist in key `.; histDump[]]; r};

-1"dump → optDump[]  writes ~/Code/port-opt-stack/optData.txt, and bench/live_<mode>.csv when run in OPT";
