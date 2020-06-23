#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import json
import networkx as nx
import os
import pandas as pd
import matplotlib as mpl
import matplotlib.cm
import signal
import sys


def ctrl_c_handler(s, f):
    sys.exit(0)


signal.signal(signal.SIGINT, ctrl_c_handler)


class Node:
    def __init__(self, row):
        self.filename = row[0]
        self.line = row[1]
        self.function = row[2]
        self.calltype = row[3]

    def __str__(self):
        return self.function

    def __eq__(self, other):
        return self.function == other.function

    def __hash__(self):
        return hash(self.function)


def create_filter(func, filtlist):
    def f(val):
        return any([func(val, f) for f in filtlist])
    return f


def index_from_filter(col, filt_funcs, how='exclude'):
    index = []
    for cell in col:
        cond = any([ff(cell) for ff in filt_funcs])
        if how == 'exclude':
            index.append(not cond)
        elif how == 'include':
            index.append(cond)
        else:
            pass
            # TODO: throw arg not supported
    return index


def startswith(value, filtval):
    return value.startswith(filtval)


def endswith(value, filtval):
    return value.endswith(filtval)


def contains(value, filtval):
    return filtval in value


def create_calls_filters(config):
    filtdict = {}
    func_lut = {'contains': contains,
                'startswith': startswith,
                'endswith': endswith}

    for filtopt in ['caller', 'callee']:
        call_cfg = config[filtopt]
        for col, cfg in call_cfg.items():
            name = filtopt + "_" + col
            filtdict[name] = {}
            if 'include' in cfg.keys():
                filters = []
                for func, filtlist in cfg['include'].items():
                    f = func_lut[func]
                    filters.append(create_filter(f, filtlist))
                filtdict[name]['include'] = filters

            if 'exclude' in cfg.keys():
                filters = []
                for func, filtlist in cfg['exclude'].items():
                    f = func_lut[func]
                    filters.append(create_filter(f, filtlist))
                filtdict[name]['exclude'] = filters

    return filtdict


def get_json_config(configfile):
    config = {}
    with open(configfile, "r") as handle:
        config = json.load(handle)
    return config


def get_calls_table(callsfile):
    df = pd.read_csv(callsfile)
    df = df.dropna(subset=['caller_function', 'callee_function', 'callee_filename'], how='any')
    # remove relative paths e.g 'kernel/../mm' becomes 'mm'
    df['caller_filename'] = df['caller_filename'].apply(os.path.normpath)
    df['callee_filename'] = df['callee_filename'].apply(os.path.normpath)
    return df


def filter_calls(df, filters):
    for col, funcdict in filters.items():
        for how, filt_funcs in funcdict.items():
            if col not in df.columns:
                continue
            index = index_from_filter(df[col], filt_funcs=filt_funcs, how=how)
            df = df[index]

    return df


def digraph_from_calls(df):
    g = nx.DiGraph()

    for idx, row in df.iterrows():
        assert len(df.columns) == 8, "Expected 4 columns for caller and callee, respectively"
        caller = Node(row[0:4])
        callee = Node(row[4:8])
        g.add_edge(caller, callee)

    return g


def get_syscalls(g):
    def node_filter(node):
        return "_x64_sys_" in node.function
    nodes = nx.subgraph_view(g, filter_node=node_filter)
    nodes = [node for node in nodes]
    return nodes


def filter_cc_with_source_nodes(g, source_filter):
    rm = []
    for wcc in nx.weakly_connected_components(g):
        sources = source_filter(g.subgraph(wcc))
        if len(sources) == 0:
            rm.extend([node for node in wcc])
    g.remove_nodes_from(rm)

    return g


def create_colormap(array):
    norm = mpl.colors.Normalize(vmin=0, vmax=len(array)-1)
    mapper = mpl.cm.ScalarMappable(norm, cmap=mpl.cm.plasma)

    colormap = {}
    for idx, val in enumerate(sorted(array)):
        colormap[val] = mpl.colors.to_hex(mapper.to_rgba(idx))

    return colormap


def hierarchy(d, name):
    children = []
    for child in d[name]['children']:
        hierarchy(d, child)
        children.append(d[child])

    d[name]["children"] = children


def create_hierarchy(g, sources, colormap, depth_limit=None, name="tree"):
    tree = {
        "name": name,
        "color": "#000000",
        "children": []
    }
    for idx, node in enumerate(sources):
        succ = nx.bfs_successors(g, node, depth_limit=depth_limit)
        d = {}
        d[node.function] = {
                "name": node.function,
                "file": node.filename,
                "color": colormap[node.filename],
                "children": []
            }
        for n, children in succ:
            for c in children:
                d[n.function]["children"].append(c.function)
                d[c.function] = {
                    "name": c.function,
                    "file": c.filename,
                    "color": colormap[c.filename],
                    "children": []
                }
        hierarchy(d, node.function)
        tree["children"].append(d[node.function])

    return tree


def write_hierarchy(filename, tree):
    with open(filename, 'w') as handle:
        json.dump(tree, handle, indent=4)


def run_server(port):
    from http.server import HTTPServer, SimpleHTTPRequestHandler

    httpd = HTTPServer(('localhost', port), SimpleHTTPRequestHandler)
    httpd.serve_forever()


def getargs():
    desc = "Create JSON representation of the Linux subtree suitable for graphical representation"
    parser = argparse.ArgumentParser(description=desc)
    help_db = "Path to calls.csv file generated with clang-indexer"
    parser.add_argument('--db', default="calls.csv", help=help_db)
    help_config = "JSON file containing filtering options with specified configuration"
    parser.add_argument('--config', default="config.json", help=help_config)
    help_name = "Name of the hierarchy root, also used as the output file name"
    parser.add_argument('--name', default="tree", help=help_name)
    help_depth = "Maximum allowed hierarchy depth"
    parser.add_argument('--depth', default=5, help=help_depth, type=int)
    help_port = "Run local server with specified port"
    parser.add_argument('--port', default=8080, help=help_port, type=int)
    return parser.parse_args()


def main():
    args = getargs()
    callsfile = os.path.expanduser(args.db)
    configfile = os.path.expanduser(args.config)
    name = args.name
    depth_limit = args.depth

    print(f"[+] Filtering {callsfile} based on the filter {configfile} configuration...")
    calls_df = get_calls_table(callsfile)
    config = get_json_config(configfile)
    filters = create_calls_filters(config)
    calls_df = filter_calls(calls_df, filters)

    print("[+] Creating graph from call data...")
    g = digraph_from_calls(calls_df)
    g = filter_cc_with_source_nodes(g, get_syscalls)

    print("[+] Generating the graphical objects...")
    paths = set([node.filename for node in g.nodes()])
    path_colormap = create_colormap(paths)
    sources = get_syscalls(g)
    tree = create_hierarchy(g, sources, path_colormap, depth_limit=depth_limit, name=name)

    out = name + ".json"
    print(f"[+] Exporting graphical representation to {out}...")
    write_hierarchy(name+".json", tree)

    if args.port:
        print(f"[+] Running local server...")
        print(f"[+] Type localhost:{args.port} in your browser or [Ctrl+C] to quit...")
        run_server(args.port)


if __name__ == '__main__':
    main()
