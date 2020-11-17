#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0


import argparse
import csv
import json
import logging
import networkx as nx
import os
import pandas as pd
import re
import sys
import utils

################################################################################

_LOGGER = logging.getLogger(utils.LOGGER_NAME)

################################################################################


class Node():
    def __init__(self, function=None, filename=None, row_id=None):
        if not isinstance(filename, str):
            print("Something odd happened")
        self.function = function
        self.filename = filename
        self.row_id = row_id

    def __eq__(self, other):
        if isinstance(other, Node):
            return (
                self.function == other.function and
                self.filename == other.filename)
        return False

    def __str__(self):
        return ":".join([self.filename, self.function])

    def __hash__(self):
        return hash(self.__str__())


class Edge():
    def __init__(
        self,
        in_node,
        out_node
    ):
        self.in_node = in_node
        self.out_node = out_node


################################################################################


def df_from_csv_file(name):
    dtype = {"caller_def_line": str, "caller_line": str}
    df = pd.read_csv(name, keep_default_na=False, dtype=dtype)
    df.reset_index(drop=True, inplace=True)
    return df


def df_to_csv_file(df, name):
    df.to_csv(
        path_or_buf=name,
        quoting=csv.QUOTE_ALL,
        sep=",", index=False, encoding='utf-8')
    _LOGGER.info("wrote: %s" % name)


def def_regex_filter(df, column, regex):
    return df[df[column].str.contains(regex, regex=True, na=False)]


def get_df_from(df, from_fun, function_col, filename_col, drop_duplicates=True):
    from_fun = from_fun.split(":")
    if len(from_fun) == 1:
        from_fun = ["", from_fun[0]]
        df_from = df[df[function_col] == from_fun[1]]
    else:
        df_from = df[(df[function_col] == from_fun[1]) & (df[filename_col] == from_fun[0])]
    # If from function not in database return immediately (with info message)
    if df_from.shape[0] <= 0:
        _LOGGER.warn(
            "Function '%s' does not exist in call graph database for selected search"
            " direction" % ":".join(from_fun)
        )
        sys.exit(1)
    # If multiple from functions with the same name, notify the user to specify a filename too
    if drop_duplicates:
        df_from = df_from[[function_col, filename_col]].drop_duplicates()
        if df_from.shape[0] > 1:
            _LOGGER.warn(
                "Multiple functions with the name '%s' exist in call graph database. Please,"
                " specify the correct function using filepath:filename format" % from_fun[1]
            )
            sys.exit(1)
    return df_from


def graph_from_df(df):
    g = nx.DiGraph()
    for row in df.itertuples():
        n1 = Node(
                function=row.caller_function,
                filename=row.caller_filename)
        n2 = Node(
                function=row.callee_function,
                filename=row.callee_filename)
        g.add_edge(n1, n2)

    return g


def find_lca(df, f1, f2):
    df_f1 = get_df_from(df, f1, 'caller_function', 'caller_filename')
    df_f2 = get_df_from(df, f2, 'caller_function', 'caller_filename')
    G = graph_from_df(df)
    G.remove_edges_from(list(nx.selfloop_edges(G)))
    f1_node = Node(
        function=df_f1['caller_function'].iloc[0],
        filename=df_f1['caller_filename'].iloc[0]
    )
    f2_node = Node(
        function=df_f1['caller_function'].iloc[0],
        filename=df_f1['caller_filename'].iloc[0]
    )
    f1_pred = list(G.predecessors(f1_node))
    f2_pred = list(G.predecessors(f2_node))
    common_pred = set(f1_pred).intersection(set(f2_pred))
    lca = []
    for node in common_pred:
        if node.function.startswith('__sys'):
            lca.append(node)
    return lca


def output_to_json(d, filename):
    with open(filename, 'w') as handle:
        json.dump(d, handle, indent=4)


################################################################################


