from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class HelloLocalConan(ConanFile):
    name = "hello-local"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        # No remote has a recipe for hello: it comes from recipes/hello, see local-recipes in pyproject.toml
        self.requires("hello/0.1.0")
        self.requires("pybind11/3.0.1")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
