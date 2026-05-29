"""Unit tests for the conan_py_build build backend."""
import importlib.machinery
import subprocess
import sys
from pathlib import Path

import pytest

from conan.errors import ConanException

from conan_py_build.wheel_deploy import move_deploy_to_wheel, patch_rpath, set_rpath_to_deploy_dir

from conan_py_build.build import (
    _parse_config,
    _read_version_from_file,
    _resolve_version,
    _get_sdist_config,
    _resolve_conanfile_path,
    _get_wheel_tags,
    _check_wheel_package_path,
    _get_wheel_packages,
    _create_dist_info,
    _write_entry_points,
    _extra_arguments,
    _build_wheel_with_tags,
    _copy_license_files_from_paths,
    _validate_version_config,
    _get_version_from_scm,
    prepare_metadata_for_build_wheel,
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

[tool.conan-py-build.version]
file = "python/myadder/__init__.py"

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


def test_resolve_version_dynamic_without_version_config_raises(tmp_path):
    (tmp_path / "pyproject.toml").write_text("""[project]
name = "pkg"
dynamic = ["version"]
description = "Test"

[build-system]
requires = ["conan-py-build"]
build-backend = "conan_py_build.build"
""", encoding="utf-8")
    meta = {"name": "pkg", "dynamic": ["version"]}
    with pytest.raises(RuntimeError, match="must define 'file' or 'provider'"):
        _resolve_version(meta, tmp_path)


def test_patch_rpath(tmp_path, monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "platform", "linux")
    mod = tmp_path / "staging" / "pkg" / "mod.cpython-312-x86_64-linux-gnu.so"
    mod.parent.mkdir(parents=True)
    mod.write_text("ext")
    patch_rpath(tmp_path / "staging")
    patchelf_calls = [c for c in calls if "patchelf" in c[0]]
    assert len(patchelf_calls) == 1
    assert patchelf_calls[0][1:] == ["--add-rpath", "$ORIGIN", str(mod)]


def test_set_rpath_to_deploy_dir_linux(tmp_path, monkeypatch):
    staging = tmp_path / "staging"
    pkg = staging / "mypkg"
    pkg.mkdir(parents=True)
    ext = f"_core{importlib.machinery.EXTENSION_SUFFIXES[0]}"
    (pkg / ext).write_bytes(b"ext")
    deploy_dir = tmp_path / ".conan-libs"
    deploy_dir.mkdir()
    (deploy_dir / "libfmt.so.12").write_bytes(b"lib")

    calls = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: calls.append(cmd) or subprocess.CompletedProcess(cmd, 0, b"", b""))
    monkeypatch.setattr(sys, "platform", "linux")

    set_rpath_to_deploy_dir(staging, deploy_dir)

    rpath_calls = [c for c in calls if "patchelf" in c[0]]
    assert len(rpath_calls) == 1
    assert rpath_calls[0][1:] == ["--add-rpath", str(deploy_dir), str(pkg / ext)]


def test_set_rpath_to_deploy_dir_darwin(tmp_path, monkeypatch):
    staging = tmp_path / "staging"
    pkg = staging / "mypkg"
    pkg.mkdir(parents=True)
    ext = f"_core{importlib.machinery.EXTENSION_SUFFIXES[0]}"
    (pkg / ext).write_bytes(b"ext")
    deploy_dir = tmp_path / ".conan-libs"
    deploy_dir.mkdir()
    (deploy_dir / "libfmt.12.dylib").write_bytes(b"lib")

    calls = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: calls.append(cmd) or subprocess.CompletedProcess(cmd, 0, b"", b""))
    monkeypatch.setattr(sys, "platform", "darwin")

    set_rpath_to_deploy_dir(staging, deploy_dir)

    it_calls = [c for c in calls if "install_name_tool" in c[0]]
    assert len(it_calls) == 1
    assert it_calls[0][1:] == ["-add_rpath", str(deploy_dir), str(pkg / ext)]


def test_set_rpath_to_deploy_dir_no_op_when_empty(tmp_path, monkeypatch):
    staging = tmp_path / "staging"
    pkg = staging / "mypkg"
    pkg.mkdir(parents=True)
    ext = f"_core{importlib.machinery.EXTENSION_SUFFIXES[0]}"
    (pkg / ext).write_bytes(b"ext")
    deploy_dir = tmp_path / ".conan-libs"
    deploy_dir.mkdir()  # exists but empty

    calls = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: calls.append(cmd) or subprocess.CompletedProcess(cmd, 0, b"", b""))
    monkeypatch.setattr(sys, "platform", "linux")

    set_rpath_to_deploy_dir(staging, deploy_dir)

    assert not calls


