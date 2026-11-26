# port-opt-stack : build the OSQP shim for q, on macOS (clang) or Linux (gcc). Run ./setup.sh first.
# Two ways to get OSQP, chosen by what ./setup.sh put in $(OSQP):
#   the release (default)  ext/osqp/lib/libosqp.dylib + include/, plus c/osqp_configure.h
#   --from-source          ext/osqp-src/build/out/libosqpstatic.a, linked into the shim
OSQP ?= ext/osqp
# Darwin or Linux: ./setup.sh --mac or --linux sets it, otherwise uname decides
OS ?= $(shell uname -s)
ifeq ($(OS),Darwin)
  # Apple clang from the Command Line Tools; Homebrew's gcc is not needed
  CC     = clang
  CFLAGS = -O2 -Wall -Wno-unused-parameter -arch $(shell uname -m)
  # a bundle, with the k symbols left for q to supply at load
  SOFLAGS= -bundle -undefined dynamic_lookup
  ORIGIN = @loader_path
else
  # Linux: gcc; a shared object may leave the k symbols undefined by default
  CC     = gcc
  CFLAGS = -O2 -Wall -Wno-unused-parameter -fPIC
  SOFLAGS= -shared
  ORIGIN = $$ORIGIN
endif

ifneq ($(wildcard $(OSQP)/build/out/libosqpstatic.a),)
  INC   = -I$(OSQP)/include/public -I$(OSQP)/build/include/public -Ic
  LIB   = $(OSQP)/build/out/libosqpstatic.a
  RPATH =
else
  # c/osqp_configure.h fills the release's gap; the .so finds libosqp in ext/
  INC   = -I$(OSQP)/include -Ic
  LIB   = -L$(OSQP)/lib -losqp
  RPATH = -Wl,-rpath,'$(ORIGIN)/../$(OSQP)/lib'
endif
comma := ,
TRPATH = $(if $(RPATH),-Wl$(comma)-rpath$(comma)$(CURDIR)/$(OSQP)/lib)

# q supplies the k symbols when it loads the library
c/qosqp.so: c/qosqp.c c/k.h
	$(CC) $(CFLAGS) $(INC) c/qosqp.c $(LIB) $(RPATH) $(SOFLAGS) -o $@

# the shim's own tests, with no q process: c/test/kmock.c stands in for the runtime
test: c/qosqp.so
	$(CC) $(CFLAGS) $(INC) c/test/test.c c/qosqp.c c/test/kmock.c $(LIB) $(TRPATH) -o c/test/qtest
	./c/test/qtest

bench:
	$(CC) $(CFLAGS) $(INC) c/test/bench.c c/qosqp.c c/test/kmock.c $(LIB) $(TRPATH) -o c/test/qbench

clean:
	rm -f c/qosqp.so c/test/qtest c/test/qbench
.PHONY: test bench clean
