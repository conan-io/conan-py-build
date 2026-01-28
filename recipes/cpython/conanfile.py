import os
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, copy
from conan.errors import ConanInvalidConfiguration
from conan.tools.scm import Version


required_conan_version = ">=2"


class CpythonPortableConan(ConanFile):
    name = "cpython-portable"
    package_type = "application"
    description = "Portable CPython from python-build-standalone."
    topics = ("python", "installer", "portable")
    homepage = "https://github.com/astral-sh/python-build-standalone"
    license = "PSF-2.0"
    settings = "os", "arch"

    def validate(self):
        if self.settings.arch == "x86" and self.settings.os != "Windows":
            raise ConanInvalidConfiguration("CPython binaries for x86 architecture are only provided for Windows. ")
        if self.settings.os == "Windows" and self.settings.arch == "armv8" and Version(self.version) < "3.11.14":
            raise ConanInvalidConfiguration("CPython prebuilt binaries for Windows arm64 are not provided for this version.")
        if self.settings.arch not in ["x86_64", "armv8", "x86"]:
            raise ConanInvalidConfiguration("CPython binaries are only provided for x86_64, armv8 and x86 (Windows). ")

    def build(self):
        arch = str(self.settings.arch)
        get(self, **self.conan_data["sources"][self.version][str(self.settings.os)][arch],
            destination=self.source_folder)

    def package(self):
        copy(self, "*", src=os.path.join(self.build_folder, "python"), dst=self.package_folder)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]

        if self.settings.os == "Windows":
            self.cpp_info.bindirs = ["."]

        bindir = Path(self.package_folder) / (self.cpp_info.bindirs[0] if self.cpp_info.bindirs else ".")
        python_exe = bindir / "python3"
        if not python_exe.exists():
            python_exe = bindir / "python"
        if not python_exe.exists() and self.settings.os == "Windows":
            python_exe = bindir / "python.exe"

        if python_exe.exists():
            python_root = python_exe.parent.parent if python_exe.parent.name == "bin" else python_exe.parent
            self.runenv_info.define("Python3_ROOT", str(python_root))
            self.buildenv_info.define("Python3_ROOT", str(python_root))
