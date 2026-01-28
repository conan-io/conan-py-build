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
build-backend = "conan_py_build"

[project]
name = "mypackage"
version = "0.1.0"
```

2. Create a `conanfile.py` with your C++ dependencies and build logic:

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

### Profiles

Jinja profiles in `examples/profiles/`: `include(default)` + wheel tags. Set **`CONAN_CPYTHON_VERSION`** (e.g. `3.11`).

Example:

```bash
export CONAN_CPYTHON_VERSION=3.11
pip wheel . --no-build-isolation \
    --config-settings="host-profile=examples/profiles/linux.jinja" \
    --config-settings="build-dir=./build" \
    -w dist/
```

## Examples

See the [examples/](examples/) directory for complete working examples:

- **[basic](examples/basic/)**: Simple Python extension using the `fmt` library

## License

MIT License - see [LICENSE](LICENSE) for details.
