"""Unit tests for the conan_py_build build backend."""
from pathlib import Path

import pytest

from conan_py_build.build import (
    _parse_config,
    _read_version_from_file,
    _resolve_version,
    _get_sdist_config,
    _get_wheel_tags,
    _check_wheel_package_path,
    _get_wheel_packages,
    _create_dist_info,
    _build_wheel_with_tags,
    _parse_license_file_paths_from_metadata_text,
    _copy_license_files_from_paths,
)


def make_pyproject_minimal(path: Path) -> None:
    (path / "pyproject.toml").write_text("""[project]
name = "test-pkg"
version = "1.2.3"
description = "Test"

[build-system]
requires = ["conan-py-build"]
build-backend = "conan_py_build.build"
""", encoding="utf-8")


def make_pyproject_with_tool_config(path: Path) -> None:
    (path / "pyproject.toml").write_text("""[project]
name = "myadder-pybind11"
dynamic = ["version"]
description = "Test"

[build-system]
requires = ["conan-py-build"]
build-backend = "conan_py_build.build"

[tool.conan-py-build]
version-file = "python/myadder/__init__.py"

[tool.conan-py-build.wheel]
packages = ["python/myadder", "src/extra_utils"]

[tool.conan-py-build.sdist]
include = ["docs"]
exclude = ["README.md"]
""", encoding="utf-8")
    init_py = path / "python" / "myadder" / "__init__.py"
    init_py.parent.mkdir(parents=True)
    init_py.write_text('__version__ = "0.5.0"', encoding="utf-8")


def test_parse_config_empty_or_none():
    assert _parse_config(None) == {
        "host_profile": "default",
        "build_profile": "default",
        "build_dir": None,
    }
    assert _parse_config({}) == _parse_config(None)


def test_parse_config_custom_profiles_and_build_dir():
    cfg = _parse_config({
        "host-profile": "linux",
        "build-profile": "macos",
        "build-dir": "/tmp/build",
    })
    assert cfg == {"host_profile": "linux", "build_profile": "macos", "build_dir": "/tmp/build"}


@pytest.mark.parametrize("content,expected", [
    ('__version__ = "2.0.0"', "2.0.0"),
    ('__version__: str = "3.1.4"', "3.1.4"),
    ("x = 1\ny = 2", None),
    ("__version__ = 1", None),
])
def test_read_version_from_file(tmp_path, content, expected):
    f = tmp_path / "version.py"
    f.write_text(content, encoding="utf-8")
    assert _read_version_from_file(f) == expected


def test_read_version_from_file_missing_returns_none(tmp_path):
    assert _read_version_from_file(tmp_path / "nonexistent.py") is None


def test_resolve_version_from_metadata():
    meta = {"name": "pkg", "version": "1.0.0"}
    assert _resolve_version(meta, Path("/any")) == "1.0.0"


def test_resolve_version_missing_falls_back_to_0_0_0(tmp_path):
    make_pyproject_minimal(tmp_path)
    meta = {"name": "pkg"}
    assert _resolve_version(meta, tmp_path) == "0.0.0"


def test_resolve_version_dynamic_without_version_file_raises(tmp_path):
    (tmp_path / "pyproject.toml").write_text("""[project]
name = "pkg"
dynamic = ["version"]
description = "Test"

[build-system]
requires = ["conan-py-build"]
build-backend = "conan_py_build.build"
""", encoding="utf-8")
    meta = {"name": "pkg", "dynamic": ["version"]}
    with pytest.raises(RuntimeError, match="version could not be resolved"):
        _resolve_version(meta, tmp_path)


def test_get_sdist_config_minimal_pyproject(tmp_path):
    make_pyproject_minimal(tmp_path)
    assert _get_sdist_config(tmp_path) == {"include": [], "exclude": []}


def test_get_sdist_config_tool_include_exclude(tmp_path):
    make_pyproject_with_tool_config(tmp_path)
    assert _get_sdist_config(tmp_path) == {"include": ["docs"], "exclude": ["README.md"]}


def test_get_wheel_tags_from_env(monkeypatch):
    monkeypatch.setenv("WHEEL_ARCH", "manylinux_2_28_x86_64")
    monkeypatch.setenv("WHEEL_PYVER", "cp312")
    monkeypatch.setenv("WHEEL_ABI", "cp312")
    assert _get_wheel_tags() == {
        "arch": ["manylinux_2_28_x86_64"],
        "pyver": ["cp312"],
        "abi": ["cp312"],
    }


def test_check_wheel_package_path_ok(tmp_path):
    pkg = tmp_path / "src" / "mypkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    assert _check_wheel_package_path(tmp_path, "src/mypkg") == pkg.resolve()


def test_check_wheel_package_path_outside_source_raises(tmp_path):
    with pytest.raises(RuntimeError, match="must be inside source"):
        _check_wheel_package_path(tmp_path, "../other/pkg")


