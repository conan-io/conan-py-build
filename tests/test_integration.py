"""Integration tests: run real PEP 517 hooks (build_sdist, build_wheel) on a project layout."""
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
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def layout(self):
        cmake_layout(self)

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
    return types.SimpleNamespace(work_dir=tmp_path)


def test_build_sdist_produces_tarball(integration_project):
    """Integration: build_sdist produces a valid tarball and PKG-INFO includes License-File (PEP 639)."""
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
        # PEP 639: License-File in sdist PKG-INFO when [project].license-files is set
        pkg_info = tar.extractfile("integration-pkg-0.1.0/PKG-INFO").read().decode("utf-8")
        assert "License-File: LICENSE" in pkg_info


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


def test_build_wheel_integration(integration_project):
    """Integration: build_wheel on a real project."""
    wheel_dir = integration_project.work_dir / "wheelhouse"
    wheel_dir.mkdir()
    name = build_wheel(str(wheel_dir), config_settings=None)
    assert name.endswith(".whl")
    assert (wheel_dir / name).is_file()
