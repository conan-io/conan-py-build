import importlib.machinery
import shutil
import subprocess
import sys
from pathlib import Path


def move_deploy_to_wheel(
    deploy_folder: Path, staging_dir: Path
) -> None:
    """
    Move contents of Conan's runtime_deploy to the wheel staging root.
    """
    deploy_folder = Path(deploy_folder)
    staging_dir = Path(staging_dir)
    if not deploy_folder.is_dir() or not any(deploy_folder.iterdir()):
        return
    staging_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(deploy_folder, staging_dir, dirs_exist_ok=True)


def _is_python_extension_module(path: Path) -> bool:
    if path.is_symlink():
        return False
    return any(path.name.endswith(suf) for suf in importlib.machinery.EXTENSION_SUFFIXES)


def patch_rpath(staging_dir: Path) -> None:
    """
    macOS/Linux: add ``@loader_path/..`` / ``$ORIGIN/..`` on Python extension modules.
    """
    if sys.platform == "darwin":
        rpath = "@loader_path/.."
        patcher = "install_name_tool"
        arguments = ["-add_rpath", rpath]
    elif sys.platform == "linux":
        rpath = "$ORIGIN/.."
        patcher = "patchelf"
        arguments = ["--add-rpath", rpath]
    else:
        return

    warned = False
    for path in staging_dir.rglob("*.so"):
        if _is_python_extension_module(path):
            try:
                subprocess.run([patcher, *arguments, str(path)],
                                check=True, capture_output=True, text=True)
            except FileNotFoundError:
                print(
                    f"WARNING: {patcher} not found. Python extension {path.name} may not load "
                    f"shared libs. Install {patcher} or run auditwheel repair on the wheel {path.name}.",
                    flush=True,
                )
                warned = True
            except subprocess.CalledProcessError:
                pass