def test_set_rpath_to_deploy_dir_subdirectory(tmp_path, monkeypatch):
    staging = tmp_path / "staging"
    pkg = staging / "mypkg"
    pkg.mkdir(parents=True)
    ext = f"_core{importlib.machinery.EXTENSION_SUFFIXES[0]}"
    (pkg / ext).write_bytes(b"ext")
    deploy_dir = tmp_path / ".conan-libs"
    subdir = deploy_dir / "fmt" / "lib"
    subdir.mkdir(parents=True)
    (subdir / "libfmt.so.12").write_bytes(b"lib")

    calls = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: calls.append(cmd) or subprocess.CompletedProcess(cmd, 0, b"", b""))
    monkeypatch.setattr(sys, "platform", "linux")

    set_rpath_to_deploy_dir(staging, deploy_dir)

    rpath_calls = [c for c in calls if "patchelf" in c[0]]
    assert len(rpath_calls) == 1
    assert rpath_calls[0][1:] == ["--add-rpath", str(subdir), str(pkg / ext)]


def test_set_rpath_to_deploy_dir_no_op_on_windows(tmp_path, monkeypatch):
    staging = tmp_path / "staging"
    pkg = staging / "mypkg"
    pkg.mkdir(parents=True)
    ext = f"_core{importlib.machinery.EXTENSION_SUFFIXES[0]}"
    (pkg / ext).write_bytes(b"ext")
    deploy_dir = tmp_path / ".conan-libs"
    deploy_dir.mkdir()
    (deploy_dir / "fmt.dll").write_bytes(b"lib")

    calls = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: calls.append(cmd) or subprocess.CompletedProcess(cmd, 0, b"", b""))
    monkeypatch.setattr(sys, "platform", "win32")

    set_rpath_to_deploy_dir(staging, deploy_dir)

    assert not any("patchelf" in str(c) or "install_name_tool" in str(c) for c in calls)


def test_move_deploy_to_wheel_copies_shared_libs_next_to_extension(tmp_path):
    deploy = tmp_path / "deploy"
    deploy.mkdir()
    (deploy / "libdep.so").write_text("so", encoding="utf-8")
    staging = tmp_path / "staging"
    pkg = staging / "mypkg"
    pkg.mkdir(parents=True)
    ext = f"_core{importlib.machinery.EXTENSION_SUFFIXES[0]}"
    (pkg / ext).write_text("ext", encoding="utf-8")
    move_deploy_to_wheel(deploy, staging)
    assert (pkg / "libdep.so").read_text() == "so"


def test_extra_arguments_empty_when_unset():
    assert _extra_arguments({}) == []
    assert _extra_arguments({"extra-arguments": []}) == []


def test_extra_arguments_returns_list_verbatim():
    args = ["-s=compiler.cppstd=17", "-o=gdal/*:shared=True", "-c=tools.build:jobs=4"]
    assert _extra_arguments({"extra-arguments": args}) == args


def test_extra_arguments_supports_pair_form():
    """Pair-form ``["-s", "value"]`` is passed through unchanged — argparse
    accepts both ``-s value`` and ``-s=value`` on Conan's CLI."""
    args = ["-s", "compiler.cppstd=17", "-o", "gdal/*:shared=True", "-c", "tools.build:jobs=4"]
    assert _extra_arguments({"extra-arguments": args}) == args


def test_extra_arguments_supports_mixed_pair_and_equals_form():
    """Mixing equals-form and pair-form in the same list works — argparse
    processes each token independently."""
    args = [
        "-s=compiler.cppstd=17",
        "-o", "gdal/*:shared=True",
        "-c=tools.build:jobs=4",
    ]
    assert _extra_arguments({"extra-arguments": args}) == args


def test_extra_arguments_rejects_non_list():
    with pytest.raises(RuntimeError, match="must be a list of strings"):
        _extra_arguments({"extra-arguments": "-s=compiler.cppstd=17"})


