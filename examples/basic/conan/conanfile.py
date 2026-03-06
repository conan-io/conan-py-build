from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MyadderConan(ConanFile):
    name = "myadder"
    version = "0.1.0"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def layout(self):
        # Recipe in conan/, sources at project root (see pyproject conanfile-path)
        cmake_layout(self, src_folder="..")

    def requirements(self):
        self.requires("fmt/12.1.0")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
