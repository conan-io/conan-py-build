#include <pybind11/pybind11.h>
#include <fmt/core.h>

double add(double a, double b) {
    double result = a + b;
    fmt::print("[meson] {} + {} = {}\n", a, b, result);
    return result;
}

PYBIND11_MODULE(_core, m) {
    m.def("add", &add);
}
