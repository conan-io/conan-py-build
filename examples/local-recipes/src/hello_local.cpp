#include <pybind11/pybind11.h>
#include <hello.h>

PYBIND11_MODULE(_core, m) {
    m.doc() = "Python bindings for libhello, built from a Conan recipe shipped with the project";
    m.def("hello", &hello, "Call libhello's hello(), which prints a greeting and build info with fmt.");
}
