#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0


import argparse
import csv
import logging
import networkx as nx
import os
import pandas as pd
import re
import sys
import utils

from collections import namedtuple
from grapher import Grapher

################################################################################

_LOGGER = logging.getLogger(utils.LOGGER_NAME)

################################################################################


SearchSettings = namedtuple(
    'SearchSettings', [
        "from_col_func",
        "from_col_fn",
        "to_col_func",
        "to_col_fn",
        "reverse"
    ]
)


def search_settings(direction):
    left_search, right_search = None, None
    if direction == "both" or direction == "left":
        left_search = SearchSettings(
            from_col_func="callee_function",
            from_col_fn="callee_filename",
            to_col_func="caller_function",
            to_col_fn="caller_filename",
            reverse=True
        )
    if direction == "both" or direction == "right":
        right_search = SearchSettings(
            from_col_func="caller_function",
            from_col_fn="caller_filename",
            to_col_func="callee_function",
            to_col_fn="callee_filename",
            reverse=False
        )
    return left_search, right_search


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
    df = pd.read_csv(name, keep_default_na=False)
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


def get_bfs_tree_dir(g, from_node, direction):
    return nx.bfs_tree(g, source=from_node, reverse=direction.reverse)


def find_all_chains(df, from_node, to_nodes, direction):
    G = graph_from_df(df)
    g_dir = get_bfs_tree_dir(G, from_node, direction)
    rows = []
    for to_node in to_nodes:
        # check every dest node for possible paths from source
        if g_dir.has_node(to_node):
            # special check for recursive call
            if from_node == to_node:
                rows.append([
                    from_node.filename, from_node.function,
                    to_node.filename, to_node.function,
                ])
                continue

            paths = nx.all_simple_paths(g_dir, from_node, to_node)
            for path in paths:
                chain = list(path)
                if len(chain) > 2:
                    chain = zip(chain[:-1], chain[1:])
                else:
                    chain = [chain]
                for link in chain:
                    out_node, in_node = link[0], link[1]
                    rows.append([
                        out_node.filename, out_node.function,
                        in_node.filename, in_node.function,
                    ])

    cols = [
        direction.from_col_fn, direction.from_col_func,
        direction.to_col_fn, direction.to_col_func
    ]
    chains_df = pd.DataFrame(data=rows, columns=cols)
    return chains_df


def get_df_from(df, from_fun, function_col, filename_col):
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
    df_from = df_from[[function_col, filename_col]].drop_duplicates()
    if df_from.shape[0] > 1:
        _LOGGER.warn(
            "Multiple functions with the name '%s' exist in call graph database. Please,"
            " specify the correct function using filepath:filename format" % from_fun[1]
        )
        sys.exit(1)
    return df_from


def get_df_to(df, to_fun, function_col, filename_col):

    # If there are no functions matching regex exit with info message
    df_to = def_regex_filter(df, column=function_col, regex=to_fun)
    df_to = df_to[[function_col, filename_col]].drop_duplicates()

    if df_to.shape[0] <= 0:
        _LOGGER.warn(
            "Function regex '%s' does not match any entries in call graph database"
            " for selected search direction" % to_fun
        )
        sys.exit(1)

    return df_to


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


def find_chains_directed_df(df, from_fun, to_fun, dir):
    df_from = get_df_from(df, from_fun, dir.from_col_func, dir.from_col_fn)
    df_to = get_df_to(df, to_fun, dir.to_col_func, dir.to_col_fn)
    from_node = Node(
        function=df_from[dir.from_col_func].iloc[0],
        filename=df_from[dir.from_col_fn].iloc[0]
    )
    to_nodes = []
    for _, row in df_to.iterrows():
        to_nodes.append(
            Node(
                function=row[dir.to_col_func], filename=row[dir.to_col_fn]
            )
        )
    chains_df = find_all_chains(df, from_node, to_nodes, dir)
    return chains_df


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
    required_named.add_argument("--calls", help=help, required=True)
    help = "function name from where the search begins (literal match)"
    required_named.add_argument("--from_function", help=help, required=True)
    help = "function name where call chain ends (regex match)"
    required_named.add_argument("--to_function", help=help, required=True)

    help = "name of the output file containing detected chains"
    parser.add_argument("--out", help=help, default="chains.csv")
    choices = ["left", "right", "both"]
    help = "selects search direction."
    parser.add_argument("--direction", help=help, choices=choices, default="right")
    help = "set the verbosity level (e.g. -vv for debug level)"
    parser.add_argument(
        "-v", "--verbose", help=help, action="count", default=1)
    return parser.parse_args()


if __name__ == "__main__":
    args = getargs()

    utils.exit_unless_accessible(args.calls)
    utils.setup_logging(verbosity=args.verbose)

    # Load graph database (remove duplicates)
    df_all = df_from_csv_file(args.calls)
    df = df_all.drop_duplicates()

    from_fun, to_fun = args.from_function, args.to_function
    left, right = search_settings(args.direction)

    merge_on = ["caller_filename", "caller_function", "callee_filename", "callee_function"]
    chains_df_right = pd.DataFrame(columns=merge_on)
    if right:
        chains_df_right = find_chains_directed_df(df, from_fun, to_fun, right)

    chains_df_left = pd.DataFrame(columns=merge_on)
    if left:
        chains_df_left = find_chains_directed_df(df, from_fun, to_fun, left)

    df_chains = pd.concat([chains_df_left, chains_df_right]).drop_duplicates()
    df_chains = pd.merge(df_all, df_chains, on=merge_on, how='inner')
    if args.out.endswith(".csv"):
        df_to_csv_file(df_chains, args.out)
    else:
        grapher = Grapher(args.out)
        grapher.graph(df_chains)
        grapher.render(args.out)

    _LOGGER.info("Done")
