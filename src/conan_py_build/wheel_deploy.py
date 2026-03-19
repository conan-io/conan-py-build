import fnmatch
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple, Union

_SHARED_LIB_SUFFIXES = (".so*", ".dylib*", ".dll*")


def _flatten_directory(
    src_dir: Union[os.PathLike, str],
    output_dir: Union[os.PathLike, str],
    symlinks: bool,
    extension_filter: Optional[Tuple[str, ...]] = None,
) -> int:
    src_root = os.path.normpath(os.path.abspath(os.fspath(src_dir)))
    out_root = Path(output_dir)
    file_count = 0
    for src_dirpath, _, fnames in os.walk(src_root, followlinks=symlinks):
        rel_path = os.path.relpath(src_dirpath, src_root)
        for name in fnames:
            if extension_filter and not any(
                fnmatch.fnmatch(name, f"*{ext}") for ext in extension_filter
            ):
                continue
            src_filepath = os.path.join(src_dirpath, name)
            if not symlinks and os.path.islink(src_filepath):
                continue
            dest = out_root / rel_path / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(src_filepath, dest, follow_symlinks=not symlinks)
                file_count += 1
            except OSError as e:
                if "WinError 1314" in str(e):
                    raise RuntimeError(
                        "wheel_deploy: Windows symlinks require admin privileges "
                        "or Developer mode. Use symlinks=False to disable."
                    ) from e
                raise
    return file_count


def _resolve_dep_dir(package_folder: Path, dirname: str) -> Path:
    return Path(dirname) if os.path.isabs(dirname) else package_folder / dirname


def default_wheel_deploy(
    graph,
    output_folder: "Path | str",
    symlinks: bool = True,
    **kwargs,
) -> None:
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)
    conanfile = graph.root.conanfile
    for req, dep in conanfile.dependencies.host.items():
        if not req.run:
            continue
        if dep.package_folder is None:
            continue
        cpp_info = dep.cpp_info.aggregated_components()
        pkg = Path(dep.package_folder)
        total = 0
        for dirname in (*(cpp_info.bindirs or ()), *(cpp_info.libdirs or ())):
            d = _resolve_dep_dir(pkg, dirname)
            if not d.is_dir():
                continue
            total += _flatten_directory(d, output_path, symlinks, _SHARED_LIB_SUFFIXES)
        if total:
            print(f"  Wheel deploy: copied {total} shared lib(s) from {dep.ref}", flush=True)


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


def _install_name_tool_add_rpath(binary: Path, rpath: str) -> None:
    subprocess.run(
        ["install_name_tool", "-add_rpath", rpath, str(binary)],
        check=True,
        capture_output=True,
    )


def fix_macos_rpath_for_libs(staging_dir: Path) -> None:
    if sys.platform != "darwin":
        return
    rpath = "@loader_path/.libs"
    for pattern in ("*.so", "*.dylib"):
        for path in staging_dir.rglob(pattern):
            if ".libs" in path.parts or path.is_symlink():
                continue
            try:
                _install_name_tool_add_rpath(path, rpath)
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
