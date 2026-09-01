"""Integration tests: run real PEP 517 hooks (build_sdist, build_wheel) on a project layout."""
import os
import subprocess
import sys
import tarfile
import types
import zipfile
from pathlib import Path

import pytest

from conan_py_build.build import build_sdist, build_wheel, prepare_metadata_for_build_wheel


_DEFAULT_PYPROJECT = """\
[project]
name = "integration-pkg"
version = "0.1.0"
description = "For integration tests"
license-files = ["LICENSE"]

[build-system]
requires = ["conan-py-build"]
build-backend = "conan_py_build.build"
"""

_DEFAULT_CONANFILE = """\
from conan import ConanFile
from conan.tools.cmake import cmake_layout


class Pkg(ConanFile):
    name = "integration_pkg"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def layout(self):
        cmake_layout(self)

    def source(self):
        self.output.info("source_called")

    def build(self):
        pass
"""


def make_integration_project(
    path: Path,
    *,
    pyproject_toml: str = _DEFAULT_PYPROJECT,
    conanfile: str = _DEFAULT_CONANFILE,
    pkg_name: str = "integration_pkg",
    init_content: str = "",
    license_text: str = "MIT",
) -> None:
    """Create a minimal conan-py-build project."""
    path.mkdir(exist_ok=True)
    (path / "pyproject.toml").write_text(pyproject_toml, encoding="utf-8")
    (path / "conanfile.py").write_text(conanfile, encoding="utf-8")
    (path / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.15)\nproject(x)\n", encoding="utf-8"
    )
    if license_text:
        (path / "LICENSE").write_text(license_text, encoding="utf-8")
    pkg = path / "src" / pkg_name
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text(init_content, encoding="utf-8")


@pytest.fixture
def integration_project(tmp_path, monkeypatch):
    """Create a minimal project in tmp_path and chdir into it."""
    dest = tmp_path / "proj"
    dest.mkdir()
    make_integration_project(dest)
    monkeypatch.chdir(dest)
    conan_home = tmp_path / "conan_home"
    monkeypatch.setenv("CONAN_HOME", str(conan_home))
    return types.SimpleNamespace(work_dir=tmp_path, project_dir=dest)


def test_build_sdist_produces_tarball(integration_project):
    """Integration: build_sdist on a real project layout produces a valid sdist tarball."""
    sdist_dir = integration_project.work_dir / "dist"
    sdist_dir.mkdir()
    filename = build_sdist(str(sdist_dir), config_settings=None)

    assert filename == "integration_pkg-0.1.0.tar.gz"
    tarball = sdist_dir / filename
    assert tarball.is_file()

    with tarfile.open(tarball, "r:gz") as tar:
        names = sorted(tar.getnames())
        expected = sorted([
            "integration_pkg-0.1.0/CMakeLists.txt",
            "integration_pkg-0.1.0/LICENSE",
            "integration_pkg-0.1.0/PKG-INFO",
            "integration_pkg-0.1.0/conanfile.py",
            "integration_pkg-0.1.0/pyproject.toml",
            "integration_pkg-0.1.0/src/integration_pkg/__init__.py",
        ])
        assert names == expected
        pkg_info = tar.extractfile("integration_pkg-0.1.0/PKG-INFO").read().decode("utf-8")
        assert "License-File: LICENSE" in pkg_info
        # PEP 625 normalizes the file and directory names above, not the metadata.
        assert "Name: integration-pkg" in pkg_info


def test_build_wheel_includes_license_in_dist_info(integration_project):
    """Integration: wheel contains .dist-info/licenses/LICENSE and METADATA lists License-File."""
    dist_dir = integration_project.work_dir / "dist"
    dist_dir.mkdir()
    build_wheel(str(dist_dir), config_settings=None)

    (wheel_path,) = dist_dir.glob("integration_pkg-0.1.0-*.whl")
    with zipfile.ZipFile(wheel_path) as zf:
        names = zf.namelist()
        assert any(n.endswith(".dist-info/licenses/LICENSE") for n in names)
        (metadata_name,) = [n for n in names if n.endswith(".dist-info/METADATA")]
        assert "License-File: LICENSE" in zf.read(metadata_name).decode("utf-8")


