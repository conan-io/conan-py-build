cmake_minimum_required(VERSION 3.15)
project(hello_bindings LANGUAGES CXX)

find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)

# Libhello is downloaded in source() to src/libhello/ (it finds fmt itself)
add_subdirectory(libhello)

# Python module that wraps hello()
pybind11_add_module(_core hello_bindings.cpp)
target_link_libraries(_core PRIVATE hello pybind11::module)
target_include_directories(_core PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/libhello/include)

if(APPLE)
    set_target_properties(_core PROPERTIES LINK_FLAGS "-undefined dynamic_lookup")
endif()

install(TARGETS _core DESTINATION hello_bindings)
