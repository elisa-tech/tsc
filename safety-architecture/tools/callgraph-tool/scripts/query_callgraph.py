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
from typing import NamedTuple

################################################################################

_LOGGER = logging.getLogger(utils.LOGGER_NAME)

################################################################################


class CallGraphFilter():
    def __init__(
            self,
            caller_function=None, caller_filename=None,
            callee_function=None, callee_filename=None):
        self.caller_function = caller_function
        self.caller_filename = caller_filename
        self.callee_function = callee_function
        self.callee_filename = callee_filename

    def get_query_str(self):
        return ' & '.join(
            ["{}=='{}'".format(key, value)
             for key, value in self.__dict__.items() if value is not None])

    def __eq__(self, other):
        if isinstance(other, CallGraphFilter):
            return (
                self.caller_function == other.caller_function and
                self.caller_filename == other.caller_filename and
                self.callee_function == other.callee_function and
                self.callee_filename == other.callee_filename)
        return False


################################################################################


DBG_INDENT = "    "


class Grapher():

    def __init__(self, csvfile):
        self.df = df_from_csv_file(csvfile)
        self.digraph = None
        # Key: node name, Value: list of labels associated to node name
        self.nodelabels = {}
        # Rows that match the query when output format is csv
        self.df_out_csv = None
        # Keep track of paths drawn to not re-draw them
        self.paths_drawn = set()
        # Default parameters
        self.maxdepth = 1
        self.edge_labels = False
        self.skip_indirect = False
        self.merge_edges = False
        self.inverse = False

    def graph(self, args):
        self._is_csv_out(args.out)
        self.maxdepth = args.depth
        self.inverse = args.inverse
        self.edge_labels = args.edge_labels
        self.skip_indirect = args.skip_indirect
        self.merge_edges = args.merge_edges

        if args.edge_labels and args.merge_edges:
            _LOGGER.warn(
                "Requested both 'edge_labels' and 'merge_edges': "
                "discarding 'edge_labels'"
            )
            self.edge_labels = False

        concentrate = 'true' if self.merge_edges else 'false'
        self.digraph = gv.Digraph(filename=args.out)
        self.digraph.attr('graph', rankdir='LR')
        self.digraph.attr('node', shape='box')
        self.digraph.attr('node', style='rounded')
        self.digraph.attr('node', margin='0.3,0.1')
        self.digraph.attr('graph', concentrate=concentrate)

        if self.inverse:
            # Filter by callee_function if 'inverse' requested
            filter = CallGraphFilter(callee_function=args.function)
        else:
            # Otherwise filter by caller_function
            filter = CallGraphFilter(caller_function=args.function)

        # Initial number of entries in the graph
        initlen = len(self.digraph.body)

        # Draw the graph
        self._graph(filter=filter)

        # Render the graph
        if len(self.digraph.body) > initlen:
            self._render(args.out)

        # Output csv
        if self.df_out_csv is not None and not self.df_out_csv.empty:
            df_to_csv_file(self.df_out_csv, args.out)

    def _is_csv_out(self, filename):
        _fname, extension = os.path.splitext(filename)
        fileformat = extension[1:]
        if fileformat == 'csv':
            self.df_out_csv = pd.DataFrame()
        else:
            self.df_out_csv = None

    def _graph(self, filter, curr_depth=0, curr_row=None):
        curr_depth += 1
        if curr_depth > self.maxdepth:
            return

        df = self._query(filter, curr_depth)
        if df.empty and curr_depth == 1:
            # First match failed: print to console and stop
            _LOGGER.info("No matching functions found")
            return
        if df.empty:
            # Reached leaf: no more matches
            _LOGGER.debug("%sFound nothing" % (DBG_INDENT*(curr_depth-1)))
            return

        if self.df_out_csv is not None:
            df.insert(0, "call_depth", curr_depth)
            self.df_out_csv = self.df_out_csv.append(df)

        for row in df.itertuples():
            self._dbg_print_row(row, curr_depth)
            if self.skip_indirect and row.callee_calltype == "indirect":
                _LOGGER.debug(
                    "%sSkipping indirect" % (DBG_INDENT*(curr_depth-1)))
                continue
            if self._path_drawn(row):
                _LOGGER.debug(
                    "%sSkipping duplicate path" % (DBG_INDENT*(curr_depth-1)))
                continue

            # Add caller node
            self._add_node(
                row.caller_function,
                row.caller_filename,
                row.caller_def_line)
            # Add callee node
            self._add_node(
                row.callee_function,
                row.callee_filename,
                row.callee_line)
            # Add edge between the nodes
            self._add_edge(row)

            # Construct the filter for next query in the call chain
            if self.inverse:
                filter = CallGraphFilter(
                    callee_function=row.caller_function,
                    callee_filename=row.caller_filename)
            else:
                filter = CallGraphFilter(
                    caller_function=row.callee_function,
                    caller_filename=row.callee_filename)

            # Recursively find the next entries
            self._graph(filter, curr_depth, row)

    def _path_drawn(self, row):
        if row is None:
            return False
        hash_str = "%s:%s:%s:%s:%s:%s" % (
            row.caller_filename,
            row.caller_function,
            row.caller_line,
            row.callee_filename,
            row.callee_function,
            row.callee_line)
        h = hash(hash_str)
        if h in self.paths_drawn:
            return True
        else:
            self.paths_drawn.add(h)
            return False

    def _query(self, filter, depth):
        query_str = filter.get_query_str()
        _LOGGER.debug("%sFiltering by: %s" % (DBG_INDENT*(depth-1), query_str))
        return self.df.query(query_str)

    def _render(self, filename):
        if self.df_out_csv is not None:
            return
        fname, extension = os.path.splitext(filename)
        format = extension[1:]
        self.digraph.render(filename=fname, format=format, cleanup=True)
        _LOGGER.info("wrote: %s" % filename)

    def _add_edge(self, row):
        if self.df_out_csv is not None:
            return
        edge_style = None
        if row.callee_calltype == "indirect":
            edge_style = "dashed"
        if self.edge_labels:
            beg = "<FONT POINT-SIZE=\"8\">"
            end = "</FONT>"
            label = "<%s%s%s>" % (beg, row.caller_line, end)
            self.digraph.edge(
                "%s_%s" % (row.caller_filename, row.caller_function),
                "%s_%s" % (row.callee_filename, row.callee_function),
                label=label,
                style=edge_style)
        else:
            self.digraph.edge(
                "%s_%s" % (row.caller_filename, row.caller_function),
                "%s_%s" % (row.callee_filename, row.callee_function),
                style=edge_style)

    def _add_node(self, function, filename, line):
        if self.df_out_csv is not None:
            return
        function = str(function)
        filename = str(filename)
        line = str(line).split('.')[0]
        node_name = "%s_%s" % (filename, function)
        # Node name = function, Default label = []
        labels = self.nodelabels.setdefault(node_name, [])
        # Add filename as new label
        labels.append("%s:%s" % (filename, line))
        # Remove possible duplicate labels, preserving order
        labels = list(OrderedDict.fromkeys(labels))
        # Build the html label: function name on the first line followed by
        # associated filenames framed with html font-tags
        beg = "<FONT POINT-SIZE=\"10\">"
        end = "</FONT>"
        label = "<%s<BR/>%s%s%s>" % (function, beg, "<BR/>".join(labels), end)
        # Add node to the graph
        self.digraph.node(
            node_name, label, style='rounded,filled', fillcolor='#EEEEEE')

    def _dbg_print_row(self, row, depth):
        _LOGGER.debug(
            "%sFound: %s:%s():%s ==> %s:%s():%s [%s]" % (
                DBG_INDENT*(depth-1),
                row.caller_filename, row.caller_function, row.caller_line,
                row.callee_filename, row.callee_function, row.callee_line,
                row.callee_calltype))

