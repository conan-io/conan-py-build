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
| `extra-arguments` | `[tool.conan-py-build]` | Extra Conan CLI flags appended to `conan build` and `conan export-pkg` | `[]` |
| `version.file` | `[tool.conan-py-build.version]` | Python file with `__version__` | (none) |
| `version.provider` | `[tool.conan-py-build.version]` | `"setuptools_scm"` for version from git tags | (none) |
| `packages` | `[tool.conan-py-build.wheel]` | Paths to Python packages in the wheel | `["src/<name>"]` |
| `include` / `exclude` | `[tool.conan-py-build.sdist]` | Glob patterns to add/remove from the sdist | `[]` / `[]` |

Variants for extra profiles: `extra-profile-host`,
`extra-profile-build`, `extra-profile-all`.
Paths relative to project root.

For one-off Conan overrides without shipping a separate
profile file, use `extra-arguments` (see *Extra Conan
arguments* below).

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

### Wheel tags (`WHEEL_PYVER`, `WHEEL_ABI`, `WHEEL_ARCH`)

By default the backend reads the wheel filename tags
(interpreter, ABI, platform) from the running Python
interpreter. When you build against a **portable
CPython** (via the `cpython-portable` Conan recipe) or
cross-compile, set these three variables in the profile's
`[buildenv]` to override them:

| Variable | Wheel tag | Example |
|----------|-----------|---------|
| `WHEEL_PYVER` | Interpreter | `cp312`, `py3` |
| `WHEEL_ABI` | ABI | `cp312`, `abi3`, `none` |
| `WHEEL_ARCH` | Platform | `manylinux_2_28_x86_64`, `macosx_11_0_arm64`, `win_amd64` |

Each variable independently overrides its auto-detected
value. Auto-detection always runs from the current
interpreter. Any variable that is set replaces only its
corresponding tag.

A typical Jinja profile sets all three from
`CONAN_CPYTHON_VERSION`:

```jinja
{% set py_ver = os.environ["CONAN_CPYTHON_VERSION"] %}
{% set py_tag = "cp" + "".join(py_ver.split(".")[:2]) %}

[buildenv]
WHEEL_PYVER={{ py_tag }}
WHEEL_ABI={{ py_tag }}
WHEEL_ARCH=manylinux_2_28_x86_64
```

The resulting wheel filename will be, for example,
`mypackage-0.1.0-cp312-cp312-manylinux_2_28_x86_64.whl`.
Working examples for Linux, macOS and Windows live under
[`examples/profiles/`](https://github.com/conan-io/conan-py-build/tree/main/examples/profiles).

## Conan home

The backend uses Conan's default home (`~/.conan2`,
or `CONAN_HOME` / `.conanrc`). Set
`CONAN_PY_BUILD_PROFILE_AUTODETECT=1` to autodetect
the profile instead of requiring `default`.

## Extra Conan arguments

CLI flags appended to `conan build` and
`conan export-pkg`. Symmetric with `extra-profile`,
with higher precedence — CLI flags win against any
profile entry.

Bump `compiler.cppstd` to match a transitive dep
(e.g. `gdal/3.12.1` requires C++17, MSVC defaults
to 14):

```toml
[tool.conan-py-build]
extra-arguments = ["-s=compiler.cppstd=17"]
```

Disable an optional dep feature and pin parallelism:

```toml
[tool.conan-py-build]
extra-arguments = [
    "-o=gdal/*:with_arrow=False",
    "-c=tools.build:jobs=4",
]
```

For values with embedded double quotes (dict / list
`[conf]` literals), use TOML literal strings (`'...'`):

```toml
extra-arguments = [
    '-c=tools.build:cflags+=["-O2", "-fPIC"]',
    '-c=tools.cmake.cmaketoolchain:extra_variables={"FOO": "bar"}',
]
```

Any Conan CLI flag works: `-s` / `-o` / `-c` (host),
`-s:b` / `-o:b` / `-c:b` (build context),
`--build=...`, `--lockfile=...`. Pair-form
(`["-s", "compiler.cppstd=17"]`) is also accepted.

## Entry points (PEP 621)