def test_sdist_pkg_info_and_wheel_metadata_identical(integration_project):
    """Integration: PKG-INFO (sdist) and METADATA (wheel) are the same core metadata."""
    dist_dir = integration_project.work_dir / "dist"
    dist_dir.mkdir()
    build_sdist(str(dist_dir), config_settings=None)
    build_wheel(str(dist_dir), config_settings=None)

    with tarfile.open(dist_dir / "integration_pkg-0.1.0.tar.gz", "r:gz") as tar:
        pkg_info = tar.extractfile("integration_pkg-0.1.0/PKG-INFO").read().decode("utf-8")

    (wheel_path,) = dist_dir.glob("integration_pkg-0.1.0-*.whl")
    with zipfile.ZipFile(wheel_path) as zf:
        (metadata_name,) = [n for n in zf.namelist() if n.endswith(".dist-info/METADATA")]
        wheel_metadata = zf.read(metadata_name).decode("utf-8")

    assert pkg_info.strip() == wheel_metadata.strip(), "PKG-INFO and METADATA must be the same core metadata"


def test_prepare_metadata_matches_wheel_metadata(integration_project):
    """Integration: METADATA from prepare_metadata_for_build_wheel matches the METADATA in the final wheel."""
    meta_dir = integration_project.work_dir / "meta"
    meta_dir.mkdir()
    dist_info_name = prepare_metadata_for_build_wheel(str(meta_dir))
    prepared = (meta_dir / dist_info_name / "METADATA").read_text(encoding="utf-8")

    wheel_dir = integration_project.work_dir / "dist"
    wheel_dir.mkdir()
    wheel_name = build_wheel(str(wheel_dir))

    with zipfile.ZipFile(wheel_dir / wheel_name) as zf:
        (entry,) = [n for n in zf.namelist() if n.endswith(".dist-info/METADATA")]
        built = zf.read(entry).decode("utf-8")

    assert prepared.strip() == built.strip()


def test_build_wheel_integration(integration_project, capfd):
    """Integration: build_wheel on a real project."""
    wheel_dir = integration_project.work_dir / "wheelhouse"
    wheel_dir.mkdir()
    name = build_wheel(str(wheel_dir), config_settings=None)
    assert name.endswith(".whl")
    assert (wheel_dir / name).is_file()
    _, err = capfd.readouterr()
    assert "source_called" in err


def test_build_wheel_injects_python_executable_for_cmake(integration_project, capfd):
    """CMakeToolchain gets Python3_EXECUTABLE/Python_EXECUTABLE = sys.executable."""
    _CONANFILE = """\
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Pkg(ConanFile):
    name = "integration_pkg"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
"""
    (integration_project.project_dir / "conanfile.py").write_text(_CONANFILE, encoding="utf-8")
    (integration_project.project_dir / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.15)\n"
        "project(x)\n"
        'message(STATUS "PY3=${Python3_EXECUTABLE}")\n'
        'message(STATUS "PY=${Python_EXECUTABLE}")\n',
        encoding="utf-8",
    )

    wheel_dir = integration_project.work_dir / "dist"
    wheel_dir.mkdir()
    build_wheel(str(wheel_dir), config_settings=None)

    output = "".join(capfd.readouterr())
    assert f"PY3={sys.executable}" in output
    assert f"PY={sys.executable}" in output


def test_wheel_does_not_contain_conan_output(integration_project):
    """Conan's output folder (build tree, generators) must not leak into the wheel platlib."""
    dist_dir = integration_project.work_dir / "dist"
    dist_dir.mkdir()
    build_wheel(str(dist_dir), config_settings=None)

    (wheel_path,) = dist_dir.glob("integration_pkg-0.1.0-*.whl")
    with zipfile.ZipFile(wheel_path) as zf:
        names = zf.namelist()

    leaked = [n for n in names if n.startswith(("build/", "conan_out/", "CMakeFiles/"))]
    assert not leaked, f"Conan output leaked into wheel: {leaked}"


def test_build_wheel_uses_metadata_directory(integration_project):
    """build_wheel copies pre-built dist-info when metadata_directory is provided (PEP 517 contract)."""
    meta_dir = integration_project.work_dir / "meta"
    meta_dir.mkdir()
    dist_info_name = prepare_metadata_for_build_wheel(str(meta_dir))
    dist_info_path = meta_dir / dist_info_name
    # Simulate a frontend adding an extra entry to the pre-built dist-info
    (dist_info_path / "extra.txt").write_text("sentinel")

    wheel_dir = integration_project.work_dir / "dist"
    wheel_dir.mkdir()
    # Pass the .dist-info path directly (spec-correct form)
    wheel_name = build_wheel(str(wheel_dir), metadata_directory=str(dist_info_path))

    with zipfile.ZipFile(wheel_dir / wheel_name) as zf:
        names = zf.namelist()
        assert any(n.endswith(".dist-info/extra.txt") for n in names), \
            "Extra file from metadata_directory must be preserved in the wheel"
        (entry,) = [n for n in names if n.endswith(".dist-info/METADATA")]
        prepared = (dist_info_path / "METADATA").read_text(encoding="utf-8")
        assert prepared.strip() == zf.read(entry).decode("utf-8").strip()


