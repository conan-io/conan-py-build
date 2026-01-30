cmake_minimum_required(VERSION 3.15)
project(myadder_pybind11 LANGUAGES CXX)

find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)
find_package(fmt REQUIRED)

pybind11_add_module(_core src/myadder.cpp)
target_link_libraries(_core PRIVATE pybind11::module fmt::fmt)

if(APPLE)
    set_target_properties(_core PROPERTIES LINK_FLAGS "-undefined dynamic_lookup")
endif()
