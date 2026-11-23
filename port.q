/ port-opt-stack : portfolio problems in OSQP's one shape  (.po namespace)
/ OSQP solves  min ½x'Px + q'x  s.t.  l <= Ax <= u  and nothing else, so
/ every portfolio here is rewritten into that shape by hand. Notation is
/ Barra's for the finance (h X F Delta alpha lambda) and OSQP's for the solver
/ (x P q A l u). One period:
/   x = (h; xp; b; s)   holdings, factor exposures, buys, sells
/   min  -alpha'h + lambda*(h'Delta h + xp'F xp) + kappa'(b+s) + eta'(b*b + s*s)
/   s.t. X'h - xp = 0           factor exposures           (k rows)
/        h - b + s = h0         the trade, split in two     (n rows)  <- fills land here
/        1'h = budget           fully invested              (1 row)
/        lo <= h <= hi          diversification             (n rows)
/        0 <= b,s <= tmax       no negative trades, ADV cap (2n rows)
/        1'(b+s) <= tau         turnover                    (1 row)   <- and here
/        fl <= xp <= fu         factor-exposure limits      (k rows)
/ V = X F X' + Delta is never formed: xp carries X'h, so P stays diagonal plus
/ one k x k block, and the problem grows linearly in n.
/ |h-h0| is linear cost, which OSQP cannot take directly: b and s split the
/ trade into two non-negative parts, and with kappa>0 one of them is always 0.
/ Defined from the root with explicit .po. names (KDB-X, see qp.q).

