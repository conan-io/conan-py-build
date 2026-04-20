project('myadder_meson_pybind11', 'cpp',
    version: '0.1.0',
    default_options: ['cpp_std=c++17'],
)

py = import('python').find_installation('python3')

pybind11_dep = dependency('pybind11')
fmt_dep = dependency('fmt')

py.extension_module('_core',
    'src/myadder.cpp',
    dependencies: [pybind11_dep, fmt_dep],
    install: true,
    install_dir: 'myadder_meson_pybind11',
)
