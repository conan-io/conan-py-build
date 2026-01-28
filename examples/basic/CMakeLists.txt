cmake_minimum_required(VERSION 3.15)
project(myadder LANGUAGES CXX)


find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
message(STATUS "Python3_EXECUTABLE: ${Python3_EXECUTABLE}")
message(STATUS "Python3_VERSION: ${Python3_VERSION}")
message(STATUS "Python3_INCLUDE_DIRS: ${Python3_INCLUDE_DIRS}")
message(STATUS "Python3_LIBRARIES: ${Python3_LIBRARIES}")
message(STATUS "Python3_LIBRARY_DIRS: ${Python3_LIBRARY_DIRS}")

find_package(fmt REQUIRED)

Python3_add_library(_core MODULE src/myadder.cpp)
target_link_libraries(_core PRIVATE fmt::fmt)

execute_process(
    COMMAND ${Python3_EXECUTABLE} -c "import sysconfig; print(sysconfig.get_config_var('EXT_SUFFIX'))"
    OUTPUT_VARIABLE PYTHON_EXT_SUFFIX
    OUTPUT_STRIP_TRAILING_WHITESPACE
)

set_target_properties(_core PROPERTIES
    PREFIX ""
    SUFFIX "${PYTHON_EXT_SUFFIX}"
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
)

if(APPLE)
    set_target_properties(_core PROPERTIES
        LINK_FLAGS "-undefined dynamic_lookup"
    )
endif()
