import fnmatch
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple, Union


def apply_deploy_folder_to_wheel_staging(
    deploy_folder: Path, staging_dir: Path
) -> None:
    """
    Copy shared libraries from a Conan ``runtime_deploy`` output folder into each
    Python package directory that contains native extensions (``.so`` / ``.pyd``).

    On Windows, DLLs are placed next to the extension, on Unix, under ``.libs/``.
    Then adjusts RPATH on macOS/Linux so extensions can load those libraries.
    """
    deploy_folder = Path(deploy_folder)
    if not deploy_folder.is_dir() or not any(deploy_folder.iterdir()):
        return
    use_libs_subdir = sys.platform != "win32"
    for pkg_dir in package_dirs_with_extensions(staging_dir):
        pkg_libs = pkg_dir / ".libs" if use_libs_subdir else pkg_dir
        pkg_libs.mkdir(parents=True, exist_ok=True)
        for f in deploy_folder.iterdir():
            dest = pkg_libs / f.name
            if f.is_file():
                shutil.copy2(f, dest)
            elif f.is_dir():
                shutil.copytree(f, dest, dirs_exist_ok=True)
    fix_macos_rpath_for_libs(staging_dir)
    fix_linux_rpath_for_libs(staging_dir)


def package_dirs_with_extensions(staging_dir: Path) -> set:
    package_dirs = set()
    for pattern in ("*.so", "*.pyd"):
        for path in staging_dir.rglob(pattern):
            if not path.is_file() or path.is_symlink():
                continue
            if ".libs" in path.parts:
                continue
            package_dirs.add(path.parent)
    return package_dirs


def fix_macos_rpath_for_libs(staging_dir: Path) -> None:
    if sys.platform != "darwin":
        return
    rpath = "@loader_path/.libs"
    for pattern in ("*.so", "*.dylib"):
        for path in staging_dir.rglob(pattern):
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
                    "  WARNING: patchelf not found. Linux extension may not load "
                    "shared libs. Install patchelf or run auditwheel repair on the wheel.",
                    flush=True,
                )
                warned = True
        except subprocess.CalledProcessError:
            pass
