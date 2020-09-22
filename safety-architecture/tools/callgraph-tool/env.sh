#!/bin/bash
# https://stackoverflow.com/questions/35006457/choosing-between-0-and-bash-source
export CLANG_BIN_DIR=$(dirname "$(realpath -s "$BASH_SOURCE")")/clang/bin/bin

if [ ! -d $CLANG_BIN_DIR ]; then
    echo "Error: '$CLANG_BIN_DIR' does not exist"
    echo "Download clang and try again"
    return 
fi

export LLVM_COMPILER=clang
export WLLVM_OUTPUT_LEVEL=WARNING
export WLLVM_OUTPUT_FILE=/tmp/wrapper.log
export PATH=${CLANG_BIN_DIR}:${PATH}