def test_check_wheel_package_path_missing_dir_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="does not exist"):
        _check_wheel_package_path(tmp_path, "src/nonexistent")


def test_check_wheel_package_path_no_init_raises(tmp_path):
    (tmp_path / "src" / "nopkg").mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="__init__.py"):
        _check_wheel_package_path(tmp_path, "src/nopkg")


def test_get_wheel_packages_default_src_name(tmp_path):
    make_pyproject_minimal(tmp_path)
    (tmp_path / "src" / "test_pkg").mkdir(parents=True)
    (tmp_path / "src" / "test_pkg" / "__init__.py").write_text("")
    assert [p.name for p in _get_wheel_packages(tmp_path, "test_pkg")] == ["test_pkg"]


def test_get_wheel_packages_default_missing_raises(tmp_path):
    make_pyproject_minimal(tmp_path)
    with pytest.raises(FileNotFoundError, match="does not exist|__init__.py"):
        _get_wheel_packages(tmp_path, "test_pkg")


def test_get_wheel_packages_from_tool_config(tmp_path):
    make_pyproject_with_tool_config(tmp_path)
    (tmp_path / "src" / "extra_utils").mkdir(parents=True)
    (tmp_path / "src" / "extra_utils" / "__init__.py").write_text("")
    assert {p.name for p in _get_wheel_packages(tmp_path, "myadder-pybind11")} == {"myadder", "extra_utils"}


def test_create_dist_info_creates_dir_and_metadata(tmp_path):
    staging = tmp_path / "staging"
    staging.mkdir()
    metadata = {"name": "test-pkg", "version": "1.0.0", "description": "A test"}
    dist_info = _create_dist_info(staging, metadata, tmp_path)
    assert dist_info.is_dir() and dist_info.name == "test_pkg-1.0.0.dist-info"
    content = (dist_info / "METADATA").read_text(encoding="utf-8")
    assert "Name: test-pkg" in content
    assert "Version: 1.0.0" in content


def test_parse_license_file_paths_from_metadata_text():
    assert _parse_license_file_paths_from_metadata_text(
        "Name: pkg\nVersion: 1.0\nLicense-File: LICENSE\nLicense-File: docs/COPYING\n"
    ) == ["LICENSE", "docs/COPYING"]
    assert _parse_license_file_paths_from_metadata_text("Name: pkg\n") == []


def test_license_files_dotdot_rejected(tmp_path):
    """pyproject_metadata rejects license-files pattern '..' (must match within project)."""
    (tmp_path / "LICENSE").write_text("", encoding="utf-8")
    staging = tmp_path / "staging"
    staging.mkdir()
    metadata = {"name": "pkg", "version": "0.1.0", "license-files": [".."]}
    with pytest.raises(Exception, match="invalid.*license-files|within the project"):
        _create_dist_info(staging, metadata, tmp_path)


def test_copy_license_files_from_paths_creates_licenses_dir(tmp_path):
    (tmp_path / "LICENSE").write_text("MIT", encoding="utf-8")
    dist_info = tmp_path / "pkg-1.0.0.dist-info"
    dist_info.mkdir()
    _copy_license_files_from_paths(dist_info, tmp_path, ["LICENSE"])
    assert (dist_info / "licenses" / "LICENSE").read_text() == "MIT"


def test_create_dist_info_includes_license_file_and_metadata(tmp_path):
    (tmp_path / "LICENSE").write_text("MIT", encoding="utf-8")
    staging = tmp_path / "staging"
    staging.mkdir()
    metadata = {"name": "myadder", "version": "0.1.0", "license-files": ["LICENSE"]}
    dist_info = _create_dist_info(staging, metadata, tmp_path)
    assert (dist_info / "licenses" / "LICENSE").is_file()
    meta_content = (dist_info / "METADATA").read_text(encoding="utf-8")
    assert "License-File: LICENSE" in meta_content


def test_create_dist_info_license_files_match_none_raises(tmp_path):
    """license-files pattern that matches no file raises (pyproject_metadata)."""
    staging = tmp_path / "staging"
    staging.mkdir()
    metadata = {"name": "pkg", "version": "0.1.0", "license-files": ["nonexistent.txt"]}
    with pytest.raises(Exception, match="must match at least one file"):
        _create_dist_info(staging, metadata, tmp_path)


def test_build_wheel_with_tags_produces_whl(tmp_path):
    wheel_dir = tmp_path / "dist"
    wheel_dir.mkdir(parents=True)
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir(parents=True)
    (staging_dir / "dummy").write_text("")
    dist_info = staging_dir / "test_pkg-1.0.0.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text("Name: test_pkg\nVersion: 1.0.0\n", encoding="utf-8")
    tags = {"pyver": ["cp312"], "abi": ["cp312"], "arch": ["any"]}
    name = _build_wheel_with_tags(wheel_dir, staging_dir, "test_pkg", "1.0.0", tags)
    assert (wheel_dir / name).is_file()