def test_extra_arguments_rejects_non_string_items():
    with pytest.raises(RuntimeError, match="must be a list of strings"):
        _extra_arguments({"extra-arguments": ["-s", {"k": "v"}]})


def test_get_sdist_config_minimal_pyproject(tmp_path):
    make_pyproject_minimal(tmp_path)
    assert _get_sdist_config(tmp_path) == {"include": [], "exclude": []}


def test_get_sdist_config_tool_include_exclude(tmp_path):
    make_pyproject_with_tool_config(tmp_path)
    assert _get_sdist_config(tmp_path) == {"include": ["docs"], "exclude": ["README.md"]}


def test_resolve_conanfile_path(tmp_path):
    """Resolved path is the conanfile.py (py=True: only .py allowed)."""
    (tmp_path / "conanfile.py").write_text("")
    assert _resolve_conanfile_path(".", tmp_path) == tmp_path / "conanfile.py"

    (tmp_path / "conan").mkdir()
    (tmp_path / "conan" / "conanfile.py").write_text("")
    assert _resolve_conanfile_path("conan", tmp_path) == tmp_path / "conan" / "conanfile.py"


def test_resolve_conanfile_path_rejects_txt(tmp_path):
    """Raises when only conanfile.txt exists (py=True allows only .py)."""
    (tmp_path / "conanfile.txt").write_text("")
    with pytest.raises(ConanException, match="Conanfile not found"):
        _resolve_conanfile_path(".", tmp_path)


def test_get_wheel_tags_from_env(monkeypatch):
    monkeypatch.setenv("WHEEL_ARCH", "manylinux_2_28_x86_64")
    monkeypatch.setenv("WHEEL_PYVER", "cp312")
    monkeypatch.setenv("WHEEL_ABI", "cp312")
    assert _get_wheel_tags() == {
        "arch": ["manylinux_2_28_x86_64"],
        "pyver": ["cp312"],
        "abi": ["cp312"],
    }


