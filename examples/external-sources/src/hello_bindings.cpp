#include <pybind11/pybind11.h>
#include "hello.h"

namespace py = pybind11;

PYBIND11_MODULE(_core, m) {
    m.doc() = "Python bindings for libhello (C++ library from https://github.com/conan-io/libhello)";
    m.def("hello", &hello, "Call the libhello hello() function (prints Hello World and build info).");
}
