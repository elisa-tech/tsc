#!/bin/bash

MYNAME=$(basename $0)

################################################################################

exit_unless_command_exists () {
    if ! [ -x "$(command -v $1)" ]; then
        echo "Error: '$1' is not installed" >&2
        [ ! -z "$2" ] && echo "$2"
        exit 1
    fi
}

################################################################################

scriptdir=$(realpath $(dirname "$0"))
pushd $scriptdir >/dev/null

exit_unless_command_exists make
exit_unless_command_exists find
exit_unless_command_exists grep

if [ ! -z "$1" ]; then
    # If $1 is given, assume it's either relative or absolute
    # path to directory that contains clang binaries somewhere in the
    # directory hierarchy
    absdir=$(cd $1 2>/dev/null && pwd)
    if [ -z $absdir ] || [ ! -d $absdir ]; then
        echo "Error: '$1' does not exist."
        exit 1
    fi
    # Find the path to an executable we know should exist in the clang bin 
    # directory. From the path to executable, find the path to bin/ directory.
    CLANG_BIN_DIR=$(find $absdir -name 'clang++' -executable -print -quit 2>/dev/null | grep -oE ".*bin")
    if [ -z $CLANG_BIN_DIR ]; then
        echo "Error: could not find clang binary directory from '$absdir'"
        exit 1
    fi
else
    CLANG_BIN_DIR=/usr/lib/llvm-10/bin
fi
echo "Using CLANG_BIN_DIR=${CLANG_BIN_DIR}"
if [ ! -d $CLANG_BIN_DIR ]; then
    echo "Error: '$CLANG_BIN_DIR' does not exist."
    exit 1
fi

if [ ! -z "$2" ]; then
    LLVM_VERSION=$2
else
    LLVM_VERSION="10.0.0"
fi
echo "Using LLVM_VERSION=${LLVM_VERSION}"

make CLANG_BIN_DIR=$CLANG_BIN_DIR LLVM_VERSION=$LLVM_VERSION progs
make CLANG_BIN_DIR=$CLANG_BIN_DIR LLVM_VERSION=$LLVM_VERSION progs-cxx
make CLANG_BIN_DIR=$CLANG_BIN_DIR LLVM_VERSION=$LLVM_VERSION cg-test-template
make CLANG_BIN_DIR=$CLANG_BIN_DIR LLVM_VERSION=$LLVM_VERSION test-opt
make CLANG_BIN_DIR=$CLANG_BIN_DIR LLVM_VERSION=$LLVM_VERSION test-same-funcname
make CLANG_BIN_DIR=$CLANG_BIN_DIR LLVM_VERSION=$LLVM_VERSION test-modules

popd >/dev/null

################################################################################
