#!/bin/bash

# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

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
exit_unless_command_exists bear "Hint: install bear (https://github.com/rizsotto/Bear)"
if bear make && make clean-progs; then
    echo -e "\033[32mWrote: ${scriptdir}/compile_commands.json\033[0m\n"
fi

popd >/dev/null

################################################################################
