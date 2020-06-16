#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import csv
import os
import sys
import hashlib
import logging
import argparse
import clang_download

from colorlog import ColoredFormatter, default_log_colors
from typing import NamedTuple

LOGGER_NAME = "clang-indexer"
LOG_SPAM = logging.DEBUG - 1
_LOGGER = logging.getLogger(LOGGER_NAME)
_FILEDIR = os.path.dirname(os.path.realpath(__file__))

###############################################################################


class CsvWriter():
    def __init__(self, filename):
        self.filename = filename
        self.fp = open(self.filename, 'w')
        self.writer = csv.writer(self.fp, delimiter=',', quoting=csv.QUOTE_ALL)

    def write_arr(self, elems):
        self.writer.writerow(elems)

    def close(self):
        self.fp.close()
        _LOGGER.info("Wrote: %s" % self.filename)


################################################################################


def filter_list(lst, blacklist):
    return [x for x in lst if x not in blacklist]


def blacklist_file(filepath, blacklist):
    return any([bl in filepath for bl in blacklist])


def exit_unless_accessible(filename):
    if filename and not os.path.isfile(filename):
        _LOGGER.error(
            "File not found or no permissions: \"%s\"" % filename)
        sys.exit(1)


def find_first(name, path):
    for root, _dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)


def obj_to_str(obj, level=0, maxdepth=1):
    LEAFTYPES = (int, float, str, list, dict, set)
    INDENT = "    "

    if level == maxdepth:
        return "...\n"
    _class = str(obj.__class__)
    ret = "%s\n" % (_class)

    for item in sorted(dir(obj)):
        if not (item.startswith("_")):
            ret += "%s%s = " % ((level + 1) * INDENT, item)
            try:
                attr = getattr(obj, item)
                if isinstance(attr, LEAFTYPES):
                    ret += "%s\n" % attr
                else:
                    ret += "%s" % obj_to_str(attr, level + 1, maxdepth)
            except (AssertionError, Exception):
                ret += "<unresolved>\n"
    return ret


def setup_logging(verbosity=1):
    project_logger = logging.getLogger(LOGGER_NAME)

    if verbosity == 0:
        level = logging.NOTSET
    elif verbosity == 1:
        level = logging.INFO
    elif verbosity == 2:
        level = logging.DEBUG
    else:
        level = LOG_SPAM

    log_colors = default_log_colors
    if level < logging.DEBUG:
        logformat = \
            "%(log_color)s%(levelname)-8s%(reset)s "\
            "%(filename)s:%(lineno)d:%(funcName)s(): %(message)s"
    else:
        logformat = "%(log_color)s%(levelname)-8s%(reset)s %(message)s"

    default_log_colors['ERROR'] = 'bold_red'
    default_log_colors['INFO'] = 'fg_bold_white'
    default_log_colors['SPAM'] = 'fg_bold_black'
    default_log_colors['DEBUG'] = 'fg_white'
    formatter = ColoredFormatter(logformat, log_colors=log_colors)
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    logging.addLevelName(LOG_SPAM, "SPAM")
    project_logger.addHandler(stream)
    project_logger.setLevel(level)


def download_missing_default_clang(argval, defval):
    if not os.path.isfile(argval):
        if defval == argval:
            clang_download.update_clang('./clang')


def clang_common_args(scriptdir):
    parser = argparse.ArgumentParser()
    help = "File path to target file (to make the script generate AST "\
        "index only for the specified translation unit (file) instead "\
        "of all translation units in the COMPDB"
    parser.add_argument('--file', help=help, default=None)

    required_named = parser.add_argument_group('required named arguments')
    help = "File path to compilation database (generated e.g. with bear)"
    required_named.add_argument('--compdb', help=help, required=True)

    help = "File path to libclang dynamic library (libclang.so)"
    path = os.path.join(scriptdir, 'clang/bin/lib/libclang.so')
    parser.add_argument('--libclang', help=help, default=path)

    help = "File path to libclang python bindings (cindex.py)"
    path = os.path.join(scriptdir, 'clang/src/bindings/python/clang/cindex.py')
    parser.add_argument('--cindexpy', help=help, default=path)

    help = "Additional string to append to clang index parse args"
    parser.add_argument('--append_arg', nargs='?', help=help, default="")

    help = "Set the verbosity level (defaults to -v or 1)"
    parser.add_argument('-v', '--verbose', action='count', default=1)

    help = "Detect system include path (defaults to 'auto')"
    parser.add_argument(
        '--isystem',
        help=help, choices=["auto", "none"], default='auto')

    help = "Project root path. If not specified, compilation database directory is used"
    parser.add_argument('--projroot', help=help, default="")

    return parser


def handle_common_args(parser, args):
    setup_logging(verbosity=args.verbose)
    exit_unless_accessible(args.compdb)
    exit_unless_accessible(args.file)
    download_missing_default_clang(args.cindexpy, parser.get_default("cindexpy"))
    download_missing_default_clang(args.libclang, parser.get_default("libclang"))
    exit_unless_accessible(args.cindexpy)
    exit_unless_accessible(args.libclang)

    # Add system headers if using the downloaded version of libclang
    if (args.isystem == "auto" and
            args.libclang == parser.get_default("libclang")):
        path = os.path.join(_FILEDIR, "clang/bin/lib/clang")
        filepath = find_first("stddef.h", path)
        filedir = os.path.dirname(filepath)
        isystem = " -isystem %s" % filedir
        args.append_arg += isystem


class CallgraphParser():
    def __init__(self, compdb, exclude):
        self.append_arg = ''
        self.cindexpy = os.path.join(_FILEDIR, 'clang/src/bindings/python/clang/cindex.py')
        self.compdb = compdb
        self.exclude = exclude
        self.file = None
        self.isystem = 'none'
        self.libclang = os.path.join(_FILEDIR, 'clang/bin/lib/libclang.so')
        self.out = 'calls.csv'
        self.projroot = ''
        self.verbose = 1

    def get_default(self, desc):
        if desc == 'libclang':
            return self.libclang
        if desc == 'cindexpy':
            return self.cindexpy
        return None

    def parse_args(self):
        return self


def setup_callgraph_parser(compdb, exclude):
    parser = CallgraphParser(compdb, exclude)
    return parser


################################################################################
