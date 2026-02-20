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
requires = ["conan-py-build"]
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
pip wheel . -w dist/ -vvv
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

### License files (PEP 639)

The backend supports [PEP 639](https://peps.python.org/pep-0639/) license metadata. Set `[project].license-files` in `pyproject.toml` to a list of glob patterns (e.g. `["LICENSE"]`) to include those files in the wheel under `.dist-info/licenses/` and add `License-File` entries to METADATA and to the sdist PKG-INFO. If `license-files` is not set, no license files are included.

### Wheel packages

You can control which Python packages are included in the wheel via
`[tool.conan-py-build].wheel` in `pyproject.toml`:

- **`wheel.packages`**: list of paths (relative to the project root) that are
  Python packages to include in the wheel. Each path must be a directory inside
  the project.

If `wheel.packages` is not set, the backend includes a single package at
`src/<normalized_project_name>` (e.g. `src/mypackage` for a project named
`mypackage`).

```toml
[tool.conan-py-build.wheel]
packages = ["src/mypackage", "src/other_package"]
```

### Sdist include / exclude

You can control what goes into the source distribution (sdist) via
`[tool.conan-py-build].sdist` in `pyproject.toml`:

- **`sdist.include`**: paths to add to the sdist (e.g. files in default exclude
  like `build/`, or extra dirs like `["docs/"]`).
- **`sdist.exclude`**: paths or patterns to remove from the sdist (e.g. default
  includes you don't want, like `["README.md"]`, or `["tests"]`).

By default the sdist includes `pyproject.toml`, `CMakeLists.txt`, `conanfile.py`,
`cmake/`, `src/`, `include/`, README and LICENSE, and excludes `__pycache__`,
`*.pyc`, `.git`, `build`, `dist` and the like.

```toml
[tool.conan-py-build.sdist]
include = ["docs/", "misc/"]
exclude = [".github", "scripts", "README.md"]
```

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

## Development

To try changes against a project that uses this backend (e.g. one of the
examples), install the backend in editable mode and build with no isolation so
it uses your local copy:

```bash
pip install -e .   # from the conan-py-build repo root
cd examples/basic  # or your own project
pip wheel . --no-build-isolation -w dist/
```

## Running tests

Install the build backend in editable mode with dev dependencies:

```bash
pip install -e ".[dev]"
```

Run the test suite:

```bash
pytest tests/ -v
```

## License

MIT License - see [LICENSE](LICENSE) for details.
