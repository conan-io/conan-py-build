from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import get


class HelloConan(ConanFile):
    name = "hello"
    # conan-py-build exports this folder with a plain `conan export`, so the recipe sets its version
    version = "0.1.0"
    description = "Hello World C++ library used in the Conan tutorials"
    license = "MIT"
    homepage = "https://github.com/conan-io/libhello"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    implements = ["auto_shared_fpic"]
    generators = "CMakeToolchain", "CMakeDeps"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # From ConanCenter, like any other dependency
        self.requires("fmt/12.1.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["hello"]
