# Basic pybind11 Example - myadder_pybind11

Example of a Python package with C++ code using **pybind11**.

Showcases PEP 621 features wired through the backend: dynamic
`version`, PEP 639 license files, and a [`project.scripts`][ep]
entry that installs the `myadder` CLI as a real executable.
Custom plugin-discovery groups (`[project.entry-points."…"]`)
are also supported — see the
[backend docs](https://conan-py-build.conan.io/configuration/).

[ep]: https://packaging.python.org/en/latest/specifications/entry-points/

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

# Console script installed automatically via [project.scripts]
myadder add 2 3
myadder add-int 10 20
myadder greet World

# Uninstall when done
pip uninstall myadder-pybind11 -y
```

### With custom Conan profiles

The `examples/profiles/` directory contains Jinja profiles. Use
`CONAN_CPYTHON_VERSION` to the full version (e.g. 3.12.12) to choose Python:

```bash
export CONAN_CPYTHON_VERSION=3.12.12
pip wheel . --no-build-isolation \
    --config-settings="host-profile=../profiles/macos.jinja" \
    -w dist/ -vvv
```

### Debug build (keep artifacts)

To keep build artifacts for inspection, use `build-dir`.

```bash
pip wheel . --no-build-isolation --config-settings="build-dir=./my-build" -w dist/ -vvv
```
