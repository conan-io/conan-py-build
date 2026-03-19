import shutil
import subprocess
import sys
from pathlib import Path


def move_deploy_to_wheel(
    deploy_folder: Path, staging_dir: Path
) -> None:
    """
    Copy shared libraries from a Conan ``runtime_deploy`` output folder into each
    Python package directory that contains native extensions (``.so`` / ``.pyd``).

    Shared libs are placed in the **same directory** as each native extension
    (``.so`` / ``.pyd``) on every platform — same idea as Windows DLL search.
    On macOS/Linux, RPATH is set to ``@loader_path`` / ``$ORIGIN`` so the dynamic
    loader can resolve ``.so`` / ``.dylib`` in the **same directory** as each
    binary under staging.
    """
    deploy_folder = Path(deploy_folder)
    if not deploy_folder.is_dir() or not any(deploy_folder.iterdir()):
        return
    for pkg_dir in package_dirs_with_extensions(staging_dir):
        pkg_dir.mkdir(parents=True, exist_ok=True)
        for f in deploy_folder.iterdir():
            dest = pkg_dir / f.name
            if f.is_file():
                shutil.copy2(f, dest)
            elif f.is_dir():
                shutil.copytree(f, dest, dirs_exist_ok=True)
    _patch_staging_rpath_for_wheel_libs(staging_dir)


def package_dirs_with_extensions(staging_dir: Path) -> set:
    package_dirs = set()
    for pattern in ("*.so", "*.pyd"):
        for path in staging_dir.rglob(pattern):
            if not path.is_file() or path.is_symlink():
                continue
            package_dirs.add(path.parent)
    return package_dirs


def _patch_staging_rpath_for_wheel_libs(staging_dir: Path) -> None:
    """macOS/Linux: add ``@loader_path`` / ``$ORIGIN`` for libs in the wheel staging tree."""
    if sys.platform == "darwin":
        rpath = "@loader_path"
        globs = [staging_dir.rglob(p) for p in ("*.so", "*.dylib")]
        paths = (p for gen in globs for p in gen)
        for path in paths:
            if path.is_symlink():
                continue
            try:
                subprocess.run(
                    ["install_name_tool", "-add_rpath", rpath, str(path)],
                    check=True,
                    capture_output=True,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        return

    if sys.platform != "linux":
        return

    rpath = "$ORIGIN"
    warned = False
    for path in staging_dir.rglob("*.so"):
        if path.is_symlink():
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