def test_build_wheel_with_profile_autodetect(integration_project, monkeypatch):
    """With CONAN_PY_BUILD_PROFILE_AUTODETECT=1 a local profile is created; by default Conan default is used."""
    profile_path = integration_project.project_dir / "conan-py-build.profile"
    wheel_dir = integration_project.work_dir / "dist"
    wheel_dir.mkdir()

    monkeypatch.delenv("CONAN_PY_BUILD_PROFILE_AUTODETECT", raising=False)
    build_wheel(str(wheel_dir), config_settings=None)
    assert not profile_path.exists(), "conan-py-build.profile must not be created when using Conan default"

    monkeypatch.setenv("CONAN_PY_BUILD_PROFILE_AUTODETECT", "1")
    build_wheel(str(wheel_dir), config_settings=None)
    assert profile_path.is_file(), "conan-py-build.profile should be created when autodetect is set"
    content = profile_path.read_text()
    assert "[settings]" in content or "os=" in content, "Profile should contain Conan settings"


def test_generate_can_modify_python_package(integration_project):
    """generate() modifications to __init__.py are reflected in the wheel, not the placeholder."""
    _CONANFILE = """\
from conan import ConanFile
from pathlib import Path


class Pkg(ConanFile):
    name = "integration_pkg"

    def generate(self):
        init = Path(self.source_folder) / "src" / "integration_pkg" / "__init__.py"
        init.write_text("GENERATED = True\\n")

    def build(self):
        pass
"""
    (integration_project.project_dir / "conanfile.py").write_text(_CONANFILE)
    (integration_project.project_dir / "src" / "integration_pkg" / "__init__.py").write_text("# placeholder\n")

    wheel_dir = integration_project.work_dir / "dist"
    wheel_dir.mkdir()
    wheel_name = build_wheel(str(wheel_dir), config_settings=None)

    with zipfile.ZipFile(wheel_dir / wheel_name) as zf:
        init = zf.read("integration_pkg/__init__.py").decode("utf-8")

    assert "GENERATED = True" in init
    assert "placeholder" not in init


def test_wheel_exclude_drops_files_from_wheel(tmp_path, monkeypatch):
    """wheel.exclude patterns must not end up in the wheel; other package files must survive."""
    _PYPROJECT = """\
[project]
name = "integration-pkg"
version = "0.1.0"
description = "For integration tests"
license-files = ["LICENSE"]

[build-system]
requires = ["conan-py-build"]
build-backend = "conan_py_build.build"

[tool.conan-py-build.wheel]
exclude = ["binding/*.h", "binding/*.cpp"]
"""
    proj = tmp_path / "proj"
    make_integration_project(proj, pyproject_toml=_PYPROJECT)
    # Add build-time artifacts inside the package — these should be excluded.
    binding_dir = proj / "src" / "integration_pkg" / "binding"
    binding_dir.mkdir()
    (binding_dir / "types.h").write_text("#pragma once\n", encoding="utf-8")
    (binding_dir / "core.cpp").write_text("// binding source\n", encoding="utf-8")

    monkeypatch.chdir(proj)
    monkeypatch.setenv("CONAN_HOME", str(tmp_path / "conan_home"))

    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    build_wheel(str(dist_dir), config_settings=None)

    (wheel_path,) = dist_dir.glob("integration_pkg-0.1.0-*.whl")
    with zipfile.ZipFile(wheel_path) as zf:
        names = zf.namelist()

    assert "integration_pkg/__init__.py" in names, "package __init__.py must still be present"
    excluded = [n for n in names if n.startswith("integration_pkg/binding/")]
    assert not excluded, f"build-time artifacts must not appear in wheel: {excluded}"


def test_wheel_without_exclude_includes_binding_files(tmp_path, monkeypatch):
    """Baseline: without wheel.exclude, files inside the package directory end up in the wheel."""
    proj = tmp_path / "proj"
    make_integration_project(proj)
    binding_dir = proj / "src" / "integration_pkg" / "binding"
    binding_dir.mkdir()
    (binding_dir / "types.h").write_text("#pragma once\n", encoding="utf-8")

    monkeypatch.chdir(proj)
    monkeypatch.setenv("CONAN_HOME", str(tmp_path / "conan_home"))

    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    build_wheel(str(dist_dir), config_settings=None)

    (wheel_path,) = dist_dir.glob("integration_pkg-0.1.0-*.whl")
    with zipfile.ZipFile(wheel_path) as zf:
        names = zf.namelist()

    assert "integration_pkg/binding/types.h" in names, \
        "without wheel.exclude, files inside the package must be copied into the wheel"


