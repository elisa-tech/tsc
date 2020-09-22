#!/bin/bash

export CLANG_BIN_DIR=/usr/lib/llvm-10/bin/

if [ ! -d $CLANG_BIN_DIR ]; then
    echo "Error: '$CLANG_BIN_DIR' does not exist."
    echo "Install clang-10 (sudo apt install clang-10) and try again."
    return 
fi

export LLVM_COMPILER=clang
export WLLVM_OUTPUT_LEVEL=WARNING
export WLLVM_OUTPUT_FILE=/tmp/wrapper.log
export PATH=${CLANG_BIN_DIR}:${PATH}
