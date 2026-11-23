# port-opt-stack

**Weights in Motion** — intraday portfolio optimisation in q/kdb+ on OSQP.
Multi-Strategy & Multi-Period Portfolio Optimization with Constraints.
**Read the document: [rohanshiloh.github.io/port-opt-stack](https://rohanshiloh.github.io/port-opt-stack/)** (built from this repo's `index.html`).

A C shim (`c/qosqp.c`) that q loads with `2:`; problem builders in `port.q` (single period,
multi-period `.po.mpo`, multi-strategy `.po.mso`); a live optimiser (`opt.q`) behind exec-tca-stack's
chained tickerplant.

## Setup (macOS or Linux)

Pick the platform with a flag; without one, `setup.sh` takes it from `uname`.

    ./setup.sh --mac                  # macOS: OSQP's v1.0.0 release, Apple clang, k.h, tests, c/qosqp.so
    ./setup.sh --linux                # Linux x86-64: the same with OSQP's Linux release and gcc
    ./setup.sh --mac --from-source    # either platform: build OSQP v1.0.0 with CMake instead
    q
    q)\l qp.q
    q)\l port.q

The flag has to match the machine: `setup.sh` builds for the computer it runs on and does
not cross-compile, so `--linux` on a Mac stops with a message.

OSQP releases: https://github.com/osqp/osqp/releases ·
C interface: https://osqp.org/docs/get_started/C.html ·
benchmarks: https://github.com/osqp/osqp_benchmarks

## Building the C shim

