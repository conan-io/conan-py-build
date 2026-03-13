#include <pybind11/pybind11.h>
#include <fmt/core.h>
#include <fmt/color.h>
#include <string>

namespace py = pybind11;

double add(double a, double b) {
    double result = a + b;
    fmt::print(fg(fmt::color::green) | fmt::emphasis::bold,
               "{} + {} = {}\n", a, b, result);
    return result;
}

long add_integers(long a, long b) {
    long result = a + b;
    fmt::print(fg(fmt::color::cyan) | fmt::emphasis::bold,
               "(integers) {} + {} = {}\n", a, b, result);
    return result;
}

std::string greet(const std::string& name) {
    std::string greeting = "Hello, " + name + "! Formatted with fmt.";
    fmt::print(fg(fmt::color::yellow) | fmt::emphasis::italic,
               "{}\n", greeting);
    return greeting;
}

PYBIND11_MODULE(_core, m) {
    m.doc() = "Example Python extension using fmt via Conan.";
    m.def("add", &add, "Add two numbers. Prints colored output to terminal.",
          py::arg("a"), py::arg("b"));
    m.def("add_integers", &add_integers, "Add two integers. Prints colored output to terminal.",
          py::arg("a"), py::arg("b"));
    m.def("greet", &greet, "Return a greeting formatted with fmt. Takes a name as argument.",
          py::arg("name"));
}
