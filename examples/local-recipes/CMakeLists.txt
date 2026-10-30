cmake_minimum_required(VERSION 3.15)
project(hello_local LANGUAGES CXX)

find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)
# Packaged by the local recipe in recipes/hello
find_package(hello CONFIG REQUIRED)

pybind11_add_module(_core src/hello_local.cpp)
target_link_libraries(_core PRIVATE hello::hello)

install(TARGETS _core DESTINATION hello_local)
