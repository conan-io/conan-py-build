# conan-py-build

> **Note:** The contents of this repository are a **proof of concept** and
> **highly experimental**. Not recommended for production use.

A minimal PEP 517 compliant build backend that uses [Conan](https://conan.io) to
build Python C/C++ extensions.

## Installation

```bash
git clone https://github.com/conan-io/conan-py-build.git
cd conan-py-build
pip install -e .
```

## Quick Start

1. Create a `pyproject.toml` for your package:

```toml
[build-system]
# TODO: Change to requires = ["conan-py-build"] once published to PyPI
# For now, install manually: pip install -e .
requires = []
build-backend = "conan_py_build.build"

[project]
name = "mypackage"
version = "0.1.0"
```

2. Create a `conanfile.py` with your C++ dependencies and build logic. Your `CMakeLists.txt` must use `install(TARGETS ... DESTINATION <package_name>)` so extensions end up in the wheel:

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
        cmake.install()
```

3. Build the wheel:

```bash
# --no-build-isolation is only needed to test while conan-py-build is not published to PyPI
pip wheel . --no-build-isolation -w dist/ -vvv
```

For a complete basic working example, see the [basic example](examples/basic/).

## Configuration

Pass configuration options via `--config-settings`:

| Option | Description | Default |
|--------|-------------|---------|
| `host-profile` | Conan profile for host context | `default` |
| `build-profile` | Conan profile for build context | `default` |
| `build-dir` | Persistent build directory | temp dir |

### Dynamic version

There is limited support for dynamic version: set `dynamic = ["version"]` in
`[project]` (no `version` key) and point to a Python file via
`[tool.conan-py-build].version-file` (e.g. `"src/mypackage/__init__.py"`). The
backend reads `__version__ = "x.y.z"` from that file.

### Profiles

Jinja profiles in `examples/profiles/`: `include(default)` + wheel tags. Set **`CONAN_CPYTHON_VERSION`** to the full version (e.g. `3.12.12`).

Example:

```bash
export CONAN_CPYTHON_VERSION=3.12.12
pip wheel . --no-build-isolation \
    --config-settings="host-profile=examples/profiles/linux.jinja" \
    --config-settings="build-dir=./build" \
    -w dist/
```

## Examples

See the [examples/](examples/) directory for complete working examples:

- **[basic](examples/basic/)**: Simple Python extension using the `fmt` library
- **[basic-pybind11](examples/basic-pybind11/)**: Python extension using pybind11 (with dynamic version from `__init__.py`)

## License

MIT License - see [LICENSE](LICENSE) for details.
