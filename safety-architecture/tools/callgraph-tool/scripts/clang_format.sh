#!/bin/bash

################################################################################

MYNAME=$0

GREEN='\033[32m'
RED='\033[31m'
YELLOW='\033[33m'
NC='\033[0m'

################################################################################

usage () {
    echo "Usage: $MYNAME [--warn] [--apply] [--style STYLE]"
    echo ""
    echo "Check/apply clang-format to C++ files in this project"
    echo ""
}

################################################################################

exit_unless_command_exists () {
    if ! [ -x "$(command -v $1)" ]; then
        echo "Error: $1 is not installed" >&2
        exit 1
    fi
}

exit_unless_file_exists () {
    if ! [ -f "$1" ]; then
        echo "File not found: $1"
        exit 1
    fi
}

################################################################################

# Transform long options to short ones
for arg in "$@"; do
  shift
  case "$arg" in
    "--help")  set -- "$@" "-h" ;;
    "--warn")  set -- "$@" "-w" ;;
    "--apply") set -- "$@" "-a" ;;
    "--style") set -- "$@" "-s" ;;
    *)         set -- "$@" "$arg"
  esac
done

warn=false; 
apply=false

# Default style is LLVM
style=LLVM

# Parse short options
OPTIND=1
while getopts "hwas:" opt
do
  case "$opt" in
    "h") usage; exit 0 ;;
    "w") warn=true ;;
    "a") apply=true ;;
    "s") style=$OPTARG ;;
    "?") usage; exit 0 ;;
    "--"*) usage; exit 1 ;;
  esac
done
# remove options from positional parameters
shift $(expr $OPTIND - 1)

exit_unless_command_exists clang-format
exit_unless_command_exists find

# Default: warn only
if [ "$apply" == "false" ]; then
    warn=true
fi

CPP_FILES_REGEX='.*\.\(cc\|h\)'
CPP_SRC_DIR='src/'
fail=false

for cppfile in $(find $CPP_SRC_DIR -regex $CPP_FILES_REGEX); do
    diff_ret=$(diff -u $cppfile <(clang-format -style=LLVM $cppfile) | tee /dev/tty)
    if [ ! -z "$diff_ret" ] && [ "$warn" == "true" ]; then 
        fail=true
    fi
    if [ "$apply" == "true" ]; then
        clang-format -style=LLVM -i $cppfile
    fi
done

if [ "$fail" == "true" ]; then
    printf "${RED}Style check failed${NC}\n"
    printf "${YELLOW}Run '$MYNAME --apply' to fix${NC}\n"
    exit 1
else
    printf "${GREEN}Style check passed${NC}\n"
    exit 0
fi

################################################################################
