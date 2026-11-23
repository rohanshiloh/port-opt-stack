# port-opt-stack

**Weights in Motion** — intraday portfolio optimisation in q/kdb+ on OSQP.
Multi-Strategy & Multi-Period Portfolio Optimization with Constraints.
**Read the document: [rohanshiloh.github.io/port-opt-stack](https://rohanshiloh.github.io/port-opt-stack/)** (built from this repo's `index.html`).

A C shim (`c/qosqp.c`) that q loads with `2:`; problem builders in `port.q` (single period,
multi-period `.po.mpo`, multi-strategy `.po.mso`); a live optimiser (`opt.q`) behind exec-tca-stack's
chained tickerplant.

## Setup (macOS)

    ./setup.sh                  # OSQP's prebuilt v1.0.0 macOS library into ext/, k.h, tests, c/qosqp.so
    ./setup.sh --from-source    # fallback: build OSQP v1.0.0 with CMake instead
    q
    q)\l qp.q
    q)\l port.q

OSQP releases: https://github.com/osqp/osqp/releases ·
C interface: https://osqp.org/docs/get_started/C.html ·
benchmarks: https://github.com/osqp/osqp_benchmarks

## Run the live stack

With exec-tca-stack in `~/Code/exec-tca-stack`, either load `warp.yaml` as a Warp launch
configuration (`cp warp.yaml ~/.warp/launch_configurations/port-opt-stack.yaml`), or start one
process per terminal, in this order:

    cd ~/Code/exec-tca-stack && q tick.q sym ./log -p 5010           # TP
    cd ~/Code/exec-tca-stack && q tick/r.q :5010 -p 5011             # RDB
    cd ~/Code/exec-tca-stack && q log/sym -p 5012                    # HDB
    cd ~/Code/exec-tca-stack && q tick/chainedtick.q :5010 -p 5013   # chained TP
    cd ~/Code/exec-tca-stack && q tca.q :5013 -p 5014                # TCA CEP
    cd ~/Code/port-opt-stack && q opt.q :5013 -p 5015                # the optimiser
    cd ~/Code/exec-tca-stack && q feed.q :5010                       # feed, last
    cd ~/Code/port-opt-stack && q lab.q                              # CTRL: status[]

## Benchmarks and the page

    make bench                      # c/test/qbench: the shim, driven from C
    python3 bench/runbench.py       # needs numpy, scipy, clarabel
    python3 bench/multistrat.py
    python3 doc/charts.py
    python3 doc/build.py            # writes index.html
