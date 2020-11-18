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
import re
import utils
import html
from collections import OrderedDict
from difflib import SequenceMatcher

################################################################################

_LOGGER = logging.getLogger(utils.LOGGER_NAME)

################################################################################


class CallGraphFilter():
    def __init__(
            self,
            caller_function=None, caller_filename=None, caller_def_line=None,
            callee_function=None, callee_filename=None, callee_line=None):
        self.caller_function = caller_function
        self.caller_filename = caller_filename
        self.caller_def_line = caller_def_line
        self.callee_function = callee_function
        self.callee_filename = callee_filename
        self.callee_line = callee_line

    def get_query_str(self):
        return ' & '.join(
            ["{}=='{}'".format(key, value)
             for key, value in self.__dict__.items() if value is not None])

    def __eq__(self, other):
        if isinstance(other, CallGraphFilter):
            return (
                self.caller_function == other.caller_function and
                self.caller_filename == other.caller_filename and
                (self.caller_def_line == other.caller_def_line or
                 (not self.caller_def_line or not other.caller_def_line)) and
                self.callee_function == other.callee_function and
                self.callee_filename == other.callee_filename and
                (self.callee_line == other.callee_line or
                 (not self.callee_line or not other.callee_line))
            )
        return False


################################################################################


DBG_INDENT = "    "


