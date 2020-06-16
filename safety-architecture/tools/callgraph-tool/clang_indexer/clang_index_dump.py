#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import csv
import os
import sys
import logging
from typing import NamedTuple

from clang_download import update_clang
import astparser
import utils

_LOGGER = logging.getLogger(utils.LOGGER_NAME)
_FILEDIR = os.path.dirname(os.path.realpath(__file__))

################################################################################


class CsvRow(NamedTuple):
    filename: str
    line: str
    col: str
    kind: str
    displayname: str
    usr: str
    isdef: str
    typestr: str
    typedef: str
    reference: str


class ClangIndexDumper():

    def __init__(self):
        self.csvwriter = None
        self.astparser = None

    def dump_index(self, csvfile, compdb, append_arg=None, srcfile=None):
        self.csvwriter = utils.CsvWriter(csvfile)
        self._write_header()

        # Let AstParser parse the AST tree, calling
        # self.ast_tree_dump() for all the translation unit root nodes
        self.astparser = astparser.AstParser(compdb, append_arg, srcfile)
        self.astparser.walk_tree(callback=self.ast_tree_dump)
        self.csvwriter.close()

    def _write_header(self):
        header = [m for m in vars(CsvRow).keys() if not m.startswith("_")]
        self.csvwriter.write_arr(header)

    def _write_row(self, csvrow_namedtuple):
        self.csvwriter.write_arr(list(csvrow_namedtuple))

    def ast_tree_dump(self, node):
        # Skip if already indexed
        if self.astparser.is_indexed(str(node.location.file)):
            return

        filename = str(node.location.file)
        typedef = ""
        if node.kind == cl.CursorKind.TYPEDEF_DECL.value:
            typedef = node.underlying_typedef_type.spelling
        usr = node.get_usr()
        reference = node.referenced.get_usr() if node.referenced else ""

        row = CsvRow(
            filename=filename,
            line=node.location.line,
            col=node.location.column,
            kind=node.kind,
            displayname=node.displayname,
            usr=usr,
            isdef=node.is_definition(),
            typestr=node.type.spelling,
            typedef=typedef,
            reference=reference,
        )
        self._write_row(row)

        # Recursively iterate all children
        children = list(node.get_children())
        for child in children:
            self.ast_tree_dump(child)


################################################################################


def add_args(parser):
    desc = "Dump nodes from clang AST index based on compilation database "\
        " (compile_commands.json)."
    epil = "Example: ./%s --compdb ~/linux-stable/compile_commands.json" % \
        os.path.basename(__file__)
    parser.description = desc
    parser.epilog = epil

    help = "Set the output file name, default is 'cindex.csv'"
    parser.add_argument('--out', nargs='?', help=help, default='cindex.csv')

    return parser

################################################################################


if __name__ == "__main__":
    parser = utils.clang_common_args(_FILEDIR)
    add_args(parser)
    args = parser.parse_args()
    utils.handle_common_args(parser, args)

    astparser.set_clang_bindings_and_lib(args.cindexpy, args.libclang)
    import clang.cindex as cl

    index = ClangIndexDumper()
    index.dump_index(
        csvfile=args.out,
        compdb=args.compdb,
        append_arg=args.append_arg,
        srcfile=args.file,
    )

################################################################################
