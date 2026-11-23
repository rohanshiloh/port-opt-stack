/* port-opt-stack : the osqp_configure.h the OSQP v1.0.0 release tarballs leave out.
 * osqp.h includes it, but the macOS and Linux releases ship only the other
 * headers and libosqp.dylib / libosqp.so. These are the defaults OSQP's CMake build uses (the same file a
 * source build generates), which is what the release binaries were built with.
 * Only OSQP_USE_LONG and OSQP_USE_FLOAT change the ABI: they set OSQPInt and
 * OSQPFloat. If the release had been built otherwise, `make test` fails on its
 * very first solve — rebuild from source with ./setup.sh --from-source. */
#ifndef OSQP_CONFIGURE_H
# define OSQP_CONFIGURE_H
# if defined(__APPLE__)
#  define IS_MAC
# elif defined(__linux__)
#  define IS_LINUX
# endif
# define OSQP_ALGEBRA_BUILTIN
# define OSQP_CODEGEN
# define OSQP_ENABLE_DERIVATIVES
# define OSQP_ENABLE_PRINTING
# define OSQP_ENABLE_PROFILING
# define OSQP_ENABLE_INTERRUPT
# define OSQP_USE_LONG           /* OSQPInt = long long: q's J, passed without a copy */
/* OSQP_USE_FLOAT undefined:    OSQPFloat = double: q's F */
#endif
