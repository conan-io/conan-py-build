# Example with a local recipe

Python bindings for [libhello](https://github.com/conan-io/libhello), a C++ library
with no recipe in ConanCenter. The project ships the recipe in `recipes/hello/`
and lists that folder in `local-recipes`:

```toml
[tool.conan-py-build]
local-recipes = ["recipes/hello"]
```

The backend exports the recipe to the Conan cache before the build, so
`self.requires("hello/0.1.0")` in `conanfile.py` resolves like any other
requirement. `hello` has no binary yet, so `conan build` builds it from source.
Its own dependency, `fmt`, comes from ConanCenter as usual.

## Build and Install

```bash
# From the repo root, install the backend first
pip install -e .

# Then build the example
cd examples/local-recipes
pip wheel . --no-build-isolation -w dist/ -vvv

# Or install directly
pip install . --no-build-isolation -vvv
```

### Test the wheel

```bash
pip install dist/hello_local-*.whl
python -c "import hello_local; hello_local.hello()"

# Uninstall when done
pip uninstall hello-local -y
```
