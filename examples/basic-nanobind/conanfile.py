from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MyadderNanobindConan(ConanFile):
    name = "myadder-nanobind"
    version = "0.1.0"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("nanobind/2.9.2")
        self.requires("fmt/12.1.0")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.install()
