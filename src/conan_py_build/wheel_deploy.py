from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _collect_shared_libs(directory: Path) -> tuple[list[Path], list[Path]]:
    """Return (libs, lib_dirs) for all shared libraries under directory."""
    if not directory.is_dir():
        return [], []
    libs: set[Path] = set()
    for pattern in ("*.so", "*.so.*", "*.dylib", "*.dll"):
        for lib in directory.rglob(pattern):
            if lib.is_file() and not lib.is_symlink():
                libs.add(lib)
    sorted_libs = sorted(libs)
    return sorted_libs, sorted({lib.parent for lib in sorted_libs})


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


def _patch_deployed_lib_rpaths(libs: list[Path], lib_dirs: list[Path]) -> None:
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
        patcher = "install_name_tool"
    elif sys.platform == "linux":
        patcher = "patchelf"
    else:
        return

    for lib in libs:
        # Build loader-relative RPATHs from this lib's directory to every lib_dir.
        new_rpaths = []
        for target_dir in lib_dirs:
            rel = os.path.relpath(target_dir, lib.parent)
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
    deployed_libs, lib_dirs = _collect_shared_libs(deploy_dir)
    if not deployed_libs:
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
    _patch_deployed_lib_rpaths(deployed_libs, lib_dirs)

    if sys.platform == "darwin":
        patcher = "install_name_tool"
        rpath_flag = "-add_rpath"
    elif sys.platform == "linux":
        patcher = "patchelf"
        rpath_flag = "--add-rpath"
    else:
        return

    staging_libs, _ = _collect_shared_libs(staging_dir)
    for path in staging_libs:
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


