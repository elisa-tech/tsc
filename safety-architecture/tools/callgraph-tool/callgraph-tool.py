#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import logging
import multiprocessing
import os
import pandas as pd
import pickle
import Pyro4
import re

import cgutils as cgu

from IPython.utils.capture import capture_output
from build import convert_build_file, Engine, BuildLogFormat
from build_ftrace import ftrace_enrich_call_graph
from build_trigger import build_trigger_map, TriggerEngine
from cgutils import ansi_highlight, read_configuration_file
from llvm_parse import Function

multiprocessing.set_start_method('spawn', True)  # VS Code runtime error fix

call_graph = {}
inverse_call_graph = {}
caller_source_and_line = {}

dot_source_lr = '''
  digraph callgraph {
    rankdir=LR;
'''
dot_source_top_down = '''
  digraph callgraph {
'''
dot_source = dot_source_lr


def build_indirect_nodes(args):
    global call_graph
    indirect_nodes = []

    conf = read_configuration_file(args.config)

    for operation, callees in conf['Indirect'].items():
        print('build_indirect_nodes: %s, %s' % (operation, callees))

        caller = Function(operation, indirect=True)
        if caller not in call_graph:
            call_graph[caller] = []
            indirect_nodes.append(operation)

        for callee in callees:
            callee = Function(callee)
            if callee not in call_graph[caller]:
                call_graph[caller].append(callee)

    return indirect_nodes


def get_missing_nodes(call_graph):
    missing_nodes = []
    for node_out in call_graph:
        for node_in in call_graph[node_out]:
            if node_in not in call_graph.keys() and node_in not in missing_nodes:
                logging.info("Missing node: %s found in the edge from %s" % (node_in.name, node_out.name))
                missing_nodes.append(node_in)
    print("Missing %s nodes found in edges" % len(missing_nodes))
    nodes = [Function(node.name, args=node.args) for node in missing_nodes]
    return nodes


def build_call_graph(indirect_nodes, args):
    global call_graph

    manager = multiprocessing.Manager()
    call_graph_lock = manager.Lock()
    tmp_call_graph = manager.dict()

    print("Proceed to LLVM parse")

    with open(args.build[0], "r") as ins:
        try:
            pool = multiprocessing.Pool(multiprocessing.cpu_count())
            engine = Engine(indirect_nodes, call_graph_lock, tmp_call_graph, args)
            pool.map(engine, ins)
        finally:  # To make sure processes are closed in the end, even if errors happen
            pool.close()
            pool.join()

    call_graph.update(tmp_call_graph)
    missing_nodes = get_missing_nodes(call_graph)
    for node in missing_nodes:
        call_graph[node] = []


def get_caller_source_and_line_numbers(caller, call_graph_db, source_and_line_db):
    source_file = ''
    line_numbers = []

    if not source_and_line_db:
        for key in call_graph.keys():
            source_and_line_db[key] = (key.source_file, key.line_numbers)

    if caller in source_and_line_db:
        return source_and_line_db[caller]
    else:
        return ('', [])


def batch_get_callees(func_records, extended=False):
    global call_graph
    global supress_from_graph
    local_cg = call_graph
    cols = ["Callee", "Caller", "Indirect"]
    call_connections = []
    dropped = []
    for record in func_records:
        funcname, *_ = record
        if funcname in suppress_from_graph:
            continue
        f = Function(funcname)
        if f not in call_graph:
            dropped.append(record)
            # Perhaps store as a NaN entry to database
            continue
        callees_of_f = call_graph[f]
        record_slot = []
        for callee_single in callees_of_f:
            if not extended:
                record_slot.append((callee_single, funcname, callee_single.indirect))
            else:
                raise NotImplementedError
        call_connections.extend(record_slot)

    return call_connections, cols


def batch_get_callers(func_records, extended=False):
    global inverse_call_graph
    global suppress_from_graph
    call_connections = []
    dropped = []
    for record in func_records:
        funcname, *_ = record
        if funcname in suppress_from_graph:
            continue
        f = Function(funcname)
        if f not in inverse_call_graph:
            dropped.append(record)
            # Perhaps store as a NaN entry to database
            continue
        callers_of_f = inverse_call_graph[f]
        record_slot = []
        cols = []
        for caller_single in callers_of_f:
            if not extended:
                cols = ["Callee", "Caller", "Indirect"]
                record_slot.append((funcname, caller_single, caller_single.indirect))
            else:
                cols = ["Callee", "File", "Line", "Caller", "Indirect"]
                record_slot.append(record + (caller_single, caller_single.indirect))
        call_connections.extend(record_slot)

    return call_connections, cols


