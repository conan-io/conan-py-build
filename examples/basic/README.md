# Basic Example - myadder

This example demonstrates a Python package with C++ code that uses the `fmt`
library (managed by Conan) for formatted output with colors.

It also shows **`conanfile-path`** (recipe in `conan/` subdirectory).

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

A custom `host-profile` is optional: plain Linux/Windows builds work against the
default profile. macOS ships a profile (`examples/profiles/macos.jinja`) that
pins the deployment target and platform tag. The wheel is built against the
interpreter you run `pip wheel` with, so pick the Python version by using that
interpreter (a venv, or cibuildwheel per version).

```bash
# macOS: pin the deployment target / platform tag
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
ls ./my-build/conan_out/   # Conan output (build tree, generators, package)
ls ./my-build/package/     # Wheel contents (platlib)
