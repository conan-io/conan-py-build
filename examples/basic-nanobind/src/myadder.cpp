#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <fmt/core.h>
#include <fmt/color.h>
#include <string>

namespace nb = nanobind;
using namespace nb::literals;

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

NB_MODULE(_core, m) {
    m.doc() = "Example Python extension using nanobind and fmt via Conan.";
    m.def("add", &add, "a"_a, "b"_a,
          "Add two numbers. Prints colored output to terminal.");
    m.def("add_integers", &add_integers, "a"_a, "b"_a,
          "Add two integers. Prints colored output to terminal.");
    m.def("greet", &greet, "name"_a,
          "Return a greeting formatted with fmt. Takes a name as argument.");
}
