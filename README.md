# conan-py-build

A [PEP 517](https://peps.python.org/pep-0517/) build backend that uses
[Conan](https://conan.io) to build Python C/C++ extensions.

**[Documentation](https://conan-py-build.conan.io)** ·
[PyPI](https://pypi.org/project/conan-py-build/) ·
[Examples](examples/)

## Install

```bash
pip install conan-py-build
```

## Quick start

> [!NOTE] The steps below use CMake, but the backend is build-system agnostic —
> it works with anything Conan can drive. For a Meson version, see
> [basic-meson-pybind11](examples/basic-meson-pybind11/).

1. Set `conan-py-build` as your build backend:

```toml
[build-system]
requires = ["conan-py-build"]
build-backend = "conan_py_build.build"

[project]
name = "mypackage"
version = "0.1.0"
```

2. Add a `conanfile.py` with your C++ dependencies:

```python
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout

class MyPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("fmt/12.1.0")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
```

3. Your `CMakeLists.txt` must install the extension
   into the package directory so it ends up in the wheel:

```cmake
install(TARGETS _core DESTINATION mypackage)
```

4. Build:

```bash
pip wheel . -w dist/ -vvv
```

See the [documentation](https://conan-py-build.conan.io)
for the full getting started guide, configuration, profiles,
dynamic versioning, and more.

## Examples

See the [examples/](examples/) directory:

- **[basic](examples/basic/)** — `fmt` extension, recipe via `conanfile-path`
- **[basic-pybind11](examples/basic-pybind11/)** — pybind11 + `fmt`, dynamic version, PEP 639
- **[basic-meson-pybind11](examples/basic-meson-pybind11/)** — pybind11 + `fmt` built with Meson instead of CMake
- **[basic-nanobind](examples/basic-nanobind/)** — nanobind + `fmt`, `extra-profile` for C++17
- **[external-sources](examples/external-sources/)** — pybind11, C++ dep fetched in `source()`
- **[cibw-example](examples/cibw-example/)** — pybind11 + [cibuildwheel](https://cibuildwheel.pypa.io/)

## License

MIT — see [LICENSE](LICENSE).
