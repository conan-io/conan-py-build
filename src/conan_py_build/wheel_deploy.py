import importlib.machinery
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
    (``.so`` / ``.pyd``) on every platform .

    RPATH for the **compiled extension** is applied in ``build.py`` via
    ``patch_rpath`` **before** this step.
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


def package_dirs_with_extensions(staging_dir: Path) -> set:
    package_dirs = set()
    for pattern in ("*.so", "*.pyd"):
        for path in staging_dir.rglob(pattern):
            if not path.is_file() or path.is_symlink():
                continue
            package_dirs.add(path.parent)
    return package_dirs


def _is_python_extension_module(path: Path) -> bool:
    return any(path.name.endswith(suf) for suf in importlib.machinery.EXTENSION_SUFFIXES)


def patch_rpath(staging_dir: Path) -> None:
    """
    macOS/Linux: add ``@loader_path`` / ``$ORIGIN`` on Python extension modules.
    """
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
        if _is_python_extension_module(path) and not path.is_symlink():
            cmd = (
                [patcher, *arguments, str(path)]
            )
            try:
                subprocess.run(cmd, check=True, capture_output=True)
            except FileNotFoundError:
                print(
                    f"WARNING: {patcher} not found. Python extension {path.name} may not load "
                    f"shared libs. Install {patcher} or run auditwheel repair on the wheel {path.name}.",
                    flush=True,
                )
                warned = True
            except subprocess.CalledProcessError:
                pass
