from __future__ import annotations

import importlib.machinery
import shutil
import subprocess
import sys
from pathlib import Path


def _find_tool(name: str) -> str:
    """Return the full path to *name* if found via PATH, else the bare name."""
    return shutil.which(name) or name


def _is_python_extension_module(path: Path) -> bool:
    """True if *path* is a real file that is a Python extension module."""
    if path.is_symlink():
        return False
    # nm -D reads ELF dynamic symbols only; Mach-O has no separate dynamic symbol table.
    if sys.platform != "darwin":
        try:
            result = subprocess.run(["nm", "-D", str(path)], capture_output=True)
            if result.returncode == 0 and result.stdout:
                return b"PyInit_" in result.stdout
            # nm ran but returned nothing (stripped binary, not ELF, etc.) → fall through
        except FileNotFoundError:
            pass
    # Fallback: filename heuristic.
    name = path.name
    for suf in importlib.machinery.EXTENSION_SUFFIXES:
        if not name.endswith(suf):
            continue
        # Bare ".so" is ambiguous: Python extensions and plain shared-lib stubs both use it.
        if suf == ".so" and name.startswith("lib"):
            return False
        return True
    return False


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


def _collect_lib_dirs(deploy_dir: Path) -> list:
    """Unique directories under deploy_dir that contain shared libraries."""
    if not deploy_dir.is_dir():
        return []
    dirs: set = set()
    for pattern in ("*.so", "*.so.*", "*.dylib", "*.dll"):
        for lib in deploy_dir.rglob(pattern):
            if lib.is_file() and not lib.is_symlink():
                dirs.add(lib.parent)
    return sorted(dirs)


def set_rpath_to_deploy_dir(staging_dir: Path, deploy_dir: Path) -> None:
    """Set RPATH of extension modules to point to every directory containing deployed shared libs.

    This makes the extensions point to the shared libs deployed by Conan so that
    auditwheel / delocate can find them, bundle them, and mangle their SONAMEs.
    No-op when no shared libs were deployed (static-only builds).
    """
    lib_dirs = _collect_lib_dirs(deploy_dir)
    if not lib_dirs:
        return

    print(
        f"WARNING: Shared libraries found in {deploy_dir.name}/. "
        "The wheel produced by the backend is an intermediate artifact and must be repaired "
        "before installation or distribution. "
        "Run auditwheel repair (Linux), delocate-wheel (macOS), or delvewheel repair (Windows) "
        "to bundle the libraries into the wheel.",
        flush=True,
    )

    if sys.platform == "darwin":
        patcher = _find_tool("install_name_tool")
        make_args = lambda p, d: [patcher, "-add_rpath", str(d), str(p)]
    elif sys.platform == "linux":
        patcher = _find_tool("patchelf")
        make_args = lambda p, d: [patcher, "--add-rpath", str(d), str(p)]
    else:
        return

    for path in staging_dir.rglob("*.so"):
        if not _is_python_extension_module(path):
            continue
        for lib_dir in lib_dirs:
            try:
                subprocess.run(make_args(path, lib_dir), check=True, capture_output=True, text=True)
            except FileNotFoundError:
                print(
                    f"WARNING: {patcher} not found. Install it so auditwheel can locate "
                    f"shared libs for {path.name}.",
                    flush=True,
                )
                break
            except subprocess.CalledProcessError as e:
                stderr = e.stderr.strip() if e.stderr else ""
                print(
                    f"WARNING: {patcher} failed for {path.name}" + (f": {stderr}" if stderr else ""),
                    flush=True,
                )


def patch_rpath(staging_dir: Path) -> None:
    """macOS/Linux: add ``@loader_path`` / ``$ORIGIN`` to extension ``.so`` files."""
    if sys.platform == "darwin":
        rpath = "@loader_path"
        patcher = _find_tool("install_name_tool")
        arguments = ["-add_rpath", rpath]
    elif sys.platform == "linux":
        rpath = "$ORIGIN"
        patcher = _find_tool("patchelf")
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
