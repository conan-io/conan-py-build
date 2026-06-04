from __future__ import annotations

import importlib.machinery
import os
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


def _collect_lib_dirs(deploy_dir: Path) -> list[Path]:
    """Unique directories under deploy_dir that contain shared libraries."""
    if not deploy_dir.is_dir():
        return []
    dirs: set[Path] = set()
    for pattern in ("*.so", "*.so.*", "*.dylib", "*.dll"):
        for lib in deploy_dir.rglob(pattern):
            if lib.is_file() and not lib.is_symlink():
                dirs.add(lib.parent)
    return sorted(dirs)


def _get_rpaths_darwin(path: Path) -> list[str]:
    """Return the LC_RPATH entries of a Mach-O binary."""
    result = subprocess.run(["otool", "-l", str(path)], capture_output=True, text=True)
    if result.returncode != 0:
        return []
    rpaths: list[str] = []
    in_rpath = False
    for line in result.stdout.splitlines():
        if "LC_RPATH" in line:
            in_rpath = True
        elif in_rpath:
            stripped = line.strip()
            if stripped.startswith("path "):
                rpaths.append(stripped.split()[1])
                in_rpath = False
    return rpaths


def _patch_deployed_lib_rpaths(lib_dirs: list[Path]) -> None:
    """Replace Conan-cache RPATHs on deployed libs with loader-relative paths.

    runtime_deploy copies libs preserving their original RPATHs (pointing to the
    Conan package cache). When a repair tool processes a deployed lib transitively
    it follows those cache RPATHs, finding a transitive dep at a different absolute
    path than the extension's RPATH (pointing to deploy_dir) does. That basename
    collision aborts delocate/auditwheel.

    Fix: replace cache RPATHs with @loader_path/$ORIGIN entries so every deployed
    lib resolves its own deps within deploy_dir, giving repair tools a single
    consistent path for each library.
    """
    if sys.platform == "darwin":
        patcher = _find_tool("install_name_tool")
    elif sys.platform == "linux":
        patcher = _find_tool("patchelf")
    else:
        return

    for lib_dir in lib_dirs:
        for lib in sorted(lib_dir.iterdir()):
            if not lib.is_file() or lib.is_symlink():
                continue
            if _is_python_extension_module(lib):
                continue

            # Build loader-relative RPATHs from this lib's directory to every lib_dir.
            new_rpaths = []
            for target_dir in lib_dirs:
                rel = os.path.relpath(target_dir, lib_dir)
                if sys.platform == "darwin":
                    new_rpaths.append("@loader_path" if rel == "." else f"@loader_path/{rel}")
                else:
                    new_rpaths.append("$ORIGIN" if rel == "." else f"$ORIGIN/{rel}")

            if sys.platform == "darwin":
                old_rpaths = _get_rpaths_darwin(lib)
                deletes = [arg for old in old_rpaths if old not in new_rpaths for arg in ("-delete_rpath", old)]
                adds = [arg for new in new_rpaths if new not in old_rpaths for arg in ("-add_rpath", new)]
                if deletes or adds:
                    try:
                        result = subprocess.run([patcher, *deletes, *adds, str(lib)], capture_output=True, text=True)
                        if result.returncode != 0 and result.stderr:
                            print(f"WARNING: {patcher} failed for {lib.name}: {result.stderr.strip()}", flush=True)
                    except FileNotFoundError:
                        raise RuntimeError(
                            f"{patcher} not found. It is required to patch RPATHs on deployed "
                            f"shared libraries. Install {patcher} and retry."
                        )
            else:
                try:
                    result = subprocess.run(
                        [patcher, "--set-rpath", ":".join(new_rpaths), str(lib)],
                        capture_output=True, text=True,
                    )
                    if result.returncode != 0 and result.stderr:
                        print(f"WARNING: {patcher} failed for {lib.name}: {result.stderr.strip()}", flush=True)
                except FileNotFoundError:
                    raise RuntimeError(
                        f"{patcher} not found. It is required to patch RPATHs on deployed "
                        f"shared libraries. Install {patcher} and retry."
                    )


def _set_deploy_rpath(staging_dir: Path, deploy_dir: Path) -> None:
    """Set RPATH of extension modules to point to every directory containing deployed shared libs.

    This makes the extensions point to the shared libs deployed by Conan so that
    auditwheel / delocate can find them, bundle them, and mangle their SONAMEs.
    No-op when no shared libs were deployed (static-only builds).
    """
    lib_dirs = _collect_lib_dirs(deploy_dir)
    if not lib_dirs:
        return

    print(
        f"WARNING: Shared libraries deployed to {deploy_dir.name}/. "
        "This wheel is an intermediate artifact — run auditwheel repair (Linux), "
        "delocate-wheel (macOS), or delvewheel repair (Windows) before installing or distributing. "
        "Local installs may work by accident while that directory exists.",
        flush=True,
    )

    # Patch deployed libs first so repair tools find every transitive dep within
    # deploy_dir rather than following the original Conan-cache RPATHs.
    _patch_deployed_lib_rpaths(lib_dirs)

    if sys.platform == "darwin":
        patcher = _find_tool("install_name_tool")
        rpath_flag = "-add_rpath"
    elif sys.platform == "linux":
        patcher = _find_tool("patchelf")
        rpath_flag = "--add-rpath"
    else:
        return

    for path in staging_dir.rglob("*.so"):
        if not _is_python_extension_module(path):
            continue
        _add_rpath_entries(path, lib_dirs, patcher, rpath_flag)


def _add_rpath_entries(path: Path, lib_dirs: list[Path], patcher: str, rpath_flag: str) -> None:
    for lib_dir in lib_dirs:
        try:
            subprocess.run([patcher, rpath_flag, str(lib_dir), str(path)], check=True, capture_output=True, text=True)
        except FileNotFoundError:
            raise RuntimeError(
                f"{patcher} not found. It is required to set RPATH on extension modules "
                f"when shared libraries are deployed. Install {patcher} and retry."
            )
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.strip() if e.stderr else ""
            print(
                f"WARNING: {patcher} failed for {path.name}" + (f": {stderr}" if stderr else ""),
                flush=True,
            )


def _patch_extension_origin_rpath(staging_dir: Path) -> None:
    """macOS/Linux: add ``@loader_path`` / ``$ORIGIN`` to extension ``.so`` files."""
    if sys.platform == "darwin":
        patcher = _find_tool("install_name_tool")
        arguments = ["-add_rpath", "@loader_path"]
    elif sys.platform == "linux":
        patcher = _find_tool("patchelf")
        arguments = ["--add-rpath", "$ORIGIN"]
    else:
        return

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
            except subprocess.CalledProcessError:
                pass
