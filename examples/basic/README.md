# Basic Example - myadder

This example demonstrates a Python package with C++ code that uses the `fmt` library
(managed by Conan) for formatted output with colors.

## Build and Install

```bash
# From the repo root, install the backend first
pip install -e .

# Then build the example
cd examples/basic
pip wheel . --no-build-isolation -w dist/ -v

# Or install directly
pip install . --no-build-isolation -v
```

### Test the wheel

```bash
# Install the built wheel
pip install dist/myadder-*.whl

# Test it
python -c "import myadder; print(myadder.add(2, 3)); print(myadder.add_integers(10, 20))"

# Uninstall when done
pip uninstall myadder -y
```

### With custom Conan profiles

The `examples/profiles/` directory contains Jinja profiles that use `include(default)` and set `WHEEL_*` for wheel tags. Use the profile that matches your OS; set `CONAN_CPYTHON_VERSION` (e.g. `3.11`) to choose Python.

```bash
# macOS (run on a Mac)
export CONAN_CPYTHON_VERSION=3.12
pip wheel . --no-build-isolation \
    --config-settings="host-profile=../profiles/macos.jinja" \
    -w dist/
```

### Debug build (keep artifacts)

```bash
pip wheel . --no-build-isolation --config-settings="build-dir=./my-build" -w dist/ -vvv

# Inspect the directories:
ls ./my-build/build/     # CMake output, compiled .so
ls ./my-build/staging/   # What goes into the wheel
```

During the build, the backend uses:

```
(temp or ./my-build)/
├── build/                          # Conan/CMake build artifacts
│   └── build/Release/
│       ├── generators/
│       │   ├── conan_toolchain.cmake
│       │   └── fmt-config.cmake
│       ├── CMakeCache.txt
│       └── _core.cpython-3xx-xxx.so
└── staging/                        # Files packaged into the wheel
    ├── myadder/
    │   ├── __init__.py
    │   └── _core.cpython-3xx-xxx.so
    └── myadder-0.1.0.dist-info/
        ├── METADATA
        └── WHEEL
```