def build_callees(fetch_src_info=True):
    global call_graph
    global inverse_call_graph
    global caller_source_and_line

    if inverse_call_graph:
        return

    inverse_call_graph = {}
    for caller in call_graph:
        for callee in call_graph[caller]:
            caller_new = Function(caller.name, callee.args, source_file=caller.source_file,
                                  line_numbers=callee.line_numbers)

            if fetch_src_info:
                # Get file/line number of callee definition. Callees own file/linenumber tells where it's called
                (source_file, line_numbers) = get_caller_source_and_line_numbers(
                    callee, call_graph, caller_source_and_line)
            else:
                (source_file, line_numbers) = ('', [])

            callee_new = Function(callee.name, callee.args, source_file=source_file,
                                  line_numbers=line_numbers)

            if callee_new not in inverse_call_graph:
                inverse_call_graph[callee_new] = []
            inverse_call_graph[callee_new].append(caller_new)


default_suppress_from_graph = {
    'panic': True,
    'printk': True,
    'vprintk': True,
    'vscnprintf': True,
    'vsnprintf': True,
    'printk_deferred': True,
    'dump_stack': True,
    '__warn': True
}
suppress_from_graph = dict(default_suppress_from_graph)


def add_node_for_function(function, line_numbers, style="solid", view_base_dir="/"):
    url = ""
    if not view_base_dir.endswith("/"):
        view_base_dir += "/"
    if function.source_file:
        url = "file://" + view_base_dir + function.source_file
    return '"%s" [label="%s\n%s\n%s\nline:%s", URL="%s", style=%s]\n' % (function.name,
                                                                         cgu.demangle(function.name),
                                                                         function.name,
                                                                         function.source_file,
                                                                         str(line_numbers),
                                                                         url,
                                                                         style)


def add_connection(caller, callee, color="black", direction="forward", view_base_dir="/", line_number=""):
    url = ""
    if not view_base_dir.endswith("/"):
        view_base_dir += "/"
    if callee.source_file:
        url = "file://" + view_base_dir + callee.source_file

    callee_args = list()
    for arg in callee.args:
        callee_args.append(cgu.demangle(arg))

    return '"%s" -> "%s" [label="%s", color="%s", dir="%s", URL="%s"]\n' % (caller.name,
                                                                            callee.name,
                                                                            ', '.join(callee_args) + ' line: ' +
                                                                            str(line_number),
                                                                            color,
                                                                            direction,
                                                                            url)


def show_callees_recursive(function, lvl=0, max_depth=999, dot=False, view_base_dir=""):
    global call_graph
    global suppress_from_graph
    global dot_source

    if function.name in suppress_from_graph:
        return

    suppress_from_graph[function.name] = True

    if function not in call_graph:
        return

    callees = call_graph[function]
    if dot:
        dot_source += add_node_for_function(function, function.line_numbers, view_base_dir=view_base_dir)
        for callee in callees:
            if callee.args:
                dot_source += add_connection(function, callee, color="blue", view_base_dir=view_base_dir,
                                             line_number=callee.line_numbers)
            else:
                dot_source += add_connection(function, callee, view_base_dir=view_base_dir,
                                             line_number=callee.line_numbers)
            style = 'solid'
            if callee.indirect:
                style = 'dashed'

            dot_source += add_node_for_function(callee, callee.line_numbers, style, view_base_dir=view_base_dir)

        if lvl >= max_depth:
            dot_source += '"%s" -> "..."\n' % (function.name)
            return
    else:
        pad = ''
        for _ in range(lvl):
            pad += '  '

        callees_str = '%s%s -> %s' % (pad, function.name, ', '.join(str(c) for c in callees))
        if lvl % 2 == 0:
            print(ansi_highlight(callees_str))
        else:
            print(callees_str)

        if lvl >= max_depth:
            print('%s  ...' % (pad))
            return

    for callee in callees:
        show_callees_recursive(callee, lvl + 1, max_depth, dot)