class Grapher():

    def __init__(self, csvfile):
        self._load_callgraph_data(csvfile)
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
        self.until_func_regex = None
        self.colorize_regex = None
        self.df_cov = None

    def graph(self, args):
        self._is_csv_out(args.out)
        self.maxdepth = args.depth
        self.inverse = args.inverse
        self.edge_labels = args.edge_labels
        self.skip_indirect = args.skip_indirect
        self.merge_edges = args.merge_edges
        self.until_func_regex = r'%s' % args.until_function
        self.colorize_regex = r'%s' % args.colorize

        if args.edge_labels and args.merge_edges:
            _LOGGER.warn(
                "Requested both 'edge_labels' and 'merge_edges': "
                "discarding 'edge_labels'"
            )
            self.edge_labels = False

        if args.coverage_file is not None:
            self._load_coverage_data(args.coverage_file)

        concentrate = 'true' if self.merge_edges else 'false'
        self.digraph = gv.Digraph(filename=args.out)
        self.digraph.attr('graph', rankdir='LR')
        self.digraph.attr('node', shape='box')
        self.digraph.attr('node', style='rounded')
        self.digraph.attr('node', margin='0.3,0.1')
        self.digraph.attr('graph', concentrate=concentrate)

        if self.inverse:
            # Filter by callee_function if 'inverse' requested
            filter = CallGraphFilter(
                callee_function=args.function,
                callee_filename=args.filename)
        else:
            # Otherwise filter by caller_function
            filter = CallGraphFilter(
                caller_function=args.function,
                caller_filename=args.filename)

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

    def _load_callgraph_data(self, filename):
        utils.exit_unless_accessible(filename)
        self.df = pd.read_csv(filename, na_values=[''], keep_default_na=False)
        self.df.reset_index(drop=True, inplace=True)
        self.df.columns = self.df.columns.str.lower()
        require_cols = [
            'caller_function',
            'caller_filename',
            'caller_def_line',
            'caller_line',
            'callee_function',
            'callee_filename',
            'callee_line',
        ]
        if not all(x in list(self.df.columns.values) for x in require_cols):
            _LOGGER.error(
                "Callgraph database '%s' missing required headers: %s" % (
                    filename, require_cols))
            exit(1)

    def _load_coverage_data(self, filename):
        utils.exit_unless_accessible(filename)
        self.df_cov = pd.read_csv(filename, sep=None, engine='python')
        self.df_cov.reset_index(drop=True, inplace=True)
        self.df_cov.columns = self.df_cov.columns.str.lower()
        require_cols = ['function', 'filename']
        if not all(x in list(self.df_cov.columns.values) for x in require_cols):
            _LOGGER.error(
                "Coverage file '%s' missing required headers: %s" % (
                    filename, require_cols))
            exit(1)
        if self.df_cov.isnull().values.any():
            _LOGGER.error(
                "Empty values in coverage data: %s" % filename)
            exit(1)

        # Normalize paths in the callgraph database.
        # This operation takes some time, so we don't do it in the suspected
        # usual case - when coverage data is not provided. However, when
        # coverage data _is_ provided, we need to normalize the filename
        # paths also in the callgraph database so that they become comparable
        # to filename paths in the coverage data.

        self.df['caller_filename'] = self.df[
            'caller_filename'].map(
                lambda a: a if pd.isnull(a) else os.path.normpath(a))
        self.df['callee_filename'] = self.df[
            'callee_filename'].map(
                lambda a: a if pd.isnull(a) else os.path.normpath(a))

        # Normalize paths in the coverage data
        self.df_cov['filename'] = self.df_cov[
            'filename'].map(
                lambda a: a if pd.isnull(a) else os.path.normpath(a))

        # Adjust filenames in coverage data to make them relative to
        # the kernel tree directory. This needs to be done so that the
        # filename paths in coverage data become comparable to the
        # filename paths in the callgraph database:

        example_cov_file = self.df_cov['filename'].iloc[0]

        # Warn if it looks like filepaths don't match between the
        # coverage data and the callgraph data.
        # Possible reasons include:
        # - Absolute vs relative filepaths
        # - Coverage data is from different build compared to callgraph data
        df = self.df[(self.df['caller_filename'] == example_cov_file)]
        if df.empty:
            _LOGGER.warn(
                "Filename '%s' from the coverage data is not in the "
                "callgraph database. File paths in coverage data will "
                "likely not match the file paths in callgraph database."
                % example_cov_file)

    def _is_csv_out(self, filename):
        _fname, extension = os.path.splitext(filename)
        fileformat = extension[1:]
        if fileformat == 'csv':
            self.df_out_csv = pd.DataFrame()
        else:
            self.df_out_csv = None

    def _graph(self, filter, curr_depth=0):
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
            if pd.isna(row.caller_function) or pd.isna(row.callee_function):
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

            if regex_match(self.until_func_regex, row.caller_function):
                _LOGGER.debug(
                    "%sReached until_function" % (DBG_INDENT*(curr_depth-1)))
                continue

            # Construct the filter for next query in the call chain
            if self.inverse:
                filter = CallGraphFilter(
                    callee_function=row.caller_function,
                    callee_filename=row.caller_filename,
                    callee_line=str(row.caller_def_line).split('.')[0]
                )
            else:
                filter = CallGraphFilter(
                    caller_function=row.callee_function,
                    caller_filename=row.callee_filename,
                    caller_def_line=str(row.callee_line).split('.')[0]
                )

            # Recursively find the next entries
            self._graph(filter, curr_depth)

    def _path_drawn(self, row):
        if row is None:
            return False
        if (row.caller_filename == row.callee_filename) and \
                (row.caller_function == row.callee_function) and \
                (row.caller_def_line == row.callee_line) and \
                (row.callee_calltype == "indirect"):
            # Skip drawing recursive indirect calls
            return True
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
            label = "<%s%s%s>" % (beg, str(row.caller_line).split('.')[0], end)
            self.digraph.edge(
                node_id(row.caller_filename, row.caller_function,
                        row.caller_def_line),
                node_id(row.callee_filename,
                        row.callee_function, row.callee_line),
                label=label,
                style=edge_style)
        else:
            self.digraph.edge(
                node_id(row.caller_filename, row.caller_function,
                        row.caller_def_line),
                node_id(row.callee_filename,
                        row.callee_function, row.callee_line),
                style=edge_style)

    def _add_node(self, function, filename, line):
        if self.df_out_csv is not None:
            return
        filename = str(filename)
        line = str(line).split('.')[0]
        node_name = node_id(filename, function, line)
        function = html.escape(str(function))
        # Node name = function, Default label = []
        labels = self.nodelabels.setdefault(node_name, [])
        # Add filename as new label
        labels.append("%s:%s" % (filename, line))
        # Add coverage pct as label
        fillcolor, pct = self._get_coverage_data(filename, function)
        if pct:
            labels.append(pct)
        # Remove possible duplicate labels, preserving order
        labels = list(OrderedDict.fromkeys(labels))
        # Build the html label: function name on the first line followed by
        # associated filenames framed with html font-tags
        beg = "<FONT POINT-SIZE=\"10\">"
        end = "</FONT>"
        label = "<%s<BR/>%s%s%s>" % (function, beg, "<BR/>".join(labels), end)
        if regex_match(self.colorize_regex, function):
            fillcolor = "#FFE6E6"
        elif not fillcolor:
            fillcolor = '#EEEEEE'
        # Add node to the graph
        self.digraph.node(
            node_name, label, style='rounded,filled', fillcolor=fillcolor)

    def _get_coverage_data(self, filename, function):
        pct = None
        fillcolor = None
        if self.df_cov is None:
            return fillcolor, pct
        df = self.df_cov[
            (self.df_cov['function'] == function) &
            (self.df_cov['filename'] == filename)]
        if df.empty:
            pct = "\ncoverage: (no coverage info)"
        elif ('percent' not in list(df.columns.values)):
            pct = ""
        elif df.shape[0] == 1:
            val = pd.to_numeric(df['percent'], errors='coerce').values[0]
            if not pd.isna(val):
                pct = "\ncoverage: %s%%" % (int(round(val)))
                fillcolor = gradient(val)
            else:
                pct = "\ncoverage: NAN"
        elif df.shape[0] > 1:
            pct = "\ncoverage: (unknown)"
            _LOGGER.error("%s:%s matches multiple rows" % (filename, function))

        return fillcolor, pct

    def _dbg_print_row(self, row, depth):
        _LOGGER.debug(
            "%sFound: %s:%s():%s ==> %s:%s():%s [%s]" % (
                DBG_INDENT*(depth-1),
                row.caller_filename, row.caller_function, row.caller_line,
                row.callee_filename, row.callee_function, row.callee_line,
                row.callee_calltype))


