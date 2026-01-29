# Basic pybind11 Example - myadder_pybind11

Example of a Python package with C++ code using **pybind11**.

## Build and Install

```bash
# From the repo root, install the backend first
pip install -e .

# Then build the example
cd examples/basic-pybind11
pip wheel . --no-build-isolation -w dist/ -vvv

# Or install directly
pip install . --no-build-isolation -vvv
```

### Test the wheel

```bash
# Install the built wheel
pip install dist/myadder_pybind11-*.whl

# Test it
python -c "import myadder_pybind11; print(myadder_pybind11.add(2, 3)); print(myadder_pybind11.add_integers(10, 20)); print(myadder_pybind11.greet('World'))"

# Uninstall when done
pip uninstall myadder-pybind11 -y
```

### With custom Conan profiles

The `examples/profiles/` directory contains Jinja profiles. Use
`CONAN_CPYTHON_VERSION` to choose the Python version:

```bash
export CONAN_CPYTHON_VERSION=3.12
pip wheel . --no-build-isolation \
    --config-settings="host-profile=../profiles/macos.jinja" \
    -w dist/ -vvv
```
