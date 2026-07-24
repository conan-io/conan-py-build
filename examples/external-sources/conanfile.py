import sys

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get
from conan.tools.microsoft import is_msvc


class HelloBindingsConan(ConanFile):
    name = "hello-bindings"
    description = "Python bindings for libhello (C++ code fetched from GitHub)"
    license = "MIT"
    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}
    generators = "CMakeDeps"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("pybind11/3.0.1")
        self.requires("fmt/12.1.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            destination="libhello",
            strip_root=True)

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
