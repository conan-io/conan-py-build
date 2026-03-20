from __future__ import annotations

import importlib.machinery
import shutil
import subprocess
import sys
from pathlib import Path


def _is_python_extension_module(path: Path) -> bool:
    """True if *path* is a real file whose name matches ``EXTENSION_SUFFIXES``."""
    if path.is_symlink():
        return False
    return any(
        path.name.endswith(suf) for suf in importlib.machinery.EXTENSION_SUFFIXES
    )


def _package_dirs_with_native_extensions(staging_dir: Path) -> set[Path]:
    """Parent dirs of each Python extension module under *staging_dir*."""
    package_dirs: set[Path] = set()
    for pattern in ("*.so", "*.pyd"):
        for path in staging_dir.rglob(pattern):
            if not path.is_file():
                continue
            if _is_python_extension_module(path):
                package_dirs.add(path.parent)
    return package_dirs


def move_deploy_to_wheel(deploy_folder: Path, staging_dir: Path) -> None:
    """Merge ``runtime_deploy`` into each package dir that has a native extension."""
    if not deploy_folder.is_dir() or not any(deploy_folder.iterdir()):
        return

    for pkg_dir in _package_dirs_with_native_extensions(staging_dir):
        shutil.copytree(deploy_folder, pkg_dir, dirs_exist_ok=True)


def patch_rpath(staging_dir: Path) -> None:
    """macOS/Linux: add ``@loader_path`` / ``$ORIGIN`` to extension ``.so`` files."""
    if sys.platform == "darwin":
        rpath = "@loader_path"
        patcher = "install_name_tool"
        arguments = ["-add_rpath", rpath]
    elif sys.platform == "linux":
        rpath = "$ORIGIN"
        patcher = "patchelf"
        arguments = ["--add-rpath", rpath]
    else:
        return

    warned = False
    for path in staging_dir.rglob("*.so"):
        if _is_python_extension_module(path):
            try:
                subprocess.run(
                    [patcher, *arguments, str(path)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except FileNotFoundError:
                print(
                    f"WARNING: {patcher} not found. Python extension {path.name} may not load "
                    f"shared libs. Install {patcher} or run auditwheel repair on the wheel {path.name}.",
                    flush=True,
                )
                warned = True
            except subprocess.CalledProcessError:
                pass
