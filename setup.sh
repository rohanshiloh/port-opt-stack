#!/bin/sh
# port-opt-stack : get OSQP, build the q shim and run its tests, from the repository root
#   ./setup.sh --mac                 macOS (Apple silicon or Intel): Apple clang, a bundle
#   ./setup.sh --linux               Linux x86-64: gcc, a shared object
#   ./setup.sh --mac --from-source   either platform, with OSQP built here by CMake (the fallback)
# With no platform flag it is taken from uname. The flag must match the machine:
# this builds for the computer it runs on, it does not cross-compile.
#
# OSQP releases:          https://github.com/osqp/osqp/releases
# OSQP C interface docs:  https://osqp.org/docs/get_started/C.html
#
# macOS needs the Xcode Command Line Tools (clang); Linux needs gcc and make
# (Debian/Ubuntu: build-essential). Both need curl and tar; CMake only for
# --from-source. Nothing is installed outside this folder: OSQP goes in ext/.
set -e
V=v1.0.0
PLAT=""; SRC=""
for a in "$@"; do
  case "$a" in
    --mac)         PLAT=mac ;;
    --linux)       PLAT=linux ;;
    --from-source) SRC=1 ;;
    *) echo "setup.sh: unknown option $a (use --mac, --linux, --from-source)"; exit 1 ;;
  esac
done
HOST=$(uname -s)
[ -n "$PLAT" ] || case "$HOST" in Darwin) PLAT=mac ;; Linux) PLAT=linux ;; *) echo "setup.sh: unsupported $HOST"; exit 1 ;; esac
case "$PLAT-$HOST" in
  mac-Darwin|linux-Linux) ;;
  *) echo "setup.sh: --$PLAT given but this machine is $HOST; run it on the machine you are building for"; exit 1 ;;
esac

case "$PLAT-$(uname -m)" in
  mac-arm64)     PKG=macos-latest;  SO=libosqp.dylib; OS=Darwin ;;
  mac-*)         PKG=macos-13;      SO=libosqp.dylib; OS=Darwin ;;   # macos-13 = Intel
  linux-x86_64)  PKG=ubuntu-latest; SO=libosqp.so;    OS=Linux ;;
  linux-*)       PKG="";            SO=libosqp.so;    OS=Linux
                 [ -n "$SRC" ] || { echo "setup.sh: no OSQP release for Linux $(uname -m); add --from-source"; exit 1; } ;;
esac
echo "setup: $PLAT ($(uname -m)), OSQP $V $([ -n "$SRC" ] && echo 'from source' || echo "release $PKG")"

if [ -n "$SRC" ]; then
  [ -d ext/osqp-src ] || git clone --depth 1 --branch $V https://github.com/osqp/osqp ext/osqp-src
  cmake -S ext/osqp-src -B ext/osqp-src/build -DCMAKE_BUILD_TYPE=Release \
        -DOSQP_BUILD_SHARED_LIB=OFF -DOSQP_BUILD_DEMO_EXE=OFF -DCMAKE_POSITION_INDEPENDENT_CODE=ON
  cmake --build ext/osqp-src/build -j
  OSQP=ext/osqp-src
else
  if [ ! -f ext/osqp/lib/$SO ]; then
    mkdir -p ext/osqp
    curl -fsSL https://github.com/osqp/osqp/releases/download/$V/osqp-$V-$PKG.tar.gz | tar xz -C ext/osqp
  fi
  OSQP=ext/osqp
fi

[ -f c/k.h ] || curl -fsSL https://raw.githubusercontent.com/KxSystems/kdb/master/c/c/k.h -o c/k.h
make OS=$OS OSQP=$OSQP clean test      # the shim's own tests, no q needed
make OS=$OS OSQP=$OSQP                 # c/qosqp.so, which qp.q loads
echo "ready: c/qosqp.so  —  q, then \\l qp.q  and  .qp.ver[::]"