def getargs():
    desc = "Find function call chains reachable from the input function."\
        " The end of call chain is defined with second argument which is a"\
        " regular expression matching one or more function names. The output"\
        " is either the database of detected call chains in csv format or image"\
        " of the detected subgraph"

    epil = "Example: ./%s --from_function sock_recvmsg --to_function '^x64_sys'"\
        "--calls calls.csv" % os.path.basename(__file__)
    parser = argparse.ArgumentParser(description=desc, epilog=epil)

    required_named = parser.add_argument_group('required named arguments')
    help = "function call database csv file"
    required_named.add_argument("--calls", help=help, required=True, nargs='+')
    help = "first input argument"
    required_named.add_argument("--function1", help=help, required=True)
    help = "second input argument"
    required_named.add_argument("--function2", help=help, required=True)

    help = "name of the output file"
    parser.add_argument("--out", help=help, default="related.json")
    choices = ["ancestor", "offspring"]
    help = "selects search direction."
    parser.add_argument("--algorithm", help=help, choices=choices, default="ancestor")
    help = "select cutoff length for path search"
    parser.add_argument("--cutoff", help=help, type=int, default=10)
    help = "set the verbosity level (e.g. -vv for debug level)"
    parser.add_argument(
        "-v", "--verbose", help=help, action="count", default=1)
    return parser.parse_args()


if __name__ == "__main__":
    args = getargs()

    for call in args.calls:
        utils.exit_unless_accessible(call)
    utils.setup_logging(verbosity=args.verbose)

    # Load graph database (remove duplicates)

    if args.algorithm == 'ancestor':
        df_all = df_from_csv_file(args.calls[0])
        df = df_all.drop_duplicates()
        f1, f2 = args.arg1, args.arg2
        lca = find_lca(df, f1, f2)

        lca_l = []
        for node in lca:
            df_row = df_all[(df_all['caller_function'] == node.function) &
                            (df_all['caller_filename'] == node.filename)]
            lca_entry = {
                    'function': df_row['caller_function'].iloc[0],
                    'filename': df_row['caller_filename'].iloc[0],
                    'def_line': df_row['caller_def_line'].iloc[0]
            }
            lca_l.append(lca_entry)

        output_to_json(lca_l, args.out)

    if args.algorithm == 'offspring':
        df1 = df_from_csv_file(args.calls[0])
        df2 = df_from_csv_file(args.calls[1])
        dropcols = ['call_depth', 'callee_inlined_from_file',
                    'callee_inlined_from_line', 'indirect_found_with']
        df1 = df1.drop(columns=dropcols)
        df2 = df2.drop(columns=dropcols)
        df = pd.merge(
            left=df1,
            right=df2,
            how="outer",
            on=["caller_filename", "caller_function", "callee_filename", "callee_function",
                "caller_def_line", "caller_line", "callee_calltype", "callee_line"],
            indicator=True)

        # insert dummy rows with caller "___" and callee being arg1 and arg2
        node1 = get_df_from(
            df1, args.function1, 'caller_function', 'caller_filename', drop_duplicates=False)
        node2 = get_df_from(
            df2, args.function2, 'caller_function', 'caller_filename', drop_duplicates=False)
        n1_function = node1['caller_function'].iloc[0]
        n1_filename = node1['caller_filename'].iloc[0]
        n1_def_line = node1['caller_def_line'].iloc[0]
        n2_function = node2['caller_function'].iloc[0]
        n2_filename = node2['caller_filename'].iloc[0]
        n2_def_line = node2['caller_def_line'].iloc[0]

        data = [
            ['___', "___", "", "0", n1_filename, n1_function, n1_def_line, ""],
            ['___', "___", "", "0", n2_filename, n2_function, n2_def_line, ""]]
        df = def_regex_filter(df, '_merge', 'both')
        df = df.drop(columns=['_merge'])
        df = df.append(pd.DataFrame(data, columns=df.columns), ignore_index=True)
        df = pd.concat([df, node1, node2])
        df_to_csv_file(df, args.out)

    _LOGGER.info("Done")
