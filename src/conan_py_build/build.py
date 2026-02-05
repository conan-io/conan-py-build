import ast
import io
import os
import shutil
import tarfile
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

from conan.api.conan_api import ConanAPI
from conan.cli.cli import Cli
from conan.tools.env import VirtualBuildEnv
from distlib.wheel import Wheel
from packaging.tags import sys_tags
from packaging.utils import canonicalize_name
from pyproject_metadata import StandardMetadata


try:
    import tomllib
except ImportError:
    import tomli as tomllib


def _get_wheel_tags() -> dict:
    """
    Get wheel tags for the target platform.

    If WHEEL_ARCH environment variable is set (e.g., from a Conan profile's [buildenv]),
    uses the environment variables:
        - WHEEL_PYVER: Python version tag (e.g., "cp312", "py3")
        - WHEEL_ABI: ABI tag (e.g., "cp312", "abi3", "none")
        - WHEEL_ARCH: Platform tag (e.g., "manylinux_2_28_x86_64", "win_amd64")

    Otherwise, auto-detects tags from the current platform using packaging library.
    """
    # Check for cross-compile env vars (typically set by Conan profile [buildenv])
    wheel_arch = os.environ.get("WHEEL_ARCH")
    if wheel_arch:
        tags = {
            "pyver": [os.environ.get("WHEEL_PYVER", "py3")],
            "abi": [os.environ.get("WHEEL_ABI", "none")],
            "arch": [wheel_arch],
        }
        print(f"  Using wheel tags from environment: {tags}")
        return tags

    # Default: auto-detect from current platform
    tag = next(sys_tags())
    return {
        "pyver": [tag.interpreter],
        "abi": [tag.abi],
        "arch": [tag.platform],
    }


def _read_pyproject() -> dict:
    """Read and parse pyproject.toml from current directory."""
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        raise FileNotFoundError("pyproject.toml not found in current directory")

    with open(pyproject_path, "rb") as f:
        return tomllib.load(f)


def _get_project_metadata() -> dict:
    """Extract project metadata from pyproject.toml."""
    pyproject = _read_pyproject()
    return pyproject.get("project", {})


