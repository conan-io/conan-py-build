from six import StringIO
from conan import ConanFile
from conan.tools.build import can_run
import re


class TestPackageConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        output = StringIO()
        python = "python" if self.settings.os == "Windows" else "python3"
        self.run(f"{python} --version", output, env="conanrun")
        output_str = str(output.getvalue())
        self.output.info("Installed version: {}".format(output_str))
        tokens = re.split('[@#]', self.tested_reference_str)
        require_version = tokens[0].split("/", 1)[1]
        self.output.info("Expected version: {}".format(require_version))
        assert_python_version = "Python %s" % require_version
        assert assert_python_version in output_str

        # Check Python reports the expected architecture
        self.run(f'{python} -c "import platform;print(platform.machine())"', output, env="conanrun")
        output_str = str(output.getvalue())
        # Conan arch -> platform.machine() on various OSes
        arch_map = {
            "armv8": ("arm64", "aarch64"),
            "x86_64": ("x86_64",),
            "armv7": ("armv7l",),
            "AMD64": ("AMD64",),
            "x86": ("x86",),
            "ARM64": ("ARM64", "arm64"),
        }
        expected = arch_map.get(str(self.settings.arch), (str(self.settings.arch),))
        assert any(arch in output_str for arch in expected), f"Expected one of {expected} in {output_str!r}"
