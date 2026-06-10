from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MyXsltCibwConan(ConanFile):
    name = "myxslt-cibw"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("pybind11/3.0.1")
        self.requires("libxslt/1.1.42")  # pulls libxml2 -> zlib

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