def _read_version_from_file(path: Path) -> Optional[str]:
    """Read __version__ from a Python file (module-level string literal only)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            value = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            target = node.target
            value = node.value
        else:
            continue
        if isinstance(target, ast.Name) and target.id == "__version__":
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                return value.value
            return None
    return None


def _get_version_from_config(source_dir: Path) -> Optional[str]:
    """Read version from [tool.conan-py-build] version-file if set."""
    tool = _read_pyproject().get("tool", {}).get("conan-py-build", {})
    version_file = tool.get("version-file")
    if not version_file:
        return None
    resolved = (source_dir / version_file).resolve()
    try:
        resolved.relative_to(source_dir.resolve())
    except ValueError:
        raise RuntimeError(
            f"version-file must be inside project: {version_file!r}"
        )
    return _read_version_from_file(resolved)


def _resolve_version(project_metadata: dict, source_dir: Path) -> str:
    version = project_metadata.get("version")
    dynamic = project_metadata.get("dynamic")
    version_is_dynamic = isinstance(dynamic, list) and "version" in dynamic

    if not version:
        version = _get_version_from_config(source_dir)
        if version_is_dynamic and not version:
            raise RuntimeError(
                "dynamic = [\"version\"] but version could not be resolved. "
                "Set [tool.conan-py-build] version-file to a file with __version__ = \"x.y.z\" at module level."
            )

    version = version or "0.0.0"
    project_metadata["version"] = version
    return version


def _normalize_name(name: str) -> str:
    canonical = canonicalize_name(name)
    return canonical.replace("-", "_")


def _parse_config(config_settings: Optional[dict]) -> dict:
    """
    Parse settings from config_settings.

    Supported config_settings:
        host-profile: Conan profile for the host context (default: "default")
        build-profile: Conan profile for the build context (default: "default")
        build-dir: Directory for build artifacts (default: temp directory, deleted after build)
    """
    config = config_settings or {}

    return {
        "host_profile": config.get("host-profile") or "default",
        "build_profile": config.get("build-profile") or "default",
        "build_dir": config.get("build-dir"),
    }


@contextmanager
def _build_directory(build_dir: Optional[str]):
    """Context manager for build directory - persistent or temporary."""
    if build_dir:
        path = Path(build_dir)
        path.mkdir(parents=True, exist_ok=True)
        print(f"Using persistent build directory: {path}")
        yield path
    else:
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)


def _write_metadata_file(dist_info_dir: Path, metadata: dict):
    """Write the METADATA file to dist-info directory."""
    metadata_path = dist_info_dir / "METADATA"
    # StandardMetadata rejects project.version if project.dynamic contains
    # "version". We resolved it, so remove from dynamic.
    project = dict(metadata)
    dynamic = project.get("dynamic")
    if isinstance(dynamic, list) and "version" in dynamic:
        project["dynamic"] = [f for f in dynamic if f != "version"]
    pyproject = {"project": project}
    std_metadata = StandardMetadata.from_pyproject(pyproject, project_dir=Path.cwd())
    with metadata_path.open("w", encoding="utf-8") as f:
        f.write(str(std_metadata.as_rfc822()))


def _create_dist_info(staging_dir: Path, metadata: dict) -> Path:
    """Create .dist-info directory with metadata files."""
    name = _normalize_name(metadata.get("name", "unknown"))
    version = metadata.get("version", "0.0.0")

    dist_info_dir = staging_dir / f"{name}-{version}.dist-info"
    dist_info_dir.mkdir(parents=True, exist_ok=True)

    _write_metadata_file(dist_info_dir, metadata)

    return dist_info_dir


# PEP 517 Hooks


def get_requires_for_build_wheel(config_settings: Optional[dict] = None) -> list:
    """PEP 517 hook: Return additional dependencies needed to build a wheel."""
    return []


def get_requires_for_build_sdist(config_settings: Optional[dict] = None) -> list:
    """PEP 517 hook: Return additional dependencies needed to build an sdist."""
    return []


def build_wheel(
    wheel_directory: str,
    config_settings: Optional[dict] = None,
    metadata_directory: Optional[str] = None,
) -> str:
    """
    PEP 517 hook: Build a wheel from the source tree.

    Note: prepare_metadata_for_build_wheel is not implemented, so
    metadata_directory is ignored if provided.
    """

    if metadata_directory is not None:
        print(f"WARNING: metadata_directory provided: '{metadata_directory}' - " \
               "backend will ignore/recreate dist-info.")

    wheel_dir = Path(wheel_directory)
    wheel_dir.mkdir(parents=True, exist_ok=True)

    source_dir = Path.cwd()
    project_metadata = _get_project_metadata()
    version = _resolve_version(project_metadata, source_dir)
    name = _normalize_name(project_metadata.get("name", "unknown"))

    print(f"Building wheel for {name}...")

    config = _parse_config(config_settings)

    with _build_directory(config["build_dir"]) as base_dir:
        return _do_build_wheel(
            source_dir,
            base_dir,
            wheel_dir,
            name,
            version,
            project_metadata,
            config,
        )


def _do_build_wheel(
    source_dir: Path,
    base_dir: Path,
    wheel_dir: Path,
    name: str,
    version: str,
    project_metadata: dict,
    config: dict,
) -> str:
    """Internal function that performs the actual wheel build."""
    
    # Staging = wheel platlib; build tree stays outside via cmake_layout.
    staging_dir = base_dir / "package"
    package_dir = base_dir / "package" / name
    package_dir.mkdir(parents=True, exist_ok=True)

    src_python_dir = source_dir / "src" / name
    if src_python_dir.exists():
        shutil.copytree(src_python_dir, package_dir, dirs_exist_ok=True)

    build_folder_conf = f"tools.cmake.cmake_layout:build_folder={(base_dir / 'build').resolve()}"
    user_presets_conf = "tools.cmake.cmaketoolchain:user_presets="  # empty = disable CMakeUserPresets.json


    # TODO: Consider isolating builds by setting CONAN_HOME to a temporary
    # directory
    api = ConanAPI()
    cli = Cli(api)
    cli.add_commands()

    host_profile = config["host_profile"]
    build_profile = config["build_profile"]

    # Auto-detect default profile if using defaults
    if host_profile == "default" or build_profile == "default":
        print("Detecting default Conan profile...", flush=True)
        api.command.run(["profile", "detect", "--force"])

    print(
        f"Running conan build (profiles: host={host_profile}, build={build_profile})...",
        flush=True,
    )
    # -of staging_dir: conanfile.package_folder = staging_dir, so
    # cmake.install() installs there. 
    # -c build_folder: build tree goes to
    # base_dir/build, not inside staging.
    try:
        result = api.command.run(
            [
                "build",
                ".",
                "-of",
                str(staging_dir),
                "-c",
                build_folder_conf,
                "-c",
                user_presets_conf,
                "--build=missing",
                f"-pr:h={host_profile}",
                f"-pr:b={build_profile}",
            ]
        )
    except Exception as e:
        raise RuntimeError(f"Conan build failed: {e}") from e

    deps_graph = result.get("graph")

    # Ensure __init__.py exists
    init_file = package_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text(f'"""Package {name}."""\n')

    # Create dist-info
    _create_dist_info(staging_dir, project_metadata)

    # Build wheel using distlib. Apply Conan's buildenv to get cross-compile
    # wheel tags from [buildenv]
    conanfile = deps_graph.root.conanfile
    buildenv = VirtualBuildEnv(conanfile)
    env_vars = buildenv.environment().vars(conanfile)

    with env_vars.apply():
        tags = _get_wheel_tags()
        wheel_name = _build_wheel_with_tags(wheel_dir, staging_dir, name, version, tags)

    return wheel_name


def _build_wheel_with_tags(
    wheel_dir: Path, staging_dir: Path, name: str, version: str, tags: dict
) -> str:
    """Build the wheel file with the given tags."""
    whl = Wheel()
    whl.name = name
    whl.version = version
    whl.dirname = str(wheel_dir)

    paths = {"platlib": str(staging_dir)}
    wheel_path = whl.build(paths, tags=tags, wheel_version=(1, 0))

    wheel_name = Path(wheel_path).name
    print(f"Built wheel: {wheel_name}")
    return wheel_name


# FIXME: This implementation is too basic and needs improvement.
def build_sdist(sdist_directory: str, config_settings: Optional[dict] = None) -> str:
    """
    PEP 517 hook: Build a source distribution (sdist).
    """
    sdist_dir = Path(sdist_directory)
    sdist_dir.mkdir(parents=True, exist_ok=True)

    source_dir = Path.cwd()
    project_metadata = _get_project_metadata()
    version = _resolve_version(project_metadata, source_dir)
    name = project_metadata.get("name", "unknown")
    sdist_name = f"{name}-{version}"
    sdist_filename = f"{sdist_name}.tar.gz"

    print(f"Building sdist: {sdist_filename}")

    include_patterns = [
        "pyproject.toml",
        "CMakeLists.txt",
        "conanfile.py",
        "cmake",
        "src",
        "include",
        "README.md",
        "README.rst",
        "LICENSE",
    ]

    exclude_patterns = [
        "__pycache__",
        "*.pyc",
        "*.pyo",
        ".git",
        ".gitignore",
        "build",
        "dist",
        "*.egg-info",
        ".eggs",
    ]

    def should_exclude(path: Path) -> bool:
        name = path.name
        for pattern in exclude_patterns:
            if pattern.startswith("*"):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern:
                return True
        return False

    sdist_path = sdist_dir / sdist_filename

    with tarfile.open(sdist_path, "w:gz", format=tarfile.PAX_FORMAT) as tar:
        for pattern in include_patterns:
            source_path = source_dir / pattern
            if source_path.exists():
                if source_path.is_file():
                    arcname = f"{sdist_name}/{pattern}"
                    tar.add(source_path, arcname=arcname)
                elif source_path.is_dir():
                    for file_path in source_path.rglob("*"):
                        if file_path.is_file() and not should_exclude(file_path):
                            rel_path = file_path.relative_to(source_dir)
                            arcname = f"{sdist_name}/{rel_path}"
                            tar.add(file_path, arcname=arcname)

        pkg_info_lines = [
            "Metadata-Version: 2.1",
            f"Name: {name}",
            f"Version: {version}",
        ]
        if "description" in project_metadata:
            pkg_info_lines.append(f"Summary: {project_metadata['description']}")

        pkg_info_data = "\n".join(pkg_info_lines).encode("utf-8")
        pkg_info_file = tarfile.TarInfo(name=f"{sdist_name}/PKG-INFO")
        pkg_info_file.size = len(pkg_info_data)
        tar.addfile(pkg_info_file, io.BytesIO(pkg_info_data))

    print(f"Built sdist: {sdist_filename}")
    return sdist_filename
