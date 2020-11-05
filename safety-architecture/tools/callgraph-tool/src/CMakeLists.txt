# SPDX-FileCopyrightText: 2020 callgraph-tool authors. All rights reserved
#
# SPDX-License-Identifier: LicenseRef-LLVM

cmake_minimum_required(VERSION 3.5.1)
project(CALLGRAPH)

message(STATUS "LLVM_MIN_VERSION=${LLVM_MIN_VERSION}")
find_package(LLVM ${LLVM_MIN_VERSION} REQUIRED)

message(STATUS "Found LLVM ${LLVM_PACKAGE_VERSION}")
message(STATUS "Using LLVMConfig.cmake in: ${LLVM_DIR}")

include_directories(${LLVM_INCLUDE_DIRS})
add_definitions(${LLVM_DEFINITIONS})

add_subdirectory(lib)
