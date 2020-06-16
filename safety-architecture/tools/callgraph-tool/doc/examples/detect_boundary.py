#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import networkx as nx
import os
import pandas as pd
import pickle
import sys


callgraphtool_path = os.path.dirname(os.path.abspath(__file__)) + '/../../'
sys.path.append(callgraphtool_path)

from db import GraphDb  # noqa E402

"""
_LIN_DIRS = [
    "arch", "block", "certs", "crypto", "drivers", "firmware", "fs", "include", "init", "ipc",
    "kernel", "lib", "mm", "net", "samples", "scripts", "security", "sound", "tools", "usr", "virt"
]
"""
_SEL_DIRS = ["arch", "include", "mm"]


def include_filelist(module, filelist=None):
    include_fl = []
    if filelist:
        with open(filelist, 'r') as fl:
            for line in fl:
                if line.startswith(module):
                    if 'Kconfig' not in line and 'Makefile' not in line:
                        p = os.path.normpath(line.strip())
                        include_fl.append(p)
    return include_fl


def file_filter(fileset):
    def vertex_file_filter(node):
        return node.source_file in fileset
    return vertex_file_filter


def boundary_out_in(outname, inname):
    def filter12(node1, node2):
        return node1.source_file.startswith(outname) and node2.source_file.startswith(inname)
    return filter12


def boundary(outname, file_filter=lambda x: True):
    def filter_boundary(node1, node2):
        return node1.source_file.startswith(outname) and file_filter(node1) and\
            not node2.source_file.startswith(outname)
    return filter_boundary


def interface(inname, file_filter=lambda x: True):
    def filter_interface(node1, node2):
        return not node1.source_file.startswith(inname) and\
            node2.source_file.startswith(inname) and file_filter(node2)
    return filter_interface


def normalize_paths(g):
    for k, vals in g.items():
        k.source_file = str(os.path.normpath(k.source_file))
        for v in vals:
            v.source_file = str(os.path.normpath(v.source_file))


def cg2nx(g):
    normalize_paths(g)
    return nx.DiGraph(g)


def graph_stats(g, brief=False):
    print("Node count: ", len(g.nodes()))
    print("Edge count: ", len(g.edges()))
    print("Number of weakly connected compoments: ", nx.number_weakly_connected_components(g))

    if not brief:
        largest_cc = max(nx.weakly_connected_components(g), key=len)
        smallest_cc = min(nx.weakly_connected_components(g), key=len)
        print("Largest connected component: ", len(largest_cc))
        print("Smallest connected component: ", len(smallest_cc))
        acc = 0
        for c in nx.weakly_connected_components(g):
            if len(c) == 1:
                acc += 1

        print("Count of size==1 connected components: ", acc)


def create_pd_entry(sel, node1, node2):
    node1_ln = ",".join(node1.line_numbers) if node1.line_numbers else ""
    node2_ln = ",".join(node2.line_numbers) if node2.line_numbers else ""
    entry = [sel, node1.name, node1.source_file, node1_ln,
             node2.name, node2.source_file, node2_ln]
    return entry


def analyse(dbs, outlist, fin=None, fout=None):
    cgs = []
    for db in dbs:
        print("\nLoading: ", db)
        with open(db, 'rb') as handle:
            cg = pickle.load(handle)
            g = cg2nx(cg)
            graph_stats(g)
            cgs.append(g)

    columns = ["Module", "Caller", "CallerFile", "CallerLine", "Callee", "CalleeFile", "CalleeLine"]
    dflist = []

    for idx, filelist in enumerate(outlist):
        pd_entries = []
        # define driver boundary
        if fout:
            drivers_fl = include_filelist('drivers/', filelist)
            drivers_ffilter = file_filter(drivers_fl)
            drivers_bo = boundary('drivers/', drivers_ffilter)
        else:
            drivers_bo = boundary('drivers/')
        # filter driver side
        driver_boundary_g = nx.subgraph_view(cgs[idx], filter_edge=drivers_bo)

        sel_bi = {sel: sel + '/' for sel in _SEL_DIRS}
        sel_boundary_g = {}
        sel_interface = {}

        for sel, sbi in sel_bi.items():
            # define mm boundary
            if fin:
                sel_fl = include_filelist(sbi, fin)
                sel_ffilter = file_filter(sel_fl)
                sel_iface = interface(sbi, sel_ffilter)
            else:
                sel_iface = interface(sbi)
            # filter mm side
            sg = nx.subgraph_view(driver_boundary_g, filter_edge=sel_iface)
            # induce subgraphs from the edges (i.e. filter nodes wo edges)
            sel_boundary_g[sel] = sg.edge_subgraph(sg.edges())
            # collect module interface
            mod_interface = set()
            for edge in sel_boundary_g[sel].edges():
                node1, node2 = edge
                # cache for dataframe
                pd_entries.append(create_pd_entry(sel, node1, node2))
                # cache for file list
                mod_interface.add(node2)
            sel_interface[sel] = mod_interface
        # save the data
        summary = "summary_" + outlist[idx]
        print(f"Saving summary to {summary}")
        mmfilter = set()
        with open(summary, 'w') as o:
            for sel, iface in sel_interface.items():
                o.write(sel + ":\n\n")
                for f in sorted(iface, key=lambda x: x.source_file):
                    mmfilter.add(f.source_file)
                    o.write(f.source_file + ": " + f.name + '\n')

        mmfiltout = "mmfilter_" + outlist[idx]
        with open(mmfiltout, 'w') as o:
            for f in sorted(mmfilter):
                o.write(f + '\n')

        df = pd.DataFrame(pd_entries, columns=columns)
        dflist.append(df)
        print(f"Save boundary database to {outlist[idx]}")
        df.to_csv(outlist[idx], index=False)

    return dflist


def getargs():
    desc = "Detect functional interface between specified parts of the code database"
    parser = argparse.ArgumentParser(description=desc)
    help_db = "Path to callgraph database file"
    parser.add_argument('db', help=help_db)
    help_out = "Output file name"
    parser.add_argument('out', help=help_out)
    help_fout = "Filter file containing list of the paths to the files to include in boundary definition."\
        " Refers to the files in caller module."
    parser.add_argument('--fout', help=help_fout)
    help_fin = "Filter file containing list of the paths to the files to include in boundary definition."\
        " Refers to the files in called module."
    parser.add_argument('--fin', help=help_fin)

    return parser.parse_args()


def main():
    args = getargs()
    db = os.path.expanduser(args.db)
    out = os.path.expanduser(args.out)
    filtin = os.path.expanduser(args.fin) if args.fin else None
    filtout = os.path.expanduser(args.fout) if args.fout else None
    analyse([db], [out], filtin, filtout)


if __name__ == '__main__':
    main()
