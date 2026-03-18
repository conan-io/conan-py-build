"""
Wheel deploy: copy shared libraries from Conan host dependencies and fix RPATH
so extensions find them (macOS/Linux). Used when building wheels with shared libs.

TODO: support configurable deploy (e.g. [tool.conan-py-build.wheel] deployer path,
exclude-shared-deps) so users can override or filter what gets bundled.
"""

import fnmatch
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    pass  # graph type from Conan, avoid import at module level


# Glob patterns for shared libs to copy (avoid matching e.g. "resolution" for ".so")
SHARED_LIB_PATTERNS = ("*.so", "*.so.*", "*.dylib", "*.dylib.*", "*.dll")


def _flatten_directory(
    dep_package_folder: Path,
    src_dir: Path,
    output_dir: Path,
    extension_filter: Optional[tuple] = None,
    symlinks: bool = True,
) -> int:
    """
    Copy files from src_dir into output_dir, optionally filtering by extension.
    Preserves relative subfolder structure under output_dir.
    Returns the number of files copied.
    """
    file_count = 0
    for dirpath, _, filenames in os.walk(src_dir, followlinks=symlinks):
        dirpath = Path(dirpath)
        try:
            rel_path = dirpath.relative_to(src_dir)
        except ValueError:
            rel_path = dirpath
        for filename in filenames:
            if extension_filter and not any(
                fnmatch.fnmatch(filename, pat) for pat in extension_filter
            ):
                continue
            src_file = dirpath / filename
            dest_file = output_dir / rel_path / filename
            if not dest_file.parent.exists():
                dest_file.parent.mkdir(parents=True, exist_ok=True)
            if src_file.is_symlink() and not symlinks:
                continue
            try:
                shutil.copy2(src_file, dest_file, follow_symlinks=not symlinks)
                file_count += 1
            except OSError as e:
                if "WinError 1314" in str(e):
                    raise RuntimeError(
                        "wheel_deploy: Windows symlinks require admin privileges "
                        "or Developer mode. Use symlinks=False to disable."
                    ) from e
                raise
    return file_count


def default_wheel_deploy(
    graph,
    output_folder: "Path | str",
    symlinks: bool = True,
    **kwargs,
) -> None:
    """
    Copy shared libraries (.so, .dylib, .dll) from Conan host dependencies into output_folder.
    """
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)
    conanfile = graph.root.conanfile

    host_deps = getattr(conanfile.dependencies, "host", None)
    if host_deps is None:
        host_deps = conanfile.dependencies

    items = host_deps.items() if hasattr(host_deps, "items") else list(host_deps.values())
    if hasattr(host_deps, "items"):
        iterator = items
    else:
        iterator = [(None, d) for d in items]

    for _req, dep in iterator:
        if getattr(dep, "package_folder", None) is None:
            continue
        ref = getattr(dep, "ref", None)
        pkg_folder = Path(dep.package_folder)
        cpp_info = dep.cpp_info.aggregated_components()
        libdirs = getattr(cpp_info, "libdirs", []) or []
        bindirs = getattr(cpp_info, "bindirs", []) or []
        total = 0
        for libdir in libdirs:
            src_dir = pkg_folder / libdir if not os.path.isabs(libdir) else Path(libdir)
            if not src_dir.is_dir():
                continue
            total += _flatten_directory(
                pkg_folder,
                src_dir,
                output_path,
                extension_filter=SHARED_LIB_PATTERNS,
                symlinks=symlinks,
            )
        for bindir in bindirs:
            src_dir = pkg_folder / bindir if not os.path.isabs(bindir) else Path(bindir)
            if not src_dir.is_dir():
                continue
            total += _flatten_directory(
                pkg_folder,
                src_dir,
                output_path,
                extension_filter=SHARED_LIB_PATTERNS,
                symlinks=symlinks,
            )
        if total and ref is not None:
            print(f"  Wheel deploy: copied {total} shared lib(s) from {ref}", flush=True)


def package_dirs_with_extensions(staging_dir: Path) -> set:
    """
    Return set of package directories under staging_dir that contain at least one
    extension module (.so or .pyd). Used to deploy shared libs into each package's .libs
    (delocate-style).
    """
    package_dirs = set()
    for ext in ("*.so", "*.pyd"):
        for path in staging_dir.rglob(ext):
            if not path.is_file() or path.is_symlink():
                continue
            if ".libs" in path.parts:
                continue
            package_dirs.add(path.parent)
    return package_dirs


def fix_macos_rpath_for_libs(staging_dir: Path) -> None:
    """
    On macOS, add @loader_path/.libs to extension modules so they find
    shared libs in their package's .libs folder after install (delocate-style).
    """
    if sys.platform != "darwin":
        return
    rpath = "@loader_path/.libs"
    for path in staging_dir.rglob("*.so"):
        if ".libs" in path.parts or path.is_symlink():
            continue
        try:
            subprocess.run(
                ["install_name_tool", "-add_rpath", rpath, str(path)],
                check=True,
                capture_output=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    for path in staging_dir.rglob("*.dylib"):
        if ".libs" in path.parts or path.is_symlink():
            continue
        try:
            subprocess.run(
                ["install_name_tool", "-add_rpath", rpath, str(path)],
                check=True,
                capture_output=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass


def fix_linux_rpath_for_libs(staging_dir: Path) -> None:
    """
    On Linux, add $ORIGIN/.libs to extension modules' RPATH so they find
    shared libs in their package's .libs folder. Uses patchelf if available.
    """
    if sys.platform != "linux":
        return
    rpath = "$ORIGIN/.libs"
    warned = False
    for path in staging_dir.rglob("*.so"):
        if ".libs" in path.parts or path.is_symlink():
            continue
        try:
            subprocess.run(
                ["patchelf", "--add-rpath", rpath, str(path)],
                check=True,
                capture_output=True,
            )
        except FileNotFoundError:
            if not warned:
                print(
                    "  WARNING: patchelf not found; Linux extension may not load "
                    "shared libs. Install patchelf or run auditwheel repair on the wheel.",
                    flush=True,
                )
                warned = True
        except subprocess.CalledProcessError:
            pass
