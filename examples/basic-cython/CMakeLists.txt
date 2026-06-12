cmake_minimum_required(VERSION 3.15)
project(myformatter LANGUAGES CXX)

find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
find_package(fmt REQUIRED)

find_program(CYTHON_EXECUTABLE NAMES cython cython3 REQUIRED)

add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/_myformatter.cpp
    COMMAND ${CYTHON_EXECUTABLE}
            --cplus -3
            ${CMAKE_CURRENT_SOURCE_DIR}/src/myformatter/_myformatter.pyx
            -o ${CMAKE_CURRENT_BINARY_DIR}/_myformatter.cpp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/src/myformatter/_myformatter.pyx
    VERBATIM
)

Python3_add_library(_myformatter MODULE ${CMAKE_CURRENT_BINARY_DIR}/_myformatter.cpp)
target_link_libraries(_myformatter PRIVATE fmt::fmt)
target_include_directories(_myformatter PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src/myformatter)

install(TARGETS _myformatter DESTINATION "myformatter")
