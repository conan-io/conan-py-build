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

        self.run(f'{python} -c "import platform;print(platform.platform())"', output, env="conanrun")
        if self.settings.os == "Macos":
            arch = "arm64" if self.settings.arch == "armv8" else str(self.settings.arch)
            output_str = str(output.getvalue())
            assert arch in output_str