# Example with external sources

Example where the **C++ code is fetched in `source()`** from an external repo
([libhello](https://github.com/conan-io/libhello)).

## Build and Install

```bash
# From the repo root, install the backend first
pip install -e .

# Then build the example
cd examples/external-sources
pip wheel . --no-build-isolation -w dist/ -vvv

# Or install directly
pip install . --no-build-isolation -vvv
```

### Test the wheel

```bash
pip install dist/hello_bindings-*.whl
python -c "import hello_bindings; hello_bindings.hello()"

# Uninstall when done
pip uninstall hello-bindings -y
```