def _git_init_and_tag(cwd, tag):
    """Initialise a throw-away git repo, commit everything and create *tag*."""
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    for cmd in (
        ["git", "init"],
        ["git", "add", "."],
        ["git", "commit", "-m", "init"],
        ["git", "tag", tag],
    ):
        subprocess.run(cmd, cwd=cwd, check=True, env=env, capture_output=True)


def test_build_sdist_version_file(tmp_path, monkeypatch):
    """Integration: build_sdist resolves dynamic version from [tool.conan-py-build.version].file."""
    proj = tmp_path / "proj"
    make_integration_project(proj, pkg_name="file_pkg", pyproject_toml="""\
[project]
name = "file-pkg"
dynamic = ["version"]
description = "Test"

[build-system]
requires = ["conan-py-build"]
build-backend = "conan_py_build.build"

[tool.conan-py-build.version]
file = "src/file_pkg/__init__.py"
""", init_content='__version__ = "2.3.4"')
    monkeypatch.chdir(proj)
    monkeypatch.setenv("CONAN_HOME", str(tmp_path / "conan_home"))

    sdist_dir = tmp_path / "dist"
    sdist_dir.mkdir()
    assert build_sdist(str(sdist_dir)) == "file_pkg-2.3.4.tar.gz"



def test_build_sdist_version_scm(tmp_path, monkeypatch):
    """Integration: build_sdist resolves dynamic version from setuptools_scm (git tag)."""
    proj = tmp_path / "proj"
    make_integration_project(proj, pkg_name="scm_pkg", pyproject_toml="""\
[project]
name = "scm-pkg"
dynamic = ["version"]
description = "Test"

[build-system]
requires = ["conan-py-build"]
build-backend = "conan_py_build.build"

[tool.conan-py-build.version]
provider = "setuptools_scm"

[tool.setuptools_scm]
version_file = "src/scm_pkg/_version.py"
""")
    _git_init_and_tag(proj, "v3.0.0")
    monkeypatch.chdir(proj)
    monkeypatch.setenv("CONAN_HOME", str(tmp_path / "conan_home"))

    sdist_dir = tmp_path / "dist"
    sdist_dir.mkdir()
    filename = build_sdist(str(sdist_dir))
    assert filename == "scm_pkg-3.0.0.tar.gz"

    with tarfile.open(sdist_dir / filename, "r:gz") as tar:
        names = tar.getnames()
        assert "scm_pkg-3.0.0/src/scm_pkg/_version.py" in names


def test_build_sdist_exclude_applies_to_top_level_files(tmp_path, monkeypatch):
    """Integration: sdist.exclude drops top-level files, not only files found
    inside the included directories."""
    proj = tmp_path / "proj"
    make_integration_project(proj, pyproject_toml=_DEFAULT_PYPROJECT + """
[tool.conan-py-build.sdist]
exclude = ["README.md", "notes.txt"]
""")
    (proj / "README.md").write_text("readme", encoding="utf-8")
    (proj / "src" / "notes.txt").write_text("notes", encoding="utf-8")
    monkeypatch.chdir(proj)
    monkeypatch.setenv("CONAN_HOME", str(tmp_path / "conan_home"))

    sdist_dir = tmp_path / "dist"
    sdist_dir.mkdir()
    with tarfile.open(sdist_dir / build_sdist(str(sdist_dir)), "r:gz") as tar:
        names = tar.getnames()

    assert "integration_pkg-0.1.0/README.md" not in names       # top-level file
    assert "integration_pkg-0.1.0/src/notes.txt" not in names   # inside a directory
    assert "integration_pkg-0.1.0/CMakeLists.txt" in names

def _sdist_names(tmp_path, expected_filename):
    """Build the sdist of the current project and return the tarball member names."""
    sdist_dir = tmp_path / "dist"
    sdist_dir.mkdir(exist_ok=True)
    assert build_sdist(str(sdist_dir)) == expected_filename
    with tarfile.open(sdist_dir / expected_filename, "r:gz") as tar:
        return tar.getnames()


