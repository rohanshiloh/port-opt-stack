/ port-opt-stack : Lab D1 from q — cold solve, then warm re-solves on fills
/ The same experiment as c/test/bench.c, driven through the shim from a q prompt.
/ usage:  q bench.q 2000        (number of names; 50 factors)
\l qp.q
\l port.q
n:$[count .z.x; "J"$first .z.x; 2000];
d:.po.universe[n;50;7];
\t b:.po.single d
-1"vars ",string[b`N],"  rows ",string[b`M],"  nnz(A) ",string count b[`A;4];
tSetup:value"\\t hs:.po.setup[b;.qp.S n]";
tCold:value"\\t r:.qp.solve hs";
-1"setup ",string[tSetup],"ms   cold solve ",string[tCold],"ms   ",string[r`iter]," iterations   ",string r`status;
show .po.parts[d;.po.split[b;r`x]];

/ forty fills: each moves 1% of names a quarter of the way to target
onFill:{[n;b;hs;tgt;e] a:neg[1|n div 100]?n;
  dh:@[n#0f;a;:;0.25*(tgt a)-(b`l) b[`rT]+a];
  b:.po.fill[b;dh]; .qp.update[hs;::;b`l;b`u];
  t0:.z.p; r:.qp.solve hs; ms:1e-6*`long$.z.p-t0;
  (b; n#r`x; ms; r`iter)};
st:(b; n#r`x; 0n; 0N);
res:{[n;hs;st;e] onFill[n;st 0;hs;st 1;e]}[n;hs]\[st;til 40];
ms:res[;2]; it:res[;3];
-1"warm re-solve over 40 fills: median ",string[med ms],"ms  90th ",string[ms (iasc ms) 36],"ms  avg iterations ",string avg it;
