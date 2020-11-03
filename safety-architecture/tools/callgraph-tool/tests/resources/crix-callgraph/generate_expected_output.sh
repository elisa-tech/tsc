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
exit_unless_command_exists csvsql
exit_unless_command_exists csvformat

make expected_calls

# Remove entries where caller or callee function name begins with '__cxx'.
# These are library functions we don't want to include into the
# expected_calls.csv
csvsql --query \
    "select distinct * from expected_calls where caller_function not like '__cxx%' and callee_function not like '__cxx%'"\
    expected_calls.csv | csvformat -U1 > expected_calls.csv.temp

mv expected_calls.csv.temp expected_calls.csv
sort expected_calls.csv -o expected_calls.csv

popd >/dev/null

################################################################################