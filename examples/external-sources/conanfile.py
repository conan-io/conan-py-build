from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import get
from conan.tools.microsoft import is_msvc


class HelloBindingsConan(ConanFile):
    name = "hello-bindings"
    version = "0.1.0"
    description = "Python bindings for libhello (C++ code fetched from GitHub)"
    license = "MIT"
    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}
    generators = "CMakeToolchain", "CMakeDeps"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("pybind11/3.0.1")
        self.requires("fmt/12.1.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            destination="libhello",
            strip_root=True)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
