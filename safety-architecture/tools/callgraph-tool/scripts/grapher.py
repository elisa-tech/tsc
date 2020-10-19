#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import graphviz as gv
import os
from collections import OrderedDict


class Grapher():

    def __init__(self, out):
        self.out = out
        self.maxdepth = 30

        self.digraph = gv.Digraph(filename=out)
        self.digraph.attr('graph', rankdir='LR')
        self.digraph.attr('node', shape='box')
        self.digraph.attr('node', style='rounded')
        self.digraph.attr('node', margin='0.3,0.1')
        self.digraph.attr('graph', concentrate='true')
        # Key: node name, Value: list of labels associated to node name
        self.nodelabels = {}

        # Initial number of entries in the graph
        self.initlen = len(self.digraph.body)

    def _add_node(self, function, filename, line):
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
        fillcolor = '#EEEEEE'
        # Add node to the graph
        self.digraph.node(
            node_name, label, style='rounded,filled', fillcolor=fillcolor)

    def _add_edge(self, row):
        edge_style = None
        if row.callee_calltype == "indirect":
            edge_style = "dashed"
        self.digraph.edge(
            "%s_%s" % (row.caller_filename, row.caller_function),
            "%s_%s" % (row.callee_filename, row.callee_function),
            style=edge_style)

    def graph(self, df):
        for row in df.itertuples():
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

    def render(self, filename):
        # Render the graph
        if len(self.digraph.body) <= self.initlen:
            return
        fname, extension = os.path.splitext(filename)
        ext = extension[1:]
        self.digraph.render(filename=fname, format=ext, cleanup=True)
