/ port-opt-stack : the live optimiser, a subscriber of exec-tca-stack's chained TP
/ Every fill the TCA stack prints moves the book; every 250ms, if anything moved,
/ the optimiser moves h0 on the trade rows, spends the turnover the fills used,
/ and re-solves warm. One solver handle lives for the whole session.
/ usage:  q opt.q :5013 -p 5015 [-mode single|mpo|mso]
/   single  one book, one period: the target for now                      (default)
/   mpo     one book, H periods (days): trade period 1, the rest is a plan
/   mso     S strategy books, one period, one net book: trade only the net
/ In every mode a fill moves the same thing, the firm's h0 in period 1.
\l qp.q
\l port.q

o:.Q.opt .z.x;
MODE:$[`mode in key o; `$first o`mode; `single];
if[not MODE in `single`mpo`mso; '"mode: single, mpo or mso"];

/ the names exec-tca-stack trades (its sym.q), and a book worth NAV
uni:`AAPL`MSFT`NVDA`AMZN`TSLA`META`GOOGL`JPM;
NAV:5e8;
px:uni!182.4 418.1 121.7 178.9 244.3 503.6 166.2 201.8;   / last price seen per name
REBAL:0D00:01;                                            / turnover budget resets every minute

/ the problem: 8 names; five named styles and three industries (1.2a); up to 30%
/ in a name and up to 5% in cash. The industries are set by hand, the rest drawn
IND:`tech`consumer`financials;
SECTOR:uni!`tech`tech`tech`consumer`consumer`tech`tech`financials;
d:.po.mfm[count uni;count IND;42];
d[`X]:{[e;j] @[e;5+til count IND;:;"f"$j=til count IND]}'[d`X;IND?SECTOR uni];
d[`fnames]:.po.STYLES,IND;
exposures:{(d`fnames)!cur`xp};                             / the book's exposure to each factor
d[`hi]:(count uni)#0.3;
H:3; DECAY:0.7;                                           / mpo: 3 periods, alpha fading 30% a period
STRATS:`momentum`value`reversal`event;                    / mso: four illustrative books, equal capital
CAPS:(count STRATS)#1f%count STRATS;
ALPHAS:{system"S ",string x; 0.03*.po.nrm count uni} each 7+til count STRATS;
b:$[MODE=`single; .po.single d;
    MODE=`mpo;    .po.mpo[d;H;DECAY];
                  .po.mso[d;ALPHAS;CAPS;(count STRATS)#enlist d`h0;(count STRATS)#enlist d`hi]];
/ 0.95 <= 1'h <= 1: on every period's budget row in mpo, on the net book's in mso
bud:$[MODE=`mpo; b[`rB]+(b`M1)*til H; b`rB];
b[`l]:@[b`l;bud;:;0.95];
BOX:$[MODE=`mso; (0f;sum CAPS*(count STRATS)#enlist d`hi); (d`lo;d`hi)];   / mso: the net can reach only sum c_s hi_s
CO:$[MODE=`mso; b`co; 0];                                 / where the net book's columns start
hs:.po.setup[b;.qp.S count uni];
r:.qp.solve hs;
lastX:r`x;                                                / the last solution that solved
cur:.po.split[b;CO _ lastX];                                / period 1 / the net book. Not z: a z in a lambda makes it take three arguments
books:{$[MODE=`mso; ([] sym:uni),'flip (STRATS,`net)!.po.books[b;lastX]; '"books: mso only"]};
plan:{$[MODE=`mpo; ([] sym:uni),'flip (`$"h",/:string 1+til H)!{(.po.period[b;lastX;x])`h} each til H; '"plan: mpo only"]};

pend:uni!(count uni)#0f;                                  / weight moved by fills not yet in b
nFill:0; lastRebal:.z.n;

/ once a second, what the book is and what the optimiser wants, name by name: the
/ live charts in Labs E1, C1 and C2 are drawn from this. e1..e4 depend on the mode:
/ mpo, the planned books h2 and h3; mso, the four strategy books; single, empty.
hist:([] time:`timespan$(); sym:`symbol$(); h0:`float$(); h:`float$(); e1:`float$(); e2:`float$(); e3:`float$(); e4:`float$());
HISTEVERY:0D00:00:01; lastHist:0D;
logHist:{ n:count uni; h0v:(b`l) b[`rT]+til n;
  ex:$[MODE=`mpo; ((.po.period[b;lastX;1])`h; (.po.period[b;lastX;2])`h; n#0n; n#0n);
       MODE=`mso; 4#.po.books[b;lastX];
                  4#enlist n#0n];
  `hist insert (n#.z.n; uni; h0v; cur`h; ex 0; ex 1; ex 2; ex 3) };
/ one row per resolve. A failed first attempt is retried once with a wider tau: both attempts are kept.
/ primRes and dualRes are the final attempt's; epsPrim and epsDual are OSQP's stopping thresholds for them
/ (eps_abs + eps_rel * the problem's norms, with z taken as Ax clamped to [l,u]). rhoEstimate is OSQP's
/ estimate of a good rho, not necessarily the rho it used; rhoUpdates counts refactorisations from adaptive rho.
solves:([] time:`timespan$(); nfills:`long$(); windowReset:`boolean$(); retried:`boolean$();
  status1:`symbol$(); iter1:`long$(); ms1:`float$(); status2:`symbol$(); iter2:`long$(); ms2:`float$();
  totalMs:`float$(); status:`symbol$(); iter:`long$(); primRes:`float$(); epsPrim:`float$();
  dualRes:`float$(); epsDual:`float$(); rhoUpdates:`long$(); rhoEstimate:`float$();
  turnoverLeft:`float$(); objective:`float$());
/ one row each time tau is widened to repair an infeasible problem
widen:([] time:`timespan$(); tauLeftBefore:`float$(); tauAfter:`float$(); windowReset:`boolean$());
EPS:.qp.S[count uni]`eps_abs`eps_rel;

/ OSQP's stopping thresholds for this problem at solution (x;y): b holds A and the upper triangle of P as triplets
thresholds:{[x;y] Ax:@[b[`M]#0f;b`I;+;b[`V]*x b`J]; z:b[`l]|b[`u]&Ax;
  o:where b[`PI]<>b`PJ; Px:@[b[`N]#0f;b`PI;+;b[`PV]*x b`PJ]; Px:@[Px;b[`PJ] o;+;(b[`PV]*x b`PI) o];
  Aty:@[b[`N]#0f;b`J;+;b[`V]*y b`I];
  (EPS[0]+EPS[1]*max abs[Ax],abs z; EPS[0]+EPS[1]*max abs[Px],abs[Aty],abs b`q)};
target:{([sym:uni] h0:(b`l) b[`rT]+til b`n; h:cur`h; tradeShares:`long$NAV*(cur[`h]-(b`l) b[`rT]+til b`n)%px uni)};

/ the least turnover that brings h0 back inside lo <= h <= hi and 0.95 <= 1'h <= 1
tauNeed:{h0:(b`l) b[`rT]+til b`n; c:BOX[0]|BOX[1]&h0; m:sum abs c-h0;
  m+:(0|(b`l)[b`rB]-sum c)+0|(sum c)-(b`u) b`rB;
  (d`tau)|0.0001+1.05*m};

/ a fill: a buy of q shares at p adds q*p/NAV to the name's weight
upd:{[t;x] if[not t=`execs; :()];
  / execType="F" is a fill in exec-tca-stack's execution reports
  f:select sym, side, lastPx, lastQty from x where execType="F", sym in uni;
  if[0=count f; :()];
  px[f`sym]:f`lastPx;
  g:exec sym!dh from select dh:sum (?[side="B";1f;-1f])*lastQty*lastPx%NAV by sym from f;
  pend+:g; nFill+:count f };

resolve:{
  dh:value pend; pend::uni!(count uni)#0f;
  b::.po.fill[b;dh];
  reset:REBAL<.z.n-lastRebal;
  if[reset; b::.po.retau[b;d`tau]; lastRebal::.z.n];
  .qp.update[hs;::;b`l;b`u];
  t0:.z.p; r::.qp.solve hs; t1:.z.p; r1:r; retried:not `solved=r`status;
  / infeasible: the random fills from the feed walked h0 outside the box or the budget band
  / by more than tau can repair. Widen tau to what the repair needs, plus a margin, solve again
  if[retried; tb:(b`u) b`rO; tn:tauNeed[]; b::.po.retau[b;tn]; lastRebal::.z.n;
     `widen insert (.z.n; tb; tn; reset);
     .qp.update[hs;::;b`l;b`u]; r::.qp.solve hs];
  t2:.z.p; ms1:1e-6*`long$t1-t0; ms2:$[retried;1e-6*`long$t2-t1;0n];
  if[`solved=r`status; lastX::r`x; cur::.po.split[b;CO _ lastX];              / keep the last good target otherwise
     if[HISTEVERY<.z.n-lastHist; lastHist::.z.n; logHist[]]];
  th:thresholds[r`x;r`y];
  `solves insert (.z.n; nFill; reset; retried; r1`status; r1`iter; ms1;
    $[retried;r`status;`]; $[retried;r`iter;0N]; ms2; 1e-6*`long$t2-t0; r`status; r`iter;
    r`primRes; th 0; r`dualRes; th 1; r`rhoUpdates; r`rhoEstimate; (b`u) b`rO; r`obj) };


.z.ts:{ if[any 0<>value pend; resolve[]] };

/ subscribe to execs only, all syms, behind the chain
.u.rep:{(.[;();:;].)each x};
TP:$[count tps:.z.x where .z.x like ":*"; first tps; ":5013"];
.u.rep enlist (hopen `$":",TP)".u.sub[`execs;`]";
system"t 250";
-1"opt → mode ",string[MODE]," · subscribed @ ",TP,"   try:  target[]   -10#solves   select avg totalMs, max totalMs, avg iter from solves   exposures[]",$[MODE=`mpo;"   plan[]";MODE=`mso;"   books[]";""];
