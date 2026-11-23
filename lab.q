/ port-opt-stack : CTRL-tab helpers  —  q lab.q
/ Load in the CTRL tab, never inside OPT: OPT has a solves table and its own helpers.
/ Pings every process of the stack and asks the optimiser for its state.
/ Each call opens and closes its own handle, so a process that restarts is fine.
procs:([] proc:`TP`RDB`HDB`CTP`TCA`OPT; port:5010 5011 5012 5013 5014 5015);
up:{@[{hclose hopen x; `up};x;`down]};
status:{update state:up each port from procs};
ask:{[port;x] h:hopen port; r:h x; hclose h; r};
opt:ask 5015;                                  / opt"target[]"   opt"-10#solves"
solveStats:{opt"select n:count i, avgMs:avg ms, maxMs:max ms, avgIter:avg iter by status from solves"};
-1"lab → status[]   opt\"target[]\"   solveStats[]   ask[5014;\"…\"]";
