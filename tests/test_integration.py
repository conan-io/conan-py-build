"""Integration tests: run real PEP 517 hooks (build_sdist, build_wheel) on a project layout."""
import subprocess
import tarfile
import types
import zipfile
from pathlib import Path

import pytest

from conan_py_build.build import build_sdist, build_wheel


def make_integration_project(path: Path) -> None:
    """Create a minimal conan-py-build project"""

    (path / "pyproject.toml").write_text("""[project]
name = "integration-pkg"
version = "0.1.0"
description = "For integration tests"
license-files = ["LICENSE"]

[build-system]
requires = ["conan-py-build"]
build-backend = "conan_py_build.build"
""", encoding="utf-8")

    (path / "LICENSE").write_text("MIT", encoding="utf-8")

    (path / "conanfile.py").write_text("""from conan import ConanFile
from conan.tools.cmake import cmake_layout


class Pkg(ConanFile):
    name = "integration_pkg"
    version = "0.1.0"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def layout(self):
        cmake_layout(self)

    def source(self):
        self.output.info("source_called")

    def build(self):
        pass
""", encoding="utf-8")

    (path / "CMakeLists.txt").write_text("""cmake_minimum_required(VERSION 3.15)
project(integration_pkg)
""", encoding="utf-8")

    (path / "src" / "integration_pkg" / "__init__.py").parent.mkdir(parents=True)

    (path / "src" / "integration_pkg" / "__init__.py").write_text("", encoding="utf-8")


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

    assert filename == "integration-pkg-0.1.0.tar.gz"
    tarball = sdist_dir / filename
    assert tarball.is_file()

    with tarfile.open(tarball, "r:gz") as tar:
        names = sorted(tar.getnames())
        expected = sorted([
            "integration-pkg-0.1.0/CMakeLists.txt",
            "integration-pkg-0.1.0/LICENSE",
            "integration-pkg-0.1.0/PKG-INFO",
            "integration-pkg-0.1.0/conanfile.py",
            "integration-pkg-0.1.0/pyproject.toml",
            "integration-pkg-0.1.0/src/integration_pkg/__init__.py",
        ])
        assert names == expected
        pkg_info = tar.extractfile("integration-pkg-0.1.0/PKG-INFO").read().decode("utf-8")
        assert "License-File: LICENSE" in pkg_info


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

    with tarfile.open(dist_dir / "integration-pkg-0.1.0.tar.gz", "r:gz") as tar:
        pkg_info = tar.extractfile("integration-pkg-0.1.0/PKG-INFO").read().decode("utf-8")

    (wheel_path,) = dist_dir.glob("integration_pkg-0.1.0-*.whl")
    with zipfile.ZipFile(wheel_path) as zf:
        (metadata_name,) = [n for n in zf.namelist() if n.endswith(".dist-info/METADATA")]
        wheel_metadata = zf.read(metadata_name).decode("utf-8")

    assert pkg_info.strip() == wheel_metadata.strip(), "PKG-INFO and METADATA must be the same core metadata"


def test_build_wheel_integration(integration_project, capfd):
    """Integration: build_wheel on a real project."""
    wheel_dir = integration_project.work_dir / "wheelhouse"
    wheel_dir.mkdir()
    name = build_wheel(str(wheel_dir), config_settings=None)
    assert name.endswith(".whl")
    assert (wheel_dir / name).is_file()
    _, err = capfd.readouterr()
    assert "source_called" in err


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


def test_build_sdist_version_file(tmp_path, monkeypatch):
    """Integration: build_sdist resolves dynamic version from [tool.version].file."""
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "pyproject.toml").write_text("""[project]
name = "file-ver-pkg"
dynamic = ["version"]
description = "Test"

[build-system]
requires = ["conan-py-build"]
build-backend = "conan_py_build.build"

[tool.conan-py-build]
version = "file"

[tool.version]
file = "src/file_ver_pkg/__init__.py"
""", encoding="utf-8")
    (proj / "conanfile.py").write_text("""from conan import ConanFile
from conan.tools.cmake import cmake_layout

class Pkg(ConanFile):
    name = "file_ver_pkg"
    version = "2.3.4"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"
    def layout(self):
        cmake_layout(self)
    def source(self):
        pass
    def build(self):
        pass
""", encoding="utf-8")
    (proj / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.15)\nproject(x)\n")
    pkg = proj / "src" / "file_ver_pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text('__version__ = "2.3.4"', encoding="utf-8")
    monkeypatch.chdir(proj)
    monkeypatch.setenv("CONAN_HOME", str(tmp_path / "conan_home"))

    sdist_dir = tmp_path / "dist"
    sdist_dir.mkdir()
    filename = build_sdist(str(sdist_dir))
    assert filename == "file-ver-pkg-2.3.4.tar.gz"


def test_build_sdist_version_scm(tmp_path, monkeypatch):
    """Integration: build_sdist resolves dynamic version from setuptools_scm (git tag)."""
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "pyproject.toml").write_text("""[project]
name = "scm-ver-pkg"
dynamic = ["version"]
description = "Test"

[build-system]
requires = ["conan-py-build"]
build-backend = "conan_py_build.build"

[tool.conan-py-build]
version = "setuptools_scm"

[tool.version.setuptools_scm]
write_to = "src/scm_ver_pkg/_version.py"
""", encoding="utf-8")
    (proj / "conanfile.py").write_text("""from conan import ConanFile
from conan.tools.cmake import cmake_layout

class Pkg(ConanFile):
    name = "scm_ver_pkg"
    version = "3.0.0"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"
    def layout(self):
        cmake_layout(self)
    def source(self):
        pass
    def build(self):
        pass
""", encoding="utf-8")
    (proj / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.15)\nproject(x)\n")
    pkg = proj / "src" / "scm_ver_pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")

    env = {**dict(__import__("os").environ), "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "init"], cwd=proj, check=True, env=env, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=proj, check=True, env=env, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=proj, check=True, env=env, capture_output=True)
    subprocess.run(["git", "tag", "v3.0.0"], cwd=proj, check=True, env=env, capture_output=True)

    monkeypatch.chdir(proj)
    monkeypatch.setenv("CONAN_HOME", str(tmp_path / "conan_home"))

    sdist_dir = tmp_path / "dist"
    sdist_dir.mkdir()
    filename = build_sdist(str(sdist_dir))
    assert filename == "scm-ver-pkg-3.0.0.tar.gz"
