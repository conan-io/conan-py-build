# Basic Meson + pybind11 Example - myadder_meson_pybind11

Example of a Python package with C++ code using **pybind11** and **Meson** as
the build system. Same as `basic-pybind11` but with `MesonToolchain` +
`PkgConfigDeps` instead of `CMakeToolchain` + `CMakeDeps`.

## Build and Install

```bash
# From the repo root, install the backend first
pip install -e .

# Then build the example (requires `meson` and `ninja` in PATH)
cd examples/basic-meson-pybind11
pip wheel . --no-build-isolation -w dist/ -vvv

# Or install directly
pip install . --no-build-isolation -vvv
```

### Test the wheel

```bash
# Install the built wheel
pip install dist/myadder_meson_pybind11-*.whl

# Test it
python -c "import myadder_meson_pybind11; print(myadder_meson_pybind11.add(2, 3)); print(myadder_meson_pybind11.add_integers(10, 20)); print(myadder_meson_pybind11.greet('World'))"

# Uninstall when done
pip uninstall myadder-meson-pybind11 -y
```
