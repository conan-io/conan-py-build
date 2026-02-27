# Basic nanobind Example - myadder_nanobind

Example of a Python package with C++ code using **nanobind** (from Conan Center) and **fmt**.

## Build and Install

```bash
# From the repo root, install the backend first
pip install -e .

# Then build the example
cd examples/basic-nanobind
pip wheel . --no-build-isolation -w dist/ -vvv

# Or install directly
pip install . --no-build-isolation -vvv
```

### Test the wheel

```bash
# Install the built wheel
pip install dist/myadder_nanobind-*.whl

# Test it
python -c "import myadder_nanobind; print(myadder_nanobind.add(2, 3)); print(myadder_nanobind.add_integers(10, 20)); print(myadder_nanobind.greet('World'))"

# Uninstall when done
pip uninstall myadder-nanobind -y
```