`[project.scripts]`, `[project.gui-scripts]` and
`[project.entry-points.*]` from `pyproject.toml` are
written to `<pkg>.dist-info/entry_points.txt` in the
wheel, per the PyPA
[entry points specification](https://packaging.python.org/en/latest/specifications/entry-points/).
Installers create the corresponding console/GUI
wrappers at install time; runtime tools like
`importlib.metadata.entry_points()` read them
from this file.

```toml
[project.scripts]
mycli = "mypackage.cli:main"

[project.gui-scripts]
mygui = "mypackage.gui:run"

[project.entry-points."myplugin.hooks"]
on_event = "mypackage.hooks:on_event"
```

The file is only written when at least one entry
point is declared.

## License files (PEP 639)

Set `license-files` in `[project]`
(e.g. `["LICENSE"]`) to include license files in the
wheel `.dist-info/licenses/` and sdist PKG-INFO.

## Shared libraries

When your extension links to Conan-provided shared libraries, the backend:

1. Deploys them to a `.conan-libs/` directory next to the wheel.
2. Patches the extension RPATH so that repair tools can discover and bundle
   those libraries.

> **Important:** when Conan shared libraries are deployed, the wheel returned by
> `build_wheel()` is **an intermediate artifact**. It contains an absolute RPATH
> pointing to the `.conan-libs/` build directory but does not bundle the
> libraries themselves. Installing this wheel locally may appear to work as long
> as `.conan-libs/` still exists on disk, but will fail with `ImportError` on
> any other machine or after the build directory is removed. Always run a repair
> step before installing or distributing.

Run the appropriate repair tool after building:

- **Linux** — [`auditwheel repair`](https://github.com/pypa/auditwheel)
- **macOS** — [`delocate-wheel`](https://github.com/matthew-brett/delocate)
- **Windows** — [`delvewheel repair`](https://github.com/adang1345/delvewheel)

[`cibuildwheel`](https://cibuildwheel.pypa.io/) runs the right tool
automatically on Linux and macOS. On Windows, add this to your `pyproject.toml`:

```toml
[tool.cibuildwheel.windows]
before-all = "pip install delvewheel"
repair-wheel-command = 'delvewheel repair --add-path "{wheel}/../.conan-libs" -w "{dest_dir}" "{wheel}"'
```

The `.conan-libs/` directory is a build artifact and can be deleted after the
repair step completes.

Static-only builds are unaffected: when no Conan shared libraries are deployed
the backend is a no-op and the wheel is self-contained.

### System libraries and ABI risk

Each repair tool excludes libraries it considers part of the host system and
does not bundle them into the wheel:

- **auditwheel (Linux)** uses an explicit [allowlist of named
  libraries](https://github.com/pypa/auditwheel/blob/main/src/auditwheel/policy/manylinux-policy.json)
  guaranteed on manylinux systems (e.g. `libz.so.1`, `libstdc++.so.6`,
  `libm.so.6`).
- **delocate (macOS)** [excludes any
  library](https://github.com/matthew-brett/delocate/blob/master/delocate/libsana.py#L36-L37)
  whose install name starts with `/usr/lib/` or `/System/Library/` (e.g.
  `/usr/lib/libz.dylib`).
- **delvewheel (Windows)** maintains a [list of known Windows
  DLLs](https://github.com/adang1345/delvewheel/blob/master/delvewheel/_dll_list.py)
  (e.g. `kernel32.dll`, `user32.dll`) that are assumed present on all supported
  Windows versions.

When an excluded library is found in `.conan-libs/`, the repair tool skips it
and the wheel loads it from the target system at runtime instead.

This means that if you build against a Conan-provided version of a system
library (e.g. `zlib/1.3.2` with `shared=True`), the wheel will silently use the
system zlib at runtime. If the system version is older and lacks a symbol your
code depends on, the import will fail with `undefined symbol`, a bug that passes
repair tools undetected.

If your code uses symbols that exist in the Conan-provided version but not in
the system version on your target machines, the import will fail at runtime
despite the wheel passing the repair step. Linking that library statically
removes the dependency on the system version. You can inspect which symbols your
code requires with `nm -D` (Linux/macOS) or `dumpbin /exports` (Windows).

## Sdist defaults

Included: `pyproject.toml`, `conanfile.py`, your build
system's top-level file (`CMakeLists.txt`,
`meson.build`), `cmake/`, `src/`, `include/`,
README, LICENSE.
Excluded: `__pycache__`, `*.pyc`, `.git`,
`build`, `dist`.

```toml
[tool.conan-py-build.sdist]
include = ["docs/"]
exclude = [".github", "tests"]
```