################################################################################


GRADIENT_LIST = []


def gradient_list_generate():
    r1, g1, b1 = (255, 140, 140)
    r2, g2, b2 = (90, 215, 140)
    steps = int(100 + 1)
    rd, gd, bd = (r2-r1)/steps, (g2-g1)/steps, (b2-b1)/steps
    for _step in range(steps):
        r1 += rd
        g1 += gd
        b1 += bd
        hex = "#%02x%02x%02x" % (int(r1), int(g1), int(b1))
        GRADIENT_LIST.append(hex)


def gradient(pct):
    if pct < 0 or pct > 100:
        _LOGGER.error("Invalid percentage value: %s" % pct)
        exit(1)
    return GRADIENT_LIST[int(pct)]


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


def regex_match(regex, s):
    if (not regex or not s):
        return False
    return re.match(regex, s) is not None


def node_id(filename, function, line):
    # Graphviz doesn't like colons in the node names: we simply
    # remove them here. node_id is only used to uniquely identify each
    # node in the graph: each node has a label associated to it and
    # the labels can still contain colons.
    return ("%s_%s_%s" % (
        filename,
        html.escape(str(function)),
        float(line)
    )).replace(":", "")


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

    help = "filter by filename (exact match)"
    parser.add_argument('--filename', help=help, default=None)

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

    help = "Keep drawing the call chains until function name matches "\
        "the specified regular expression. This option works together with "\
        "--depth so that drawing stops when the first of the two "\
        "conditions match: when the function name matches the given regex "\
        "or when the specified call chain depth is reached."
    parser.add_argument('--until_function', help=help)

    help = "Colorize functions that match the specified regular expression."
    parser.add_argument('--colorize', help=help)

    help = "Include function coverage data into the graph from the specified "\
        "file."
    parser.add_argument('--coverage_file', help=help)

    help = "Set the verbose level (defaults to --v=1)"
    parser.add_argument('--verbose', help=help, type=int, default=1)

    return parser.parse_args()


################################################################################


if __name__ == "__main__":
    args = getargs()

    utils.exit_unless_accessible(args.csv)
    utils.setup_logging(verbosity=args.verbose)
    gradient_list_generate()

    _LOGGER.info("reading input csv")
    g = Grapher(args.csv)
    g.graph(args)

################################################################################
