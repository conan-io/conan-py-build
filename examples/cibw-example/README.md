# Example: cibuildwheel + conan-py-build

Builds a pybind11 extension that wraps **libxslt** (XSLT transforms) and links
against **libxml2** as a transitive dependency. **zlib** is also a transitive
dependency of libxml2 but is linked statically, so the wheel does not depend on
the system zlib at runtime.

This example demonstrates the full shared-library workflow:

- `libxslt` and `libxml2` are built as shared libraries and deployed to
  `.conan-libs/` by `runtime_deploy`.
- The backend patches the extension RPATH so repair tools can discover them.
- **cibuildwheel** runs the appropriate repair tool on each platform:
  - Linux: `auditwheel repair` — bundles libs into `myxslt_cibw.libs/` and
    upgrades the tag to `manylinux_2_28`.
  - macOS: `delocate-wheel` — copies dylibs next to the extension.
  - Windows: `delvewheel repair` — bundles DLLs, using `--add-path` to point
    at `.conan-libs/`.
