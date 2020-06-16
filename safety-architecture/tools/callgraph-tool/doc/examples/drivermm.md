<!--
SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)

SPDX-License-Identifier: Apache-2.0
-->

# Detecting boundary between drivers and memory management module

We tried to identify relevant interface between drivers and memory management in Linux kernel by comparing the call graphs for two different architectures (x86 and mips). We wrote a simple [script](detect_boundary.py) for this purpose. Before running the script the user first needs to produce call graph databases for both architectures using the procedure described in our documentation. 

Using the graph theory terminology we try to define the driver - memory management boundary a bit more formally. Call graph G(V, E) is a directed graph of Linux source tree where V is a set of
nodes representing the functions in the code. Edges E is a set of 'caller function' - 'called function' connections. Caller function is a source of an edge and called function is a sink of this edge. Self-loops
are also allowed (recursive function calls). In order to define boundary we assume that the set V can be split in a group of disjoint subsets each representing a single functional module (subsystem) in a
kernel (e.g. drivers, kernel, filesystem, memory management). The boundary between the two modules is represented as a set of edges Eb where source node is in one module and sink node is a member of a second module. With this definition in mind we can
implement the code that detects the appropriate edges to detect boundary between two modules. 

One problem with this definition is the underlying assumption that the call graph is complete, i.e. that all
the function calls are properly detected. We know that this is not true for our call graph data because we still don't detect automatically all indirect calls in the graph. In addition, part of the connections might be incorrect because we don't use full function signature (with arguments). Analyzing some simple statistics of our graph, we can confirm this to be true. Most of the detected callgraph nodes are connected to each other but there is still significant number of unconnected components. A great majority of these unconnected components that we inspected manually are undetected indirect calls (most of them are used through struct member callback and some of them 'free-standing' pointer type variables initialized through function call).
We assume that there is a larger number of unconnected components in mips build because our indirection call detection configuration file is entirely based on x86 kernel analysis.

In order to simplify further analysis we ignore this fact for now. Once the callgraph functionality is sufficiently improved to circumvent the mentioned problems we can easily rerun the analysis and yield more reliable results. The other problem is that there doesn't exist a common agreement on which code belongs to which subsystems. While the situation with drivers subsystem is pretty much clear we cannot say the same for memory management code. The memory management is implemented in various parts of the code (generic code, architecture dependent code, various
macros, etc).


The detect_boundary script is able to detect a boundary between one specific and one or more other modules. The memory management code is not contained in a single folder but scattered across different directories in kernel tree (mm, include, arch) so we need to include all these folders into the analysis. We first filter out relevant files from drivers. Once we have limited our search to memory management related directories we can aggregate the set of files that are relevant for our boundary definition.

```
detect_boundary.py /tmp/mmbound/x86/call_graph.pickle nofilt_iface_x86.csv
detect_boundary.py /tmp/mmbound/mips/call_graph.pickle nofilt_iface_mips.csv
```

This commands produce the summary files which we further manually analyze to create a specific file filter for memory management related source files. As already explained, there doesn't exist a firm
definition of what exactly is a memory management subsystem (in terms of a complete list of source files) so we need to manually select the list that we think is relevant.

The reason we don't detect any files in mm directory is the fact that the most of the interface (function declarations) for this code is placed under include directory. Callgraph tool detects location of the
declaration for callees and not definition because these are in separate compilation units for most of the time.
After manual inspection we can see that most of those files are not relevant for the memory management. We create an additional filter (whitelist) file - [mmfilter](mmfilter.csv) based on our memory management study and the files we detected in the manual inspection.
We can rerun the filtering process using the filter file:

```
detect_boundary.py /tmp/mmbound/x86/call_graph.pickle --fin mmfilter.csv iface_x86.csv
detect_boundary.py /tmp/mmbound/mips/call_graph.pickle --fin mmfilter.csv iface_mips.csv
```

creating much more specific set of candidates for the driver - memory management interface.