################################################################################


def df_from_csv_file(name):
    df = pd.read_csv(name, na_values=[''], keep_default_na=False)
    df.reset_index(drop=True, inplace=True)
    return df


def df_to_csv_file(df, name):
    df.to_csv(
        path_or_buf=name,
        quoting=csv.QUOTE_ALL,
        sep=",", index=False, encoding='utf-8')
    _LOGGER.info("wrote: %s" % name)


def check_positive(val):
    intval = int(val)
    if intval <= 0:
        raise argparse.ArgumentTypeError(
            "%s is not positive integer" % val)
    return intval


def getargs():
    desc = "Query and visualize call graphs given the callgraph csv "\
        "database (CSV)."

    epil = "Example: ./%s --csv callgraph.csv --function "\
        "'main' --depth 4" % \
        os.path.basename(__file__)
    parser = argparse.ArgumentParser(description=desc, epilog=epil)

    required_named = parser.add_argument_group('required named arguments')

    help = "function call database csv file"
    required_named.add_argument('--csv', help=help, required=True)

    help = "filter by function name (exact match)"
    required_named.add_argument(
        '--function', help=help, required=True)

    help = "set the graph depth, defaults to 2"
    parser.add_argument(
        '--depth', help=help, type=check_positive, default=2)

    help = "draw inverse graph"
    parser.add_argument('--inverse', help=help, action='store_true')

    help = "Set the output file name, default is 'graph.png'. "\
        "The output filename extension determines the output format. "\
        "Common supported formats include: png, jpg, pdf, and dot. "\
        "For a full list of supported output formats, see: "\
        "https://graphviz.org/doc/info/output.html. In addition to graphviz "\
        "supported output formats, the tool supports output in csv to "\
        "allow post-processing the output data. Specify output file with "\
        ".csv extension to output the query result in textual csv format."
    parser.add_argument(
        '--out', nargs='?', help=help, default='graph.png')

    help = "Add edge labels to graph. This option adds caller "\
        "source line numbers as edge labels to graph."
    parser.add_argument('--edge_labels', help=help, action='store_true')

    help = "Do not include indirect calls to the output."
    parser.add_argument('--skip_indirect', help=help, action='store_true')

    help = "Merge edges: if two nodes are connected with multiple edges, "\
        "merge the multiedges into single edge."
    parser.add_argument('--merge_edges', help=help, action='store_true')

    help = "Set the verbose level (defaults to --v=1)"
    parser.add_argument('--verbose', help=help, type=int, default=1)

    return parser.parse_args()


################################################################################


if __name__ == "__main__":
    args = getargs()

    utils.exit_unless_accessible(args.csv)
    utils.setup_logging(verbosity=args.verbose)

    _LOGGER.info("reading input csv")
    g = Grapher(args.csv)
    g.graph(args)

################################################################################
