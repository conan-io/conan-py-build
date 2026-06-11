cmake_minimum_required(VERSION 3.15)
project(fmt_cython LANGUAGES CXX)

find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
find_package(fmt REQUIRED)

add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/_fmt.cpp
    COMMAND ${Python3_EXECUTABLE} -m cython
            --cplus -3
            ${CMAKE_CURRENT_SOURCE_DIR}/src/fmt_cython/_fmt.pyx
            -o ${CMAKE_CURRENT_BINARY_DIR}/_fmt.cpp
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/src/fmt_cython/_fmt.pyx
    VERBATIM
)

Python3_add_library(_fmt MODULE ${CMAKE_CURRENT_BINARY_DIR}/_fmt.cpp)
target_link_libraries(_fmt PRIVATE fmt::fmt)
target_include_directories(_fmt PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src/fmt_cython)

install(TARGETS _fmt DESTINATION "fmt_cython")
