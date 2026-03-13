# Basic SCM Example - myadder_scm

This example extends the [basic](../basic) example with **dynamic versioning**
via `setuptools-scm`. Instead of a hard-coded `version` in `pyproject.toml`,
the version is resolved automatically from Git tags.

It demonstrates every `setuptools-scm` option supported by the backend:

| Option | Value in this example | What it does |
|--------|----------------------|--------------|
| `version_scheme` | `"guess-next-dev"` | Constructs the version string between tags (e.g. `1.0.0.dev3+gabcdef`). |
| `local_scheme` | `"no-local-version"` | Strips the `+gHASH` local suffix — required for PyPI uploads. |
| `fallback_version` | `"0.0.0"` | Used when Git metadata is unavailable (e.g. building from a tarball). |
| `root` | `"."` | Path to the SCM root relative to `pyproject.toml`. Change to `".."` in a monorepo. |
| `write_to` | `"src/myadder_scm/_version.py"` | Includes the generated `_version.py` in the sdist so downstream builds without `.git` still have a version. |

## Key differences from `basic`

| | `basic` | `basic-scm` |
|--|---------|-------------|
| Version source | `version = "0.1.0"` (static) | `dynamic = ["version"]` + Git tags |
| Build requires | `conan-py-build` | `conan-py-build` + `setuptools-scm` |
| `__init__.py` | `__version__ = "0.1.0"` | Imports from `_version.py` with `"0.0.0"` fallback |
| SCM config | (none) | `[tool.setuptools_scm]` + `[tool.version.setuptools_scm]` |

## pyproject.toml highlights

```toml
[build-system]
requires = ["conan-py-build", "setuptools-scm"]
build-backend = "conan_py_build.build"

[project]
name = "myadder_scm"
dynamic = ["version"]            # no static version key

[tool.conan-py-build]
conanfile-path = "conan"
version = "setuptools_scm"       # tells the backend to use setuptools-scm

[tool.setuptools_scm]
version_scheme = "guess-next-dev"
local_scheme = "no-local-version"
fallback_version = "0.0.0"
root = "."

[tool.version.setuptools_scm]
write_to = "src/myadder_scm/_version.py"
```

## Build and Install

```bash
# From the repo root, install the backend first
pip install -e .

# Create a git tag so setuptools-scm can resolve a version
cd examples/basic-scm
git tag v1.0.0

# Build the wheel
pip wheel . --no-build-isolation -w dist/ -v

# Or install directly
pip install . --no-build-isolation -v
```

### Test the wheel

```bash
pip install dist/myadder_scm-*.whl

python -c "import myadder_scm; print(myadder_scm.__version__); print(myadder_scm.add(2, 3))"

pip uninstall myadder_scm -y
```

### Building without Git (fallback version)

If you build from a source tarball without `.git`, `setuptools-scm` cannot
resolve the version. Thanks to `fallback_version = "0.0.0"`, the build still
succeeds instead of raising an error.

### Monorepo layout

If the project lives inside a subdirectory of a larger repository, change
`root` to point to the Git root:

```toml
[tool.setuptools_scm]
root = ".."
```