def test_build_sdist_includes_wheel_packages_outside_src(tmp_path, monkeypatch):
    """Integration: wheel.packages and version.file reach the sdist from outside src/."""
    proj = tmp_path / "proj"
    make_integration_project(proj, pkg_name="ignored_pkg", pyproject_toml="""\
[project]
name = "outside-pkg"
dynamic = ["version"]
description = "Test"

[build-system]
requires = ["conan-py-build"]
build-backend = "conan_py_build.build"

[tool.conan-py-build.version]
file = "python/outside_pkg/__init__.py"

[tool.conan-py-build.wheel]
packages = ["python/outside_pkg"]
""")
    pkg = proj / "python" / "outside_pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text('__version__ = "4.5.6"', encoding="utf-8")
    (pkg / "helper.py").write_text("", encoding="utf-8")
    monkeypatch.chdir(proj)
    monkeypatch.setenv("CONAN_HOME", str(tmp_path / "conan_home"))

    names = _sdist_names(tmp_path, "outside_pkg-4.5.6.tar.gz")
    assert "outside_pkg-4.5.6/python/outside_pkg/__init__.py" in names
    assert "outside_pkg-4.5.6/python/outside_pkg/helper.py" in names


def test_build_sdist_includes_conandata(tmp_path, monkeypatch):
    """Integration: conandata.yml travels with the recipe, as Conan's own export does."""
    proj = tmp_path / "proj"
    make_integration_project(proj)
    (proj / "conandata.yml").write_text('sources:\n  "0.1.0":\n    url: "x"\n', encoding="utf-8")
    monkeypatch.chdir(proj)
    monkeypatch.setenv("CONAN_HOME", str(tmp_path / "conan_home"))

    names = _sdist_names(tmp_path, "integration_pkg-0.1.0.tar.gz")
    assert "integration_pkg-0.1.0/conandata.yml" in names


def test_build_sdist_includes_extra_profile(tmp_path, monkeypatch):
    """Integration: a declared extra-profile reaches the sdist, so a build from it
    applies the same settings instead of silently skipping the profile."""
    proj = tmp_path / "proj"
    make_integration_project(proj, pyproject_toml=_DEFAULT_PYPROJECT + """
[tool.conan-py-build]
extra-profile = "profiles/cpp17.profile"
""")
    profiles = proj / "profiles"
    profiles.mkdir()
    (profiles / "cpp17.profile").write_text("[settings]\ncompiler.cppstd=17\n", encoding="utf-8")
    monkeypatch.chdir(proj)
    monkeypatch.setenv("CONAN_HOME", str(tmp_path / "conan_home"))

    names = _sdist_names(tmp_path, "integration_pkg-0.1.0.tar.gz")
    assert "integration_pkg-0.1.0/profiles/cpp17.profile" in names


def test_build_sdist_excludes_compiled_extensions(tmp_path, monkeypatch):
    """Integration: a .so left by an in-place build does not reach the sdist."""
    proj = tmp_path / "proj"
    make_integration_project(proj)
    (proj / "src" / "integration_pkg" / "_core.cpython-312-x86_64-linux-gnu.so").write_bytes(b"\x00")
    monkeypatch.chdir(proj)
    monkeypatch.setenv("CONAN_HOME", str(tmp_path / "conan_home"))

    names = _sdist_names(tmp_path, "integration_pkg-0.1.0.tar.gz")
    assert not [n for n in names if n.endswith(".so")]


def test_wheel_packages_empty_ships_only_what_conan_staged(tmp_path, monkeypatch):
    """packages = [] keeps src/<name> out of the wheel and puts the staged module at its root."""
    proj = tmp_path / "proj"
    make_integration_project(proj, pyproject_toml=_DEFAULT_PYPROJECT + """
[tool.conan-py-build.wheel]
packages = []
""", conanfile="""\
from conan import ConanFile
from conan.tools.files import copy


class Pkg(ConanFile):
    name = "integration_pkg"
    settings = "os", "compiler", "build_type", "arch"

    def package(self):
        copy(self, "flatmod", self.source_folder, self.package_folder)
""")
    (proj / "flatmod").write_text("stands in for a top-level extension module", encoding="utf-8")
    monkeypatch.chdir(proj)
    monkeypatch.setenv("CONAN_HOME", str(tmp_path / "conan_home"))

    wheel_dir = tmp_path / "dist"
    wheel_dir.mkdir()
    wheel_name = build_wheel(str(wheel_dir), config_settings=None)

    with zipfile.ZipFile(wheel_dir / wheel_name) as zf:
        names = zf.namelist()
    assert "flatmod" in names
    assert not [n for n in names if n.startswith("integration_pkg/")]