def test_get_wheel_tags_individual_override(monkeypatch):
    """Each WHEEL_* env var overrides its tag independently (#35)."""
    from packaging.tags import Tag
    monkeypatch.setattr("conan_py_build.build.sys_tags", lambda: iter([Tag("cp312", "cp312", "macosx_15_0_arm64")]))
    monkeypatch.delenv("WHEEL_PYVER", raising=False)
    monkeypatch.delenv("WHEEL_ARCH", raising=False)
    monkeypatch.setenv("WHEEL_ABI", "abi3")
    assert _get_wheel_tags() == {
        "pyver": ["cp312"],
        "abi": ["abi3"],
        "arch": ["macosx_15_0_arm64"],
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


def test_get_version_from_scm_none_raises(tmp_path, monkeypatch):
    """LookupError when setuptools-scm returns None (no git tags, no sdist)."""
    (tmp_path / "pyproject.toml").write_text("[tool.setuptools_scm]\n")
    import setuptools_scm
    monkeypatch.setattr(setuptools_scm, "_get_version", lambda *a, **kw: None)
    with pytest.raises(LookupError, match="setuptools-scm could not detect a version"):
        _get_version_from_scm(tmp_path)


def test_validate_version_config_invalid_provider_raises(tmp_path):
    (tmp_path / "pyproject.toml").write_text("""[project]
name = "bad"
description = "Test"

[build-system]
requires = ["conan-py-build"]
build-backend = "conan_py_build.build"

[tool.conan-py-build.version]
provider = "invalid"
""", encoding="utf-8")
    with pytest.raises(RuntimeError, match="must be 'setuptools_scm'"):
        _validate_version_config(tmp_path)


@pytest.fixture
def prepared_dist_info(tmp_path, monkeypatch):
    """Run prepare_metadata_for_build_wheel on a minimal project; return the dist-info Path."""
    make_pyproject_minimal(tmp_path)
    monkeypatch.chdir(tmp_path)
    name = prepare_metadata_for_build_wheel(str(tmp_path / "meta"))
    return tmp_path / "meta" / name


def test_prepare_metadata_returns_dist_info_name(tmp_path, monkeypatch):
    """Returns the .dist-info directory name with normalised package name and version."""
    make_pyproject_minimal(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert prepare_metadata_for_build_wheel(str(tmp_path / "meta")) == "test_pkg-1.2.3.dist-info"


def test_prepare_metadata_metadata_content(prepared_dist_info):
    """METADATA contains the Name and Version headers from pyproject.toml."""
    content = (prepared_dist_info / "METADATA").read_text(encoding="utf-8")
    assert "Name: test-pkg" in content
    assert "Version: 1.2.3" in content


def test_prepare_metadata_no_wheel_file(prepared_dist_info):
    """WHEEL file is not written: tags depend on VirtualBuildEnv and cannot be computed here."""
    assert not (prepared_dist_info / "WHEEL").exists()


def test_prepare_metadata_dynamic_version_from_file(tmp_path, monkeypatch):
    """Dynamic version resolved from [tool.conan-py-build.version].file is used in the directory name."""
    make_pyproject_with_tool_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    name = prepare_metadata_for_build_wheel(str(tmp_path / "meta"))
    assert name == "myadder_pybind11-0.5.0.dist-info"
    assert "Version: 0.5.0" in (tmp_path / "meta" / name / "METADATA").read_text(encoding="utf-8")


def test_write_entry_points_omits_file_when_no_entries(tmp_path):
    dist_info = tmp_path / "pkg-1.0.0.dist-info"
    dist_info.mkdir()
    _write_entry_points(dist_info, {"name": "pkg", "version": "1.0.0"}, tmp_path)
    assert not (dist_info / "entry_points.txt").exists()


def test_write_entry_points_emits_all_section_kinds(tmp_path):
    """scripts -> [console_scripts], gui-scripts -> [gui_scripts],
    entry-points."group" -> [group], all coexisting in the same file."""
    dist_info = tmp_path / "pkg-1.0.0.dist-info"
    dist_info.mkdir()
    metadata = {
        "name": "pkg",
        "version": "1.0.0",
        "scripts": {"mytool": "pkg.cli:main"},
        "gui-scripts": {"mygui": "pkg.gui:run"},
        "entry-points": {"rasterio.rio_commands": {"info": "pkg.info:info"}},
    }
    _write_entry_points(dist_info, metadata, tmp_path)
    content = (dist_info / "entry_points.txt").read_text(encoding="utf-8")
    assert "[console_scripts]\nmytool = pkg.cli:main" in content
    assert "[gui_scripts]\nmygui = pkg.gui:run" in content
    assert "[rasterio.rio_commands]\ninfo = pkg.info:info" in content


def test_write_entry_points_reserved_group_in_entry_points_raises(tmp_path):
    """Reserved group ('console_scripts') under [project.entry-points] is forbidden by PEP 621."""
    dist_info = tmp_path / "pkg-1.0.0.dist-info"
    dist_info.mkdir()
    metadata = {
        "name": "pkg",
        "version": "1.0.0",
        "scripts": {"cli": "pkg.cli:main"},
        "entry-points": {"console_scripts": {"other": "pkg.cli:other"}},
    }
    with pytest.raises(Exception):
        _write_entry_points(dist_info, metadata, tmp_path)


def test_create_dist_info_writes_entry_points_when_scripts_declared(tmp_path):
    """End-to-end: _create_dist_info emits entry_points.txt alongside METADATA."""
    staging = tmp_path / "staging"
    staging.mkdir()
    metadata = {"name": "pkg", "version": "1.0.0", "scripts": {"mytool": "pkg.cli:main"}}
    dist_info = _create_dist_info(staging, metadata, tmp_path)
    assert (dist_info / "METADATA").is_file()
    assert (dist_info / "entry_points.txt").is_file()


def test_prepare_metadata_with_license_file(tmp_path, monkeypatch):
    """License file declared in pyproject.toml is copied into .dist-info/licenses/."""
    (tmp_path / "pyproject.toml").write_text("""\
[project]
name = "licensed-pkg"
version = "0.9.0"
description = "Test"
license-files = ["LICENSE"]

[build-system]
requires = ["conan-py-build"]
build-backend = "conan_py_build.build"
""", encoding="utf-8")
    (tmp_path / "LICENSE").write_text("MIT", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    dist_info = tmp_path / "meta" / prepare_metadata_for_build_wheel(str(tmp_path / "meta"))
    assert (dist_info / "licenses" / "LICENSE").read_text() == "MIT"
    assert "License-File: LICENSE" in (dist_info / "METADATA").read_text(encoding="utf-8")
