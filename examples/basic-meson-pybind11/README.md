# Basic Meson + pybind11 Example - myadder_meson_pybind11

Minimal Python extension using **pybind11** and **Meson** as the build system.

## Build and Install

```bash
# From the repo root, install the backend first
pip install -e .

# Then build the example (Conan provides meson + ninja via tool_requires)
cd examples/basic-meson-pybind11
pip wheel . --no-build-isolation -w dist/ -vvv
```

### Test the wheel

```bash
pip install dist/myadder_meson_pybind11-*.whl
python -c "import myadder_meson_pybind11; print(myadder_meson_pybind11.add(2, 3))"
pip uninstall myadder-meson-pybind11 -y
```
