#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
import sys
import re
import asciitree
import colorama
import logging

from clang_download import update_clang
import astparser
import utils


_LOGGER = logging.getLogger(utils.LOGGER_NAME)
_FILEDIR = os.path.dirname(os.path.realpath(__file__))


################################################################################


class ClangAstTreeviewer():

    def dump_ast(self,
                 compdb,
                 append_arg=None,
                 srcfile=None,
                 noloc=False,
                 regex=None,
                 colorize='auto'):

        self.noloc = noloc
        self.regex = re.compile(regex) if regex else None
        self.color = colorize
        tree = {'': {}}
        self.tree = tree['']

        # Let AstParser parse the AST tree, calling
        # self.ast_tree_dump() for all the translation unit root nodes
        self.astparser = astparser.AstParser(compdb, append_arg, srcfile)
        self.astparser.walk_tree(callback=self.ast_tree_dump)

        tr = asciitree.LeftAligned(
            draw=asciitree.BoxStyle(gfx=asciitree.drawing.BOX_LIGHT, horiz_len=1))
        print(tr(tree))
        print("")

    def colorize(self, string, color):
        if self.color == 'always':
            return color + string + colorama.Style.RESET_ALL
        elif self.color == 'auto' and sys.stdout.isatty():
            return color + string + colorama.Style.RESET_ALL
        else:
            return string

    def ast_tree_dump(self, node, tree=None):
        tree = self.tree if tree is None else tree
        filename = str(node.location.file)
        line = self.colorize("%s" % (node.kind), colorama.Fore.LIGHTBLUE_EX)

        if node.spelling or node.displayname:
            line += " '%s'" % (node.spelling if node.spelling else node.displayname)
        usr = node.get_usr()
        if usr:
            line += self.colorize(" [usr = %s]" % (usr), colorama.Fore.GREEN)
        if not self.noloc:
            line += " <%s:%s:%s>" % (
                filename,
                node.location.line,
                node.location.column)
        if node.referenced:
            ref_usr = node.referenced.get_usr()
            line += self.colorize(
                " [ref = %s]" % (ref_usr), colorama.Fore.YELLOW)

        sem_parent = node.semantic_parent
        if sem_parent:
            usr = sem_parent.get_usr()
            line += self.colorize(" [sem = %s]" % (usr), colorama.Fore.LIGHTMAGENTA_EX)

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
        children = list(node.get_children())
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

    help = "Don't dump location information for AST nodes. "\
        "Note: since REGEX filters are applied to the lines as they "\
        "appear in the output, disabling location information from the "\
        "output dump will also disable all the matches based on the location "\
        "information"
    parser.add_argument(
        '--noloc', help=help, default=False, action="store_true")

    help = "Colorize output (defaults to 'auto')"
    parser.add_argument(
        '--color',
        help=help, choices=["auto", "always", "never"], default='auto')

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
        noloc=args.noloc,
        regex=args.regex,
        colorize=args.color,
    )

################################################################################
