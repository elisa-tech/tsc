#!/bin/bash

# SPDX-FileCopyrightText: 2020 callgraph-tool authors. All rights reserved
#
# SPDX-License-Identifier: Apache-2.0

if [ "$1" == "clang_download" ]; then
    export CLANG_BIN_DIR=$(dirname "$(realpath -s "$BASH_SOURCE")")/clang/bin/bin
else
    export CLANG_BIN_DIR=/usr/lib/llvm-10/bin/
fi
echo "Using CLANG_BIN_DIR=${CLANG_BIN_DIR}"
if [ ! -d $CLANG_BIN_DIR ]; then
    echo "Error: '$CLANG_BIN_DIR' does not exist."
    return 
fi

export LLVM_COMPILER=clang
export WLLVM_OUTPUT_LEVEL=WARNING
export WLLVM_OUTPUT_FILE=/tmp/wrapper.log
PATH=${CLANG_BIN_DIR}:${PATH}:${HOME}/.local/bin/
# Remove duplicates from the PATH, preserving order
PATH=$(n= IFS=':'; for e in $PATH; do [[ :$n == *:$e:* ]] || n+=$e:; done; echo "${n:0: -1}")
export PATH=${PATH}