import sys

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MyadderPybind11Conan(ConanFile):
    name = "myadder-pybind11"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("pybind11/3.0.1")
        self.requires("fmt/12.1.0")

    def generate(self):
        tc = CMakeToolchain(self)
        # Build against the interpreter driving the build.
        tc.cache_variables["Python3_EXECUTABLE"] = sys.executable
        tc.cache_variables["Python_EXECUTABLE"] = sys.executable
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
