# Basic Example - myadder

This example demonstrates a Python package with C++ code that uses the `fmt`
library (managed by Conan) for formatted output with colors.

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

The `examples/profiles/` directory contains Jinja profiles that use
`include(default)` and set `WHEEL_*` for wheel tags. Use the profile that
matches your OS. Set `CONAN_CPYTHON_VERSION` to the full version (e.g.
`3.12.12`) to choose Python.

```bash
export CONAN_CPYTHON_VERSION=3.12.12
pip wheel . --no-build-isolation \
    --config-settings="host-profile=../profiles/macos.jinja" \
    -w dist/
```

### Debug build (keep artifacts)

If you omit `build-dir`, the backend uses a temporary directory (removed after
the build). To keep artifacts for inspection, pass a path:

```bash
pip wheel . --no-build-isolation --config-settings="build-dir=./my-build" -w dist/ -vvv

# Inspect the directories:
ls ./my-build/build/     # CMake build tree
ls ./my-build/package/   # Wheel contents
