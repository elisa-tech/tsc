#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
import sys
import re
import asciitree
import logging

from clang_download import update_clang
import astparser
import utils


_LOGGER = logging.getLogger(utils.LOGGER_NAME)
_FILEDIR = os.path.dirname(os.path.realpath(__file__))


################################################################################


class ClangAstTreeviewer():

    def dump_ast(
        self,
        compdb,
        append_arg=None,
        srcfile=None,
        regex=None,
    ):
        self.regex = re.compile(regex) if regex else None
        tree = {'': {}}
        self.tree = tree['']

        self.astparser = astparser.AstParser(compdb, append_arg, srcfile)
        self.ast_tree = self.astparser.get_ast_tree()
        self.ast_tree.walk_tu_heads(self.ast_tree_dump)

        tr = asciitree.LeftAligned(
            draw=asciitree.BoxStyle(gfx=asciitree.drawing.BOX_LIGHT, horiz_len=1))
        print(tr(tree))
        print("")

    def ast_tree_dump(self, treenode, tree=None):
        tree = self.tree if tree is None else tree
        line = treenode.dbg()

        include_line = False
        if line and self.regex:
            match = re.search(self.regex, line)
            if match:
                include_line = True
        else:
            include_line = True

        if include_line:
            subtree = {}
            tree[line] = subtree
        else:
            subtree = tree

        # Recursively iterate all children
        children = treenode.children
        for child in children:
            self.ast_tree_dump(child, tree=subtree)


################################################################################


def add_args(parser):
    desc = \
        "Dump nodes from clang AST tree based on compilation database "\
        " (compile_commands.json)."
    epil = "Example: ./%s --compdb ~/linux-stable/compile_commands.json" % \
        os.path.basename(__file__)
    parser.description = desc
    parser.epilog = epil

    help = "Set the output file name, default is 'calls.csv'"
    parser.add_argument('--out', nargs='?', help=help, default='calls.csv')

    help = "Include only AST nodes where the resulting line matches "\
        "REGEX regular expression"
    parser.add_argument('--regex', help=help, default=None)

    return parser


################################################################################


if __name__ == "__main__":
    parser = utils.clang_common_args(_FILEDIR)
    add_args(parser)
    args = parser.parse_args()
    utils.handle_common_args(parser, args)

    if args.regex:
        args.regex = re.compile(args.regex)

    astparser.set_clang_bindings_and_lib(args.cindexpy, args.libclang)
    import clang.cindex as cl

    viewer = ClangAstTreeviewer()
    viewer.dump_ast(
        compdb=args.compdb,
        append_arg=args.append_arg,
        srcfile=args.file,
        regex=args.regex,
    )

################################################################################
