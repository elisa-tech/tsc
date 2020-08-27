#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0
import argparse
import csv
import os
import sys
import logging
import graphviz as gv
import pandas as pd
import utils
from collections import OrderedDict

_LOGGER = logging.getLogger(utils.LOGGER_NAME)

################################################################################


class Grapher():

    def __init__(self, csvfile, depth):
        self.df = df_from_csv_file(csvfile)
        self.digraph = None
        self.maxdepth = 1
        # Key: node name, Value: list of labels associated to node name
        self.nodelabels = {}

    def graph_caller_function(
            self,
            caller_function_regex,
            filename="graph.dot",
            depth=2,
            inverse=False,
            format='png'):

        self.digraph = gv.Digraph(filename=filename)
        self.digraph.attr('graph', rankdir='LR')
        self.digraph.attr('graph', concentrate='true')
        self.digraph.attr('node', shape='box')
        self.digraph.attr('node', style='rounded')
        self.digraph.attr('node', margin='0.3,0.1')
        self.maxdepth = depth
        if inverse:
            self._graph(col='callee_function',
                        regex=caller_function_regex, inverse=inverse)
        else:
            self._graph(col='caller_function', regex=caller_function_regex)
        self._render(filename, format=format)

    def _graph(self, col, regex, curr_depth=0, inverse=False):
        curr_depth += 1
        if curr_depth > self.maxdepth:
            return
        df = self._regex_filter(col, regex)
        for row in df.itertuples():
            # Caller node
            self._add_node(row.caller_function, row.caller_filename)
            # Callee node
            self._add_node(row.callee_function, row.callee_filename)
            # Edge
            self.digraph.edge(row.caller_function, row.callee_function)
            if inverse:
                self._graph(col, r'^%s$' % row.caller_function, curr_depth)
            else:
                self._graph(col, r'^%s$' % row.callee_function, curr_depth)

    def _render(self, filename, format):
        self.digraph.render(format=format)
        _LOGGER.info("wrote: %s" % filename)
        _LOGGER.info("wrote: %s.%s" % (filename, format))

    def _regex_filter(self, col, regex):
        return self.df[self.df[col].str.contains(regex, regex=True, na=False)]

    def _add_node(self, function, filename):
        function = str(function)
        filename = str(filename)
        # Node name = function, Default label = []
        labels = self.nodelabels.setdefault(function, [])
        # Add filename as new label
        labels.append(filename)
        # Remove possible duplicate labels, preserving order
        labels = list(OrderedDict.fromkeys(labels))
        # Build the html label: function name on the first line followed by
        # associated filenames framed with html font-tags
        beg = "<FONT POINT-SIZE=\"10\">"
        end = "</FONT>"
        label = "<%s<BR/>%s%s%s>" % (function, beg, "<BR/>".join(labels), end)
        # Add node to the graph
        self.digraph.node(function, label)


################################################################################


def df_from_csv_file(name):
    df = pd.read_csv(name, na_values=[''], keep_default_na=False)
    df.reset_index(drop=True, inplace=True)
    return df


def getargs():
    desc = "Visualize call graphs based on function call csv database (CSV)"

    epil = "Example: ./%s --csv calls.csv --caller_function_regex "\
        "'^__x64_sys_open$' --format png --depth 4" % \
        os.path.basename(__file__)
    parser = argparse.ArgumentParser(description=desc, epilog=epil)

    required_named = parser.add_argument_group('required named arguments')
    help = "function call database csv file"
    required_named.add_argument('--csv', help=help, required=True)
    help = "filter by caller_function (regular expression)"
    required_named.add_argument(
        '--caller_function_regex', help=help, required=True)

    help = "set the graph depth, defaults to 2"
    parser.add_argument('--depth', nargs='?', help=help, type=int, default=2)
    help = "draw inverse graph"
    parser.add_argument('--inverse', help=help, action='store_true')
    help = "set the graph output format, defaults to png"
    parser.add_argument('--format', nargs='?', help=help, default='png')

    return parser.parse_args()


################################################################################


if __name__ == "__main__":
    args = getargs()

    utils.exit_unless_accessible(args.csv)
    utils.setup_logging(verbosity=2)

    _LOGGER.info("reading input csv")
    g = Grapher(args.csv, args.depth)
    g.graph_caller_function(
        caller_function_regex=args.caller_function_regex,
        depth=args.depth,
        inverse=args.inverse,
        format=args.format)

################################################################################