`c/qosqp.c` is a 180-line C file that sits between q and OSQP. It converts q objects
(via KX's `k.h`) into OSQP's C structures and back, and keeps up to 256 solvers alive
between calls. It is built as `c/qosqp.so`, which `qp.q` loads with `2:`. It builds with
Apple clang on macOS and with gcc on Linux; the Makefile picks the compiler from `uname -s`.

### What setup.sh runs

After downloading OSQP into `ext/osqp` and `k.h` into `c/`, `setup.sh` compiles with two lines,
where `OS` is `Darwin` for `--mac` and `Linux` for `--linux`:

    make OS=$OS OSQP=$OSQP clean test      # the shim's own tests, no q needed
    make OS=$OS OSQP=$OSQP                 # c/qosqp.so, which qp.q loads

`make` in turn runs one of these (the Makefile rule for `c/qosqp.so`):

    # macOS
    clang -O2 -Wall -Wno-unused-parameter -arch $(uname -m) \
      -Iext/osqp/include -Ic c/qosqp.c -Lext/osqp/lib -losqp \
      -Wl,-rpath,'@loader_path/../ext/osqp/lib' \
      -bundle -undefined dynamic_lookup -o c/qosqp.so

    # Linux
    gcc -O2 -Wall -Wno-unused-parameter -fPIC \
      -Iext/osqp/include -Ic c/qosqp.c -Lext/osqp/lib -losqp \
      -Wl,-rpath,'$ORIGIN/../ext/osqp/lib' \
      -shared -o c/qosqp.so

The rest of this section is the same thing by hand.

### macOS, with clang

**1. Prerequisites**

    xcode-select --install          # Apple clang, ld and make (the Command Line Tools)
    clang --version                 # any recent Apple clang
    uname -m                        # arm64 (Apple silicon) or x86_64 (Intel)

Homebrew's gcc is not needed. q must be the same architecture as the shim: an arm64 q
cannot load an x86_64 bundle, and the reverse.

**2. OSQP: the prebuilt release**

    mkdir -p ext/osqp
    curl -fsSL https://github.com/osqp/osqp/releases/download/v1.0.0/osqp-v1.0.0-macos-latest.tar.gz \
      | tar xz -C ext/osqp          # Intel Macs: osqp-v1.0.0-macos-13.tar.gz
    ls ext/osqp/lib                 # libosqp.dylib
    ls ext/osqp/include             # osqp.h and the other public headers

The release leaves out one header, `osqp_configure.h`. The repo supplies it in
`c/osqp_configure.h`, matching how the release was built: built-in linear algebra,
code generation, derivatives, printing, profiling and interrupt on, and `OSQP_USE_LONG`,
so OSQP's integer `OSQPInt` is 64-bit, the same as q's `long`.

**3. k.h**

    curl -fsSL https://raw.githubusercontent.com/KxSystems/kdb/master/c/c/k.h -o c/k.h

[`k.h`](https://github.com/KxSystems/kdb/blob/master/c/c/k.h) declares q's C API: the `K`
object type and the functions the shim calls (`ktn`, `kf`, `knk`, `krr` and so on).
Nothing is linked against: q provides those symbols itself when it loads the bundle.

**4. Compile and link**

    clang -O2 -Wall -Wno-unused-parameter -arch $(uname -m) \
      -Iext/osqp/include -Ic \
      c/qosqp.c \
      -Lext/osqp/lib -losqp \
      -Wl,-rpath,'@loader_path/../ext/osqp/lib' \
      -bundle -undefined dynamic_lookup \
      -o c/qosqp.so

| Flag | Why |
|---|---|
| `-O2 -Wall -Wno-unused-parameter` | optimise; warn, except about the unused arguments q's calling convention forces |
| `-arch $(uname -m)` | build for this Mac's CPU, the same as q |
| `-Iext/osqp/include -Ic` | OSQP's headers, then `c/` for `k.h` and the missing `osqp_configure.h` |
| `-Lext/osqp/lib -losqp` | link against `libosqp.dylib` |
| `-Wl,-rpath,'@loader_path/../ext/osqp/lib'` | at load time, find the dylib relative to the `.so` itself, so the repo can live anywhere |
| `-bundle` | make a loadable bundle, which is what q's `2:` opens |
| `-undefined dynamic_lookup` | leave the `k.h` functions unresolved; q supplies them when it loads the bundle |

**5. Check it**

    make test                                    # 23 tests of the shim in C, no q needed
    otool -L c/qosqp.so                          # should list @rpath/libosqp.dylib
    nm -gU c/qosqp.so | grep qp_                 # qp_setup qp_solve qp_update qp_updmat qp_warm qp_set qp_free qp_ver

### Linux, with gcc

The same steps, with the Linux release and gcc. Tested on Ubuntu 24.04 with gcc 13.

**1. Prerequisites**

    sudo apt install build-essential curl        # gcc, make, curl (Debian/Ubuntu)
    gcc --version
    uname -m                                     # x86_64: the only Linux release OSQP publishes

On ARM Linux (aarch64) there is no release library: use `./setup.sh --from-source`.

**2. OSQP: the prebuilt release**

    mkdir -p ext/osqp
    curl -fsSL https://github.com/osqp/osqp/releases/download/v1.0.0/osqp-v1.0.0-ubuntu-latest.tar.gz \
      | tar xz -C ext/osqp
    ls ext/osqp/lib                 # libosqp.so

Like the macOS one, the Linux release has no `osqp_configure.h`; `c/osqp_configure.h`
covers both systems.

**3. k.h** — the same `curl` as on macOS.

**4. Compile and link**

    gcc -O2 -Wall -Wno-unused-parameter -fPIC \
      -Iext/osqp/include -Ic \
      c/qosqp.c \
      -Lext/osqp/lib -losqp \
      -Wl,-rpath,'$ORIGIN/../ext/osqp/lib' \
      -shared \
      -o c/qosqp.so

| Flag | Why |
|---|---|
| `-fPIC` | position-independent code, required for a shared object |
| `-shared` | make a shared object, which q's `2:` opens; unlike macOS, undefined `k.h` symbols are allowed by default and resolved by q at load |
| `-Wl,-rpath,'$ORIGIN/../ext/osqp/lib'` | find `libosqp.so` relative to the `.so`; the single quotes stop the shell expanding `$ORIGIN` |

The other flags are as on macOS.

**5. Check it**

    make test                                    # the same 23 tests, built with gcc
    readelf -d c/qosqp.so | grep -E 'NEEDED|RUNPATH'   # libosqp.so and $ORIGIN/../ext/osqp/lib
    ldd c/qosqp.so | grep osqp                   # resolves to ext/osqp/lib/libosqp.so
    nm -D --defined-only c/qosqp.so | grep qp_   # the eight qp_ functions

### Load it in q (both systems)

    q
    q)\l qp.q                                    # loads the eight functions with 2:
    q).qp.ver[::]
    "v1.0.0"