def show_callers_recursive(function, lvl=0, max_depth=999, dot=False, view_base_dir=""):
    global inverse_call_graph
    global suppress_from_graph
    global dot_source

    if function.name in suppress_from_graph:
        return

    suppress_from_graph[function] = True

    if function not in inverse_call_graph:
        return

    pad = ''
    for _ in range(lvl):
        pad += '  '

    callers = inverse_call_graph[function]
    if dot:
        if function in call_graph:
            keys = list(call_graph.keys())
            function_in_call_graph = keys[keys.index(function)]
            line_numbers = function_in_call_graph.line_numbers
        else:
            line_numbers = []
        dot_source += add_node_for_function(function, line_numbers, view_base_dir=view_base_dir)
        for caller in callers:
            if caller.args:
                dot_source += add_connection(function, caller, color="blue", direction="back",
                                             view_base_dir=view_base_dir, line_number=caller.line_numbers)
            else:
                dot_source += add_connection(function, caller, direction="back", view_base_dir=view_base_dir,
                                             line_number=caller.line_numbers)
            style = 'solid'
            if caller.indirect:
                style = 'dashed'

            (source_file, line_numbers) = get_caller_source_and_line_numbers(caller)

            dot_source += add_node_for_function(caller, line_numbers, style, view_base_dir=view_base_dir)

        if lvl >= max_depth:
            dot_source += '"%s" -> "..." [dir=back]\n' % (function.name)
            return
    else:
        callers_str = '%s%s <- %s' % (pad, function, ', '.join(str(c) for c in callers))
        if lvl % 2 == 0:
            print(ansi_highlight(callers_str))
        else:
            print(callers_str)

        if lvl >= max_depth:
            print('%s  ...' % (pad))
            return

    for caller in callers:
        show_callers_recursive(caller, lvl + 1, max_depth, dot, view_base_dir=view_base_dir)


def find_path_recursive(path_from, path_to, breadcrumbs, lvl=0, max_depth=-1, reverse=False, dot=False):
    global call_graph
    global dot_source

    if lvl >= max_depth:
        return False

    breadcrumbs.append(path_from)

    if path_from not in call_graph:
        return False

    callees = call_graph[path_from]

    for callee in callees:
        if callee == path_to:
            breadcrumbs.append(path_to)
            if dot:
                if not reverse:
                    dot_source += ' -> '.join(str(b) for b in breadcrumbs)
                else:
                    dot_source += ' -> '.join(str(b) for b in breadcrumbs[::-1]) + ' [dir=back]'
            else:
                if not reverse:
                    print(' -> '.join(str(b) for b in breadcrumbs))
                else:
                    print(' <- '.join(str(b) for b in breadcrumbs[::-1]))
            return True
        else:
            if find_path_recursive(callee, path_to, list(breadcrumbs), lvl + 1, max_depth, reverse, dot):
                return True

    return False


multipath_output = {}


def find_multipath_recursive(path_from, path_to, breadcrumbs, lvl=0, max_depth=-1):
    global inverse_call_graph
    global multipath_output

    if lvl >= max_depth:
        return False

    breadcrumbs.append(path_from)

    if path_from not in inverse_call_graph:
        return False

    callees = inverse_call_graph[path_from]

    for callee in callees:
        if callee in path_to:
            br = breadcrumbs[::]
            br.append(callee)
            if not path_to[callee] in multipath_output:
                multipath_output[path_to[callee]] = br
            del(path_to[callee])

    for callee in callees:
        if find_multipath_recursive(callee, path_to, list(breadcrumbs), lvl + 1, max_depth):
            return True

    return False


def show_graphviz(view_type):
    global dot_source

    dot_source += "}\n"
    filename = '/tmp/callgraph.%s' % view_type
    cgu.exec_cmd_with_stdin("dot -T%s -o%s && xdg-open %s" % (view_type, filename, filename), dot_source)


