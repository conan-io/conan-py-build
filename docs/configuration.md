# Configuration

## Config settings (`-C`)

Passed per-invocation via
`pip wheel … -C <key>=<value>`:

| Option | Description | Default |
|--------|-------------|---------|
| `host-profile` | Conan profile for host context | `default` |
| `build-profile` | Conan profile for build context | `default` |
| `build-dir` | Persistent build directory | temp dir |

## `pyproject.toml`

All project-level options live under
`[tool.conan-py-build]`:

| Option | TOML section | Description | Default |
|--------|--------------|-------------|---------|
| `conanfile-path` | `[tool.conan-py-build]` | Path to the Conan recipe, relative to project root | `"."` |
| `extra-profile` | `[tool.conan-py-build]` | Extra Conan profile composed on top of the active one | (none) |
| `version.file` | `[tool.conan-py-build.version]` | Python file with `__version__` | (none) |
| `version.provider` | `[tool.conan-py-build.version]` | `"setuptools_scm"` for version from git tags | (none) |
| `packages` | `[tool.conan-py-build.wheel]` | Paths to Python packages in the wheel | `["src/<name>"]` |
| `include` / `exclude` | `[tool.conan-py-build.sdist]` | Glob patterns to add/remove from the sdist | `[]` / `[]` |

Variants for extra profiles: `extra-profile-host`,
`extra-profile-build`, `extra-profile-all`.
Paths relative to project root.

Default `packages` is `src/<normalized_project_name>`
(hyphens → underscores).

## Dynamic version

Set `dynamic = ["version"]` in `[project]` and pick
**one** source:

=== "From a file"

    ```toml
    [tool.conan-py-build.version]
    file = "src/mypackage/__init__.py"
    ```

=== "From git tags (setuptools-scm)"

    ```toml
    [tool.conan-py-build.version]
    provider = "setuptools_scm"
    ```

`version.file` and `version.provider` are mutually
exclusive. For setuptools-scm options see
[`[tool.setuptools_scm]`](https://setuptools-scm.readthedocs.io/).

## Profiles

```bash
export CONAN_CPYTHON_VERSION=3.12.12
pip wheel . --no-build-isolation \
    -C host-profile=examples/profiles/linux.jinja \
    -C build-dir=./build \
    -w dist/
```

An `extra-profile` in `pyproject.toml` is applied
**on top** of the active profile — useful for enforcing
e.g. `compiler.cppstd=17`:

```toml
[tool.conan-py-build]
extra-profile = "cpp17.profile"
```

## Conan home

The backend uses Conan's default home (`~/.conan2`,
or `CONAN_HOME` / `.conanrc`). Set
`CONAN_PY_BUILD_PROFILE_AUTODETECT=1` to autodetect
the profile instead of requiring `default`.

## License files (PEP 639)

Set `license-files` in `[project]`
(e.g. `["LICENSE"]`) to include license files in the
wheel `.dist-info/licenses/` and sdist PKG-INFO.

## Shared libraries

If your extension links to Conan-provided shared
libraries, the backend copies them next to the
extension after the build and patches RPATH so they
resolve at runtime:

- **macOS** — adds `@loader_path` via `install_name_tool`
- **Linux** — adds `$ORIGIN` via `patchelf`
- **Windows** — no patching needed, DLLs placed
  next to the `.pyd` are found automatically

No configuration is needed: the backend detects shared
libraries automatically from the Conan deploy output.

## Sdist defaults

Included: `pyproject.toml`, `CMakeLists.txt`,
`conanfile.py`, `cmake/`, `src/`, `include/`,
README, LICENSE.
Excluded: `__pycache__`, `*.pyc`, `.git`,
`build`, `dist`.

```toml
[tool.conan-py-build.sdist]
include = ["docs/"]
exclude = [".github", "tests"]
```
