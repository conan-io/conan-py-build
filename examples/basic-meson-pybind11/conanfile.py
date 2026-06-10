from conan import ConanFile
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson


class MyadderMesonPybind11Conan(ConanFile):
    name = "myadder-meson-pybind11"
    settings = "os", "compiler", "build_type", "arch"
    generators = "MesonToolchain", "PkgConfigDeps"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("pybind11/3.0.1")
        self.requires("fmt/12.1.0")

    def build_requirements(self):
        self.tool_requires("meson/[>=1.4.0 <2]")
        self.tool_requires("pkgconf/[>=2.2 <3]")

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