@Pyro4.expose
class Service:

    SERVICE_FILE = '/tmp/callgraph-tool.service'

    def serve(self, args):
        print(ansi_highlight("\nserve %s\n" % args, '38;5;206'))

        with capture_output() as c:
            self.parse(args)
        c()
        return c.stdout

    def parse(self, args):
        global call_graph
        global dot_source
        global suppress_from_graph
        global trigger_map
        dot_source = dot_source_lr
        suppress_from_graph = dict(default_suppress_from_graph)

        if args['no_indirect']:
            to_be_deleted = []
            for caller in call_graph:
                if caller.indirect:
                    to_be_deleted.append(caller)
                    continue
                for callee in call_graph[caller]:
                    if callee.indirect:
                        call_graph[caller].remove(callee)
            for caller in to_be_deleted:
                del call_graph[caller]

        if args['depth'] < 0:
            if args['graph'] or args['inverse_graph']:
                args['depth'] = 3
            elif args['multipath']:
                args['depth'] = 25
            else:
                args['depth'] = 20

        if args['graph']:
            function = Function(args['graph'])
            for key in call_graph.keys():
                if key.name != function.name:
                    continue
                show_callees_recursive(key, max_depth=args['depth'], dot=args['view'],
                                       view_base_dir=args['view_base_dir'])
                break

            if args['view']:
                show_graphviz(args['view_type'])

        if args['inverse_graph']:
            build_callees()
            show_callers_recursive(Function(args['inverse_graph']), max_depth=args['depth'], dot=args['view'],
                                   view_base_dir=args['view_base_dir'])
            if args['view']:
                show_graphviz(args['view_type'])

        if args['batch_inverse_graph']:
            build_callees(fetch_src_info=False)
            with open(args['batch_inverse_graph'], 'rb') as stream:
                records = pickle.load(stream)
                connected_calls, cols = batch_get_callers(records)
                df = pd.DataFrame.from_records(connected_calls, columns=cols)
                df.to_csv("connected_calls_inv.csv", index=False)

        if args['batch_graph']:
            with open(args['batch_graph'], 'rb') as stream:
                records = pickle.load(stream)
                connected_calls, cols = batch_get_callees(records)
                df = pd.DataFrame.from_records(connected_calls, columns=cols)
                df.to_csv("connected_calls.csv", index=False)

        if args['path']:
            path_from, path_to = map(Function, args['path'].split('..'))
            for i in range(args['depth']):
                # try direct path first
                breadcrumbs = []
                dot_source = dot_source_top_down
                if find_path_recursive(path_from, path_to, breadcrumbs, max_depth=i, dot=args['view']):
                    if args['view']:
                        show_graphviz(args['view_type'])
                    return
                # try reverse path
                breadcrumbs = []
                dot_source = dot_source_top_down
                if find_path_recursive(path_to, path_from, breadcrumbs, max_depth=i, reverse=True, dot=args['view']):
                    if args['view']:
                        show_graphviz(args['view_type'])
                    return
            print("Can't find code path between " + args['path'])

        if args['multipath']:
            build_callees()

            conf = read_configuration_file(args['config'])

            path_from = Function(args['multipath'])
            path_to = {}
            multipath_order = []
            for syscall, entry_point in conf['Direct'].items():
                if isinstance(entry_point, list):
                    for point in entry_point:
                        path_to[Function(point)] = syscall
                else:
                    path_to[Function(entry_point)] = syscall
                multipath_order.append(syscall)

            global multipath_output
            multipath_output = {}

            for i in range(args['depth']):
                # print('Depth %d' % i)
                breadcrumbs = []
                find_multipath_recursive(path_from, path_to, breadcrumbs, max_depth=i)

            for syscall in multipath_order:
                if syscall in multipath_output:
                    br = multipath_output[syscall]
                    print(ansi_highlight(syscall + ': ', '38;5;206') + ' <- '.join(str(b) for b in br))

        if args['map_trigger']:
            if not os.path.isfile(args['trgdb']):
                print("Warning: Trigger database does not exist")
            for trigger in trigger_map:
                for callee in trigger_map[trigger]:
                    if callee.name == args['map_trigger']:
                        print(trigger)


