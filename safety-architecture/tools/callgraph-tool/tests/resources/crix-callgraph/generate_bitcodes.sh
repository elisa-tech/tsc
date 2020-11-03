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
make progs
make progs-cxx
make cg-test-template
make test-opt
make test-same-funcname

popd >/dev/null

################################################################################
