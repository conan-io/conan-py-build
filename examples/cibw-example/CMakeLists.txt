cmake_minimum_required(VERSION 3.15)
project(myxslt_cibw LANGUAGES CXX)

find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)
find_package(LibXslt REQUIRED)
find_package(LibXml2 REQUIRED)

pybind11_add_module(_core src/myxslt.cpp)
target_link_libraries(_core PRIVATE pybind11::module LibXslt::LibXslt LibXml2::LibXml2)

install(TARGETS _core DESTINATION myxslt_cibw)
