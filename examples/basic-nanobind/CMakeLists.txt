cmake_minimum_required(VERSION 3.15)
project(myadder_nanobind LANGUAGES CXX)

find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)

find_package(nanobind CONFIG REQUIRED)
find_package(fmt REQUIRED)

# nanobind_add_module links the nanobind runtime internally; no need for nanobind::nanobind
nanobind_add_module(_core src/myadder.cpp)

target_link_libraries(_core PRIVATE fmt::fmt)

install(TARGETS _core DESTINATION myadder_nanobind)
