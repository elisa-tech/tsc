#!/bin/bash

# SPDX-FileCopyrightText: 2020 callgraph-tool authors. All rights reserved
#
# SPDX-License-Identifier: Apache-2.0

################################################################################

MYNAME=$0

usage () {
    echo "Usage: $MYNAME [--clangdir DIR]"
    echo ""
    echo "Set environment variables for crix-callgraph"
    echo ""
}

################################################################################

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: this script needs to be sourced, not executed."
    echo "Re-run with: 'source $MYNAME $@'"
    exit 1
fi

################################################################################

# Transform long options to short ones
for arg in "$@"; do
  shift
  case "$arg" in
    "--help")     set -- "$@" "-h" ;;
    "--clangdir") set -- "$@" "-c" ;;
    *)            set -- "$@" "$arg"
  esac
done

# Default
clangdir='/usr/lib/llvm-10/bin'

# Parse short options
OPTIND=1
while getopts "hc:" opt
do
  case "$opt" in
    "h") usage; return ;;
    "c") clangdir=$OPTARG ;;
    "?") usage; return ;;
    "--"*) usage; return ;;
  esac
done
# remove options from positional parameters
shift $(expr $OPTIND - 1)

################################################################################

# $clangdir now contains either relative or absolute
# path to directory that contains clang binaries somewhere in the
# directory hierarchy
absdir=$(cd $clangdir 2>/dev/null && pwd)
if [ -z $absdir ] || [ ! -d $absdir ]; then
    echo "Error: '$clangdir' does not exist."
    return 
fi
# Find the path to an executable we know should exist in the clang bin 
# directory. From the path to executable, find the path to bin/ directory.
CLANG_BIN_DIR=$(find $absdir -name 'clang++' -executable -print -quit 2>/dev/null | grep -oE ".*bin")
if [ -z $CLANG_BIN_DIR ]; then
    echo "Error: could not find clang binary directory from '$absdir'"
    return
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

################################################################################
