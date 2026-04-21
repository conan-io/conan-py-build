# Examples

Complete working projects under
[`examples/`](https://github.com/conan-io/conan-py-build/tree/main/examples):

| Example | What it shows |
|---------|---------------|
| [basic](https://github.com/conan-io/conan-py-build/tree/main/examples/basic) | `fmt` extension, recipe via `conanfile-path` |
| [basic-pybind11](https://github.com/conan-io/conan-py-build/tree/main/examples/basic-pybind11) | pybind11 + `fmt`, dynamic version, custom `wheel.packages`, PEP 639 |
| [basic-meson-pybind11](https://github.com/conan-io/conan-py-build/tree/main/examples/basic-meson-pybind11) | pybind11 + `fmt` built with Meson |
| [basic-nanobind](https://github.com/conan-io/conan-py-build/tree/main/examples/basic-nanobind) | nanobind + `fmt`, `extra-profile` for C++17 |
| [external-sources](https://github.com/conan-io/conan-py-build/tree/main/examples/external-sources) | pybind11, C++ dependency fetched in `source()` |
| [cibw-example](https://github.com/conan-io/conan-py-build/tree/main/examples/cibw-example) | pybind11 + [cibuildwheel](https://cibuildwheel.pypa.io/) cross-platform CI |
