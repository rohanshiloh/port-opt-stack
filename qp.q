/ port-opt-stack : OSQP for q  (.qp namespace)
/ Loads the shim built by `make` (c/qosqp.c) and adds the one helper every
/ caller needs: triplets -> compressed sparse column. Defined from the root with
/ explicit .qp. names, because KDB-X does not fall back to the root for reads
/ made inside a namespace.

.qp.lib:`$":",getenv[`QOSQP],$[count getenv`QOSQP;"";"c/qosqp"];   / override with QOSQP=/path/qosqp
.qp.setup :.qp.lib 2:(`qp_setup;6);     / [P;q;A;l;u;settings] -> handle
.qp.solve :.qp.lib 2:(`qp_solve;1);     / [hs] -> dict: status iter obj x y and timings
.qp.update:.qp.lib 2:(`qp_update;4);    / [hs;q;l;u]  (::) = unchanged
.qp.updmat:.qp.lib 2:(`qp_updmat;3);    / [hs;Px;Ax]  same sparsity, every value
.qp.warm  :.qp.lib 2:(`qp_warm;3);      / [hs;x;y]    (::) = unchanged
.qp.set   :.qp.lib 2:(`qp_set;2);       / [hs;settings] after setup
.qp.free  :.qp.lib 2:(`qp_free;1);      / [hs]
.qp.ver   :.qp.lib 2:(`qp_ver;1);       / [::] -> "v1.0.0"

/ OSQP reads anything at or beyond 1e30 as infinite
.qp.inf:1e30;

/ The settings this stack uses. eps 1e-5: with 2,000 names a weight is ~5e-4,
/ and a looser tolerance moves weights by more than they are worth (Lab D2).
/ rho: OSQP's default (0.1) is far too small for a factor-model portfolio; the
/ right value grows with the number of names. n%70 is the rule fitted in Lab D1.
.qp.S:{[n] `eps_abs`eps_rel`polishing`max_iter`rho!(1e-5;1e-5;0;200000;`float$n%70)};

/ triplets -> (m;n;p;i;x), the form the shim takes.
/ Sorted by column, then row within a column, which OSQP requires.
/ P must be the UPPER triangle only: OSQP reads the lower half from it.
.qp.csc:{[m;n;i;j;v]
  m:`long$m; n:`long$n; i:`long$i; j:`long$j;
  o:iasc i+m*j;                                   / one sort key: column-major
  if[count[o]>count distinct i+m*j; '"csc: duplicate (row;col) entry"];
  i:i o; j:j o;
  (m; n; 0,sums @[n#0;j;+;1]; i; `float$v o) };   / column pointers: counts, summed

/ a dense q matrix (list of rows) -> csc, keeping only the nonzeros
.qp.dense:{[M] m:count M; n:count first M; rc:raze til[m],/:\:til n;   / not ij: that is inner join
  v:raze M; k:where v<>0f; .qp.csc[m;n;rc[k;0];rc[k;1];v k] };

-1("qp → OSQP ",.qp.ver[::]," loaded from ",1_string .qp.lib;
  "   \\l port.q                                    the problem builders (.po.*)";
  "   d:.po.universe[2000;50;7]; b:.po.single d     a synthetic book, one period";
  "   hs:.po.setup[b;.qp.S 2000]; r:.qp.solve hs    set up once, solve";
  "   r`status`iter`obj                             did it solve, how fast";
  "   .po.parts[d;.po.split[b;r`x]]                 alpha, risk, cost, turnover";
  "   .qp.free hs                                   release the solver");
