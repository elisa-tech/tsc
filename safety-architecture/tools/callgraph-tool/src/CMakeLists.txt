cmake_minimum_required(VERSION 3.5.1)
project(XCALLGRAPH)

set(LLVM_MIN_MAJOR_VERSION "10")
find_package(LLVM REQUIRED)
if(LLVM_FOUND)
    if(LLVM_VERSION_MAJOR LESS ${LLVM_MIN_MAJOR_VERSION})
        message(FATAL_ERROR 
        "\nFound LLVM: ${LLVM_VERSION}, but the required "
        "minimum version is ${LLVM_MIN_MAJOR_VERSION}.0.0")
    endif()
endif()

message(STATUS "Found LLVM ${LLVM_PACKAGE_VERSION}")
message(STATUS "Using LLVMConfig.cmake in: ${LLVM_DIR}")

include_directories(${LLVM_INCLUDE_DIRS})
add_definitions(${LLVM_DEFINITIONS})

add_subdirectory(lib)
