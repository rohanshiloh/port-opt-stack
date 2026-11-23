#!/bin/sh
# port-opt-stack : set up on macOS (Apple silicon or Intel), from the repository root
#   ./setup.sh                 OSQP's prebuilt release library   (the default)
#   ./setup.sh --from-source   OSQP built here with CMake         (the fallback)
#
# OSQP releases:          https://github.com/osqp/osqp/releases
# OSQP C interface docs:  https://osqp.org/docs/get_started/C.html
#
# Needs the Xcode Command Line Tools (clang), curl and tar; CMake only for
# --from-source. Nothing is installed outside this folder: OSQP goes in ext/.
set -e
V=v1.0.0
[ "$(uname -s)" = Darwin ] || { echo "setup.sh: macOS only"; exit 1; }
case "$(uname -m)" in arm64) PKG=macos-latest ;; *) PKG=macos-13 ;; esac   # macos-13 = Intel

if [ "$1" = "--from-source" ]; then
  [ -d ext/osqp-src ] || git clone --depth 1 --branch $V https://github.com/osqp/osqp ext/osqp-src
  cmake -S ext/osqp-src -B ext/osqp-src/build -DCMAKE_BUILD_TYPE=Release \
        -DOSQP_BUILD_SHARED_LIB=OFF -DOSQP_BUILD_DEMO_EXE=OFF -DCMAKE_POSITION_INDEPENDENT_CODE=ON
  cmake --build ext/osqp-src/build -j
  OSQP=ext/osqp-src
else
  if [ ! -f ext/osqp/lib/libosqp.dylib ]; then
    mkdir -p ext/osqp
    curl -fsSL https://github.com/osqp/osqp/releases/download/$V/osqp-$V-$PKG.tar.gz | tar xz -C ext/osqp
  fi
  OSQP=ext/osqp
fi

[ -f c/k.h ] || curl -fsSL https://raw.githubusercontent.com/KxSystems/kdb/master/c/c/k.h -o c/k.h
make OSQP=$OSQP clean test      # the shim's own tests, no q needed
make OSQP=$OSQP                 # c/qosqp.so, which qp.q loads
echo "ready: c/qosqp.so  —  q, then \\l qp.q  and  .qp.ver[::]"