`qp.q` loads `c/qosqp.so` relative to the directory q was started in, so start q from the
repo root. To keep the library elsewhere, point `QOSQP` at it, without the `.so`:

    QOSQP=/path/to/qosqp q

Under KDB-X it does not need to go into the q install folder.

### Building OSQP from source instead

If the release does not suit (another OSQP version, a static build, or ARM Linux),
`./setup.sh --from-source` clones OSQP v1.0.0 into `ext/osqp-src` and builds a static
library with CMake, on either system:

    git clone --depth 1 --branch v1.0.0 https://github.com/osqp/osqp ext/osqp-src
    cmake -S ext/osqp-src -B ext/osqp-src/build -DCMAKE_BUILD_TYPE=Release \
          -DOSQP_BUILD_SHARED_LIB=OFF -DOSQP_BUILD_DEMO_EXE=OFF -DCMAKE_POSITION_INDEPENDENT_CODE=ON
    cmake --build ext/osqp-src/build -j
    make OSQP=ext/osqp-src

The static library is linked into `c/qosqp.so`, so no rpath is needed. CMake's build also
writes its own `osqp_configure.h`.

### When it goes wrong

| Symptom | Cause and fix |
|---|---|
| `incompatible architecture` (macOS) or `wrong ELF class` (Linux) in q | q and the shim are different architectures: check `file c/qosqp.so` and `file $(which q)` |
| `Library not loaded: @rpath/libosqp.dylib` / `libosqp.so: cannot open shared object file` | the library is not at `ext/osqp/lib`, relative to the `.so`: rerun step 2, or rebuild |
| `'osqp_configure.h' file not found` | `-Ic` is missing, or `c/osqp_configure.h` is not in the repo |
| `'k.h' file not found` | step 3 was skipped |
| macOS says the dylib "cannot be opened" | it was downloaded with a browser and is quarantined: `xattr -dr com.apple.quarantine ext/osqp` |
| `GLIBC_2.xx not found` (Linux) | the release was built on a newer Ubuntu than this machine: use `./setup.sh --from-source` |
| `'nyi` or `'qp_setup` from `2:` | the library is an old build: `make clean && make`, then restart q |

## Run the live stack

With exec-tca-stack in `~/Code/exec-tca-stack`, either load `warp.yaml` as a Warp launch
configuration (`cp warp.yaml ~/.warp/launch_configurations/port-opt-stack.yaml`), or start one
process per terminal, in this order:

    cd ~/Code/exec-tca-stack && q tick.q sym ./log -p 5010           # TP
    cd ~/Code/exec-tca-stack && q tick/r.q :5010 -p 5011             # RDB
    cd ~/Code/exec-tca-stack && q log/sym -p 5012                    # HDB
    cd ~/Code/exec-tca-stack && q tick/chainedtick.q :5010 -p 5013   # chained TP
    cd ~/Code/exec-tca-stack && q tca.q :5013 -p 5014                # TCA CEP
    cd ~/Code/port-opt-stack && q opt.q :5013 -p 5015 -mode single   # the optimiser (or -mode mpo, -mode mso)
    cd ~/Code/exec-tca-stack && q feed.q :5010                       # feed, last
    cd ~/Code/port-opt-stack && q lab.q                              # CTRL: status[]

## Benchmarks and the page

    make bench                      # c/test/qbench: the shim, driven from C
    python3 bench/runbench.py       # needs numpy, scipy, clarabel
    python3 bench/multistrat.py
    python3 doc/charts.py
    python3 doc/build.py            # writes index.html
