# conan-py-build

*A build backend to create Python wheels with C/C++
extensions using [Conan](https://conan.io).*

---

## Install

```bash
pip install conan-py-build
```

## Getting started

Minimal project: a Python package with a C++ extension
that uses a Conan dependency.

### Project layout

```text
mypackage/
├── pyproject.toml
├── conanfile.py
├── CMakeLists.txt
└── src/
    ├── mymodule.cpp
    └── mypackage/
        └── __init__.py
```

### `pyproject.toml`

```toml
[build-system]
requires = ["conan-py-build"]
build-backend = "conan_py_build.build"

[project]
name = "mypackage"
version = "0.1.0"
```

### `conanfile.py`

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

### `CMakeLists.txt`

The backend takes everything that `cmake --install`
produces and stages it into the wheel. For the extension
to be importable, **the `DESTINATION` in `install()` must
match your Python package name** — that is how the
compiled `.so` / `.pyd` ends up next to `__init__.py`:

```cmake
cmake_minimum_required(VERSION 3.15)
project(mypackage LANGUAGES CXX)

find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
find_package(fmt REQUIRED)

Python3_add_library(_core MODULE src/mymodule.cpp)
target_link_libraries(_core PRIVATE fmt::fmt)

install(TARGETS _core DESTINATION mypackage)
```

The resulting wheel layout:

```text
mypackage/
├── __init__.py   ← from src/mypackage/
└── _core.so      ← from install(TARGETS _core DESTINATION mypackage)
```

If `DESTINATION` doesn't match (e.g. `lib` instead of
`mypackage`), the extension lands outside the package
and `import mypackage._core` will fail.

### `src/mymodule.cpp`

This example uses the Python C API directly to keep
it dependency-free. For real projects,
[pybind11](https://pybind11.readthedocs.io/) and
[nanobind](https://nanobind.readthedocs.io/) are more
ergonomic — see [Examples](examples.md).

```cpp
#include <Python.h>
#include <fmt/core.h>
#include <string>

static PyObject* greet(PyObject* self, PyObject* args) {
    const char* name;
    if (!PyArg_ParseTuple(args, "s", &name)) return NULL;
    std::string msg = fmt::format("Hello, {}!", name);
    return PyUnicode_FromString(msg.c_str());
}

static PyMethodDef methods[] = {
    {"greet", greet, METH_VARARGS, "Greet someone."},
    {NULL, NULL, 0, NULL},
};

static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT, "mypackage._core", NULL, -1, methods,
};

PyMODINIT_FUNC PyInit__core(void) {
    return PyModule_Create(&module);
}
```

### `src/mypackage/__init__.py`

```python
from mypackage._core import greet
```

### Build and test

```bash
pip wheel . -w dist/ -vvv
pip install dist/mypackage-0.1.0-*.whl
python -c "from mypackage import greet; greet('world')"
```

---

## What's next?

| Goal | Page |
|------|------|
| All `--config-settings` and `pyproject.toml` options | **[Configuration](configuration.md)** |
| pybind11, nanobind, cibuildwheel | **[Examples](examples.md)** |
| Contributing, tests, docs | **[Development](development.md)** |