def get_args():
    parser = argparse.ArgumentParser(description='Call graph tool', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--config', default=os.path.dirname(os.path.realpath(__file__)) + '/configuration.yaml',
                        help='Use alternative configuration file')
    parser.add_argument('--build', '-b', metavar='BUILDLOG', nargs=1, help='Build call graph from build log.')
    parser.add_argument('--build_log_format', '-blf',
                        type=BuildLogFormat, metavar='FORMAT', default=BuildLogFormat.KERNEL_C.value,
                        help='Set build log format. (default: %(default)s)\n'
                        '  ' + BuildLogFormat.KERNEL_C.value + ' = reads linux kernel build log format. '
                        '(make V=1 | tee buildlog.txt)\n'
                        '  ' + BuildLogFormat.KERNEL_CLANG.value + ' = reads ClangBuiltLinux build log format\n'
                        '  ' + BuildLogFormat.LL_CLANG.value + ' = uses existing clang .ll files\n'
                        '  ' + BuildLogFormat.CPLUSPLUS.value + ' = plain build log from c++ builds')
    parser.add_argument('--build_exclude', '-be', default='tools,scripts', help='Exclude files/directories')
    parser.add_argument('--build_trigger_map', action='store_true', help='Build flat trigger map only')
    parser.add_argument('--arch', default='x86', help='Target architecture')
    parser.add_argument('--clang', default='clang', help='Path to clang executable')
    parser.add_argument('--ftrace', '-ft', default=os.path.dirname(os.path.realpath(__file__)) + '/ftrace.log',
                        help='Enrich call graph using ftrace.')
    parser.add_argument('--ftrace_enrich', '-fe', action='store_true',
                        help='Enrich current call_graph and '
                             'write enriched call_graph as <original pickle file>.ftrace')
    parser.add_argument('--fast_build', '-fb', action='store_true',
                        help='Enable to quick build without recompiling sources (reuse existing llvm files)')
    parser.add_argument('--trgdb', default=os.path.dirname(os.path.realpath(__file__)) + '/trigger_call_map.pickle',
                        help='Use alternative trigger call db file')
    parser.add_argument('--db', default=os.path.dirname(os.path.realpath(__file__)) + '/call_graph.pickle',
                        help='Use alternative db file')
    parser.add_argument('--graph', '-g', metavar='FUNCTION', help='Get call graph of a function')
    parser.add_argument('--depth', '-d', default=-1, type=int,
                        help='Max recursion depth.  Default is 3 for call graph, 20 for path, 25 for multipath.')
    parser.add_argument('--inverse_graph', '-i', metavar='FUNCTION', help='Get inverse call graph of a function')
    parser.add_argument('--path', '-p', metavar='FUNCTION',
                        help='Find code path between two functions (separated with ..)')
    help_mp = 'Find possible code paths from the given function to all functions listed in configuration.yaml'
    parser.add_argument('--multipath', '-mp', metavar='FUNCTION', help=help_mp)
    parser.add_argument('--map_trigger', '-ms', metavar='FUNCTION',
                        help='Map function to triggers specified in configuration.yaml')
    parser.add_argument('--view', '-v', action='store_true', help='View with graphviz')
    parser.add_argument('--view_type', '-vt', default='svg', help='View type: pdf or png (default: pdf)')
    parser.add_argument('--view_base_dir', '-vb', default="", help='Set base dir for the source file links')
    parser.add_argument('--service', '-s', action='store_true', help='Start or restart service')
    parser.add_argument('--client', '-c', action='store_true', help='Connect to service and forward args to it')
    parser.add_argument('--no_indirect', '-ni', action='store_true', help='Ignore indirect paths')
    parser.add_argument('--batch_graph', '-bg',
                        help='List of function calls for batch callgraph processing')
    parser.add_argument('--batch_inverse_graph', '-big',
                        help='List of function calls for inverse batch callgraph processing')

    return parser.parse_args()


def main():
    global call_graph
    global trigger_map

    args = get_args()

    if args.build and (os.path.isfile(args.build[0]) or os.path.isdir(args.build[0])):
        build_path = args.build[0]
        args.build[0] = convert_build_file(build_path, args.build_log_format)
        indirect_nodes = build_indirect_nodes(args)
        build_call_graph(indirect_nodes, args)

        with open(args.db, 'wb') as stream:
            pickle.dump(call_graph, stream, protocol=pickle.HIGHEST_PROTOCOL)

    if args.ftrace_enrich and os.path.isfile(args.ftrace):
        with open(args.db, 'rb') as stream:
            call_graph = pickle.load(stream)
        ftrace_enrich_call_graph(args.ftrace, call_graph)
        with open(args.db + '.ftrace', 'wb') as stream:
            pickle.dump(call_graph, stream, protocol=pickle.HIGHEST_PROTOCOL)

    if args.build_trigger_map:
        with open(args.db, 'rb') as stream:
            call_graph = pickle.load(stream)
        trigger_map = build_trigger_map(call_graph, args.config)
        with open(args.trgdb, 'wb') as stream:
            pickle.dump(trigger_map, stream, protocol=pickle.HIGHEST_PROTOCOL)

    if args.client:
        try:
            existing_service = open(Service.SERVICE_FILE, 'r').read()
            service = Pyro4.Proxy(existing_service)
            print(service.serve(vars(args)))
        except IOError:
            print("Service is not running, run %s -s" % __file__)
            exit(1)
    else:
        with open(args.db, 'rb') as stream:
            call_graph = pickle.load(stream)

        if os.path.isfile(args.trgdb):
            with open(args.trgdb, 'rb') as stream:
                trigger_map = pickle.load(stream)

        if args.service:
            if os.path.isfile(Service.SERVICE_FILE):
                print('Service already running or there is a stale file %s' % Service.SERVICE_FILE)
                return

            daemon = Pyro4.Daemon()
            uri = daemon.register(Service)
            print('Started service %s' % uri)

            with open(Service.SERVICE_FILE, "w") as stream:
                stream.write(str(uri))

            daemon.requestLoop()

            os.remove(Service.SERVICE_FILE)
        else:
            service = Service()
            service.parse(vars(args))


if __name__ == "__main__":
    logging.basicConfig(format='\033[30;1m%(levelname)s:\033[0m %(message)s', level=logging.INFO)
    main()