/ ── a synthetic universe ─────────────────────────────────────────────────
/ annual units: alpha in return per year, variances per year. The shape of
/ bench/model.py, drawn with q's own generator, so the numbers differ from it.
.po.nrm:{[m] (sqrt -2*log m?1f)*cos 2*acos[-1]*m?1f};          / Box–Muller
.po.universe:{[n;k;seed]
  system"S ",string seed;
  X:0.3*k cut .po.nrm n*k;
  X:@[;0;:;]'[X;1+0.3*.po.nrm n];                               / factor 0: market beta ~ 1
  fv:0.18,0.02+0.06*(k-1)?1f;                                   / factor vols
  L:0.2*k cut .po.nrm k*k;
  R:("f"${x=/:x}til k)+0.1*L mmu flip L;                      / identity + noise
  dd:1%sqrt R@'til k; R:(R*dd)*\:dd;                            / to a correlation matrix
  F:(R*fv)*\:fv;
  Dl:{x*x}0.15+0.3*n?1f;                                        / specific variance
  h0:(0.5+n?1f)%n; h0:h0%sum h0;
  `alpha`X`F`Delta`h0`lo`hi`kappa`eta`lambda`tau`tmax`fl`fu`budget!(
    0.03*.po.nrm n; X; F; Dl; h0; n#0f; n#0.02|15%n;
    1e-4*2+6*n?1f;                                              / half-spread + fee, per unit weight
    0.25+0.75*n?1f;                                             / quadratic impact
    2f; 0.1; n#.qp.inf; k#neg .qp.inf; k#.qp.inf; 1f) };

/ ── a synthetic multiple-factor model with named factors (1.2a) ──────────
/ The shape of a vendor equity model, drawn at random: five styles, then nInd
/ industries, so k = 5 + nInd. Exposures are standardised the vendor way —
/ cap-weighted mean 0, equal-weighted standard deviation 1, clipped to ±5 —
/ except market, a beta around 1, and industries, 0/1 with 5% of names split
/ 65/35 between two (a conglomerate). Specific risk rises for small, volatile
/ names. Same keys as .po.universe, plus fnames, cap, bench (cap weights), ind.
.po.STYLES:`market`size`value`momentum`volatility;
.po.std:{[cw;x] x:x-cw wsum x; -5f|5f&x%dev x};
.po.mfm:{[n;nInd;seed]
  system"S ",string seed;
  z:.po.nrm each 6#n;
  cap:exp 23+1.2*z 0; cw:cap%sum cap;                           / market cap, log-normal
  size:.po.std[cw;log cap];
  val:.po.std[cw;(-0.2*size)+sqrt[0.96]*z 1];                   / big companies a little dearer
  mom:.po.std[cw;z 2];
  vol:.po.std[cw;(-0.4*size)+sqrt[0.84]*z 3];                   / small companies jumpier
  beta:0.3|2f&1+(0.15*vol)+0.2*z 4;                             / market: a beta, not a z-score
  ind:n?nInd;
  IE:"f"$ind=\:til nInd;                                        / one industry each
  cg:where 0.05>n?1f; j2:(ind[cg]+1+(count cg)?nInd-1) mod nInd;
  IE[cg]:{[r;a;b] @[r;a,b;:;0.65 0.35]}'[IE cg;ind cg;j2];       / conglomerates: 65% / 35%
  X:flip (beta;size;val;mom;vol),flip IE;                           / n x k, one row per stock
  k:5+nInd;
  RS:(1 -0.1 0 -0.1 0.5;-0.1 1 0.2 0 -0.3;0 0.2 1 -0.3 -0.1;-0.1 0 -0.3 1 0;0.5 -0.3 -0.1 0 1);
  RI:0.25+0.75*"f"${x=/:x}til nInd;                             / industries: 0.25 correlated
  R:.[(k;k)#0f;(til 5;til 5);:;RS]; R:.[R;(5+til nInd;5+til nInd);:;RI];
  fv:0.16 0.03 0.025 0.04 0.035,0.04+0.04*nInd?1f;              / annual factor vols
  F:(R*fv)*\:fv;
  sdv:0.08|0.8&0.22*exp[(0.25*vol)-0.15*size]*exp 0.2*z 5;       / specific vol, cf. EQ 3-14
  h0:(0.5+n?1f)%n; h0:h0%sum h0;
  `alpha`X`F`Delta`h0`lo`hi`kappa`eta`lambda`tau`tmax`fl`fu`budget`fnames`cap`bench`ind!(
    0.03*.po.nrm n; X; F; sdv*sdv; h0; n#0f; n#0.02|15%n;
    1e-4*2+6*n?1f; 0.25+0.75*n?1f;
    2f; 0.1; n#.qp.inf; k#neg .qp.inf; k#.qp.inf; 1f;
    .po.STYLES,`$"ind",/:string til nInd; cap; cw; ind) };

/ ── one period's triplets, at a column offset co and a row offset ro ─────
/ isFirst: only the first period's trade rows carry h0 (Lab C1 stacks these).
.po.blocks:{[d;co;ro;isFirst]
  n:count d`alpha; k:count d`F;
  cy:co+n; cb:cy+k; cs:cb+n;                                    / columns of y, b, s
  rF:ro; rT:ro+k; rB:rT+n; rX:rB+1; rS:rX+n; rO:rS+2*n; rY:rO+1;   / first row of each block
  a:raze k#'til n; f:raze n#enlist til k;                       / (asset;factor) for every X entry
  I:(rF+f; rF+til k; rT+til n; rT+til n; rT+til n; n#rB; rX+til n; rS+til 2*n; (2*n)#rO; rY+til k);
  J:(co+a; cy+til k; co+til n; cb+til n; cs+til n; co+til n; co+til n; cb+til 2*n; cb+til 2*n; cy+til k);
  V:(raze d`X; k#-1f; n#1f; n#-1f; n#1f; n#1f; n#1f; (2*n)#1f; (2*n)#1f; k#1f);
  fg:til[k] cross til k; fg:fg where fg[;0]<=fg[;1];            / upper triangle of C
  lam:d`lambda;
  PI:(co+til n; cy+fg[;0]; cb+til 2*n);
  PJ:(co+til n; cy+fg[;1]; cb+til 2*n);
  PV:(2*lam*d`Delta; 2*lam*(d`F) ./: fg; 2*(d`eta),d`eta);          / ½x'Px, hence the 2s
  h0:$[isFirst; d`h0; n#0f];
  l:(k#0f),h0,(enlist d`budget),(d`lo),((2*n)#0f),(enlist 0f),d`fl;
  u:(k#0f),h0,(enlist d`budget),(d`hi),(d`tmax),(d`tmax),(enlist d`tau),d`fu;
  `I`J`V`PI`PJ`PV`q`l`u`n`k`N`M`rT`rB`rO!(raze I; raze J; raze V; raze PI; raze PJ; raze PV;
     (neg d`alpha),(k#0f),(d`kappa),d`kappa; l; u; n; k; k+3*n; 2+(2*k)+4*n; rT; rB; rO) };

/ triplets -> the P and A the shim takes
.po.pack:{[b] b,`P`A!(.qp.csc[b`N;b`N;b`PI;b`PJ;b`PV]; .qp.csc[b`M;b`N;b`I;b`J;b`V])};

.po.single:{[d] .po.pack .po.blocks[d;0;0;1b]};

/ x -> its four blocks: holdings, exposures, buys, sells
.po.split:{[b;x] n:b`n; k:b`k;
  `h`xp`b`s!(n#x; k#n _ x; n#(n+k) _ x; n#(k+2*n) _ x)};

/ the economics of a solution, recomputed by hand: what the objective is made of
.po.parts:{[d;z]
  ret:(d`alpha) wsum z`h;
  risk:(d`lambda)*((d`Delta) wsum z[`h]*z`h)+(z`xp) wsum (d`F) mmu z`xp;
  cost:((d`kappa) wsum (z`b)+z`s)+(d`eta) wsum (z[`b]*z`b)+z[`s]*z`s;
  `alpha`risk`cost`objective`turnover`names!(ret; risk; cost; risk+cost-ret;
     sum (z`b)+z`s; sum 1e-6<z`h) };

.po.setup:{[b;s] .qp.setup[b`P;b`q;b`A;b`l;b`u;s]};

/ ── the fill: move h0 on the trade rows, and spend the turnover it used ──
/ dh: change in holding per asset, n floats. Nothing else in the problem moves,
/ so this is two vector updates and a warm re-solve: no refactorisation.
.po.fill:{[b;dh]
  r:b[`rT]+til b`n;
  b[`l]:@[b`l;r;+;dh]; b[`u]:@[b`u;r;+;dh];
  b[`u]:@[b`u;b`rO;{0f|x-y}[;sum abs dh]];
  b };

/ a new rebalance window: the turnover budget starts again
.po.retau:{[b;tau] b[`u]:@[b`u;b`rO;:;tau]; b};

/ new alphas: only q moves
.po.alpha:{[b;alpha] b[`q]:@[b`q;til b`n;:;neg alpha]; b};

/ a new risk aversion scales every value in P: same sparsity, so updmat, not setup
.po.lambda:{[b;d;lam] d[`lambda]:lam; b2:.po.blocks[d;0;0;1b];
  o:iasc b2[`PI]+b2[`N]*b2`PJ;                          / the csc order .qp.csc used
  b[`P;4]:b2[`PV] o; b };

/ ── multi-period: H stacked periods, the first trade executed ───────────
/ Period t's alpha is alpha*decay^t: the signal fades, so later periods trade
/ less on it. Period t's trade rows also carry -h(t-1): its trade is measured
/ from the book the previous period left, not from h0.
.po.mpo:{[d;H;decay]
  n:count d`alpha; k:count d`F; N1:k+3*n; M1:2+(2*k)+4*n;
  bs:{[d;N1;M1;decay;t] .po.blocks[@[d;`alpha;*;decay xexp t]; t*N1; t*M1; t=0]}[d;N1;M1;decay] each til H;
  ks:`I`J`V`PI`PJ`PV`q`l`u;
  b:ks!{raze x@\:y}[bs] each ks;
  t:1_til H;
  b[`I]:b[`I],raze {[bs;n;t] bs[t;`rT]+til n}[bs;n] each t;
  b[`J]:b[`J],raze {[N1;n;t] ((t-1)*N1)+til n}[N1;n] each t;
  b[`V]:b[`V],((H-1)*n)#-1f;
  .po.pack b,`n`k`N`M`H`N1`M1`rT`rB`rO!(n; k; H*N1; H*M1; H; N1; M1; bs[0;`rT]; bs[0;`rB]; bs[0;`rO]) };

/ period t's blocks from an MPO solution
.po.period:{[b;x;t] .po.split[b; (b`N1)#(t*b`N1)_x]};

/ ── multi-strategy: S books, one net book, costs on the net ─────────────
/ x = (h_1 .. h_S; h; xp; b; s). Each strategy keeps its own budget and box
/ and earns its own alpha on its share of capital; the firm holds the net
/ book h = sum c_s h_s, carries the risk on it, and pays costs only on the
/ NET trade. Two strategies trading the same name in opposite directions
/ cross internally for free, which optimise-then-net cannot see (Lab C2).
.po.mso:{[d;alphas;caps;h0s;his]
  n:count d`alpha; S:count alphas; co:S*n;
  fd:d,`alpha`budget`lo`hi!(n#0f;1f;n#0f;n#1f);                / the firm block: no alpha of its own
  b:.po.blocks[fd;co;0;1b];
  M0:b`M;
  st:{[n;M0;hi;s] r:M0+s*n+1; c:s*n;                            / strategy s: budget row, then box rows
      `I`J`V`l`u!((n#r),r+1+til n; (c+til n),c+til n; (2*n)#1f; 1f,n#0f; 1f,hi)}[n;M0]'[his;til S];
  rN:M0+S*n+1;                                                  / net rows: h - sum c_s h_s = 0
  nI:raze (S+1)#enlist rN+til n;
  nJ:(co+til n),raze {[n;s] (s*n)+til n}[n] each til S;
  nV:(n#1f),raze {[n;c] n#neg c}[n] each caps;
  b[`I]:b[`I],(raze st@\:`I),nI; b[`J]:b[`J],(raze st@\:`J),nJ; b[`V]:b[`V],(raze st@\:`V),nV;
  h0:sum caps*h0s;
  l:@[b`l;b[`rT]+til n;:;h0]; u:@[b`u;b[`rT]+til n;:;h0];
  b[`l]:l,(raze st@\:`l),n#0f; b[`u]:u,(raze st@\:`u),n#0f;
  b[`q]:(neg raze caps*alphas),b`q;
  b[`N]:co+b`N; b[`M]:rN+n;
  .po.pack b,`S`co!(S;co) };

/ the strategies' books and the net book from a multi-strategy solution
.po.books:{[b;x] n:b`n; (n cut (b`co)#x),enlist n#(b`co)_x};

-1"port → .po.universe .po.mfm  ·  .po.single .po.mpo .po.mso  ·  .po.fill .po.alpha .po.lambda  ·  .po.parts .po.split";
