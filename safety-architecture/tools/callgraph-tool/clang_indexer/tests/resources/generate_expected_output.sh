#!/bin/bash

# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

MYNAME=$(basename $0)

################################################################################

pwd=$(pwd)
scriptdir=$(realpath $(dirname "$0"))

if [[ ! $pwd == $scriptdir ]]; then
    echo "Error: '$MYNAME': invalid working directory"
    echo "Hint: execute the script in the same directory where '$MYNAME' is located"
    exit 1
fi

out=expected_calls.csv

if [ -f $out ]; then
    printf "This will overwrite existing '$out', continue? (y/N): "
    read answer
    case $answer in
        [yY]) ;; # continue
        *) echo "Cancelled" && exit 0 ;; # otherwise cancel
    esac
fi

if bash generate_compile_commands.sh && \
python3 ../../clang_find_calls.py --compdb compile_commands.json --out $out; then
    echo -e "\033[32mWrote: $out\033[0m\n"
fi

################################################################################
