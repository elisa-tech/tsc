# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import cgutils as cgu
import logging
import os
import pandas as pd
import pickle
import Pyro4

from IPython.utils.capture import capture_output
from llvm_parse import Function

dot_source_lr = '''
  digraph callgraph {
    rankdir=LR;
'''
dot_source_top_down = '''
  digraph callgraph {
'''

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


@Pyro4.expose
class Service:
    SERVICE_FILE = '/tmp/callgraph-tool.service'

    def __init__(self, call_graph, trigger_map):
        self._call_graph = call_graph
        self._inverse_call_graph = {}
        self._multipath_output = {}
        self._trigger_map = trigger_map
        self._caller_source_and_line = {}

    def functionality_writer(self, args):
        print(args)
        return

    def serve(self, args):
        self.functionality_writer(cgu.ansi_highlight("\nserve %s\n" % args, '38;5;206'))

        with capture_output() as c:
            self.parse(args)
        c()
        return c.stdout

    def parse(self, args):
        # Always reset these
        self._dot_source = dot_source_lr
        self._suppress_from_graph = dict(default_suppress_from_graph)

        if args['no_indirect']:
            to_be_deleted = []
            for caller in self._call_graph:
                if caller.indirect:
                    to_be_deleted.append(caller)
                    continue
                for callee in self._call_graph[caller]:
                    if callee.indirect:
                        self._call_graph[caller].remove(callee)
            for caller in to_be_deleted:
                del self._call_graph[caller]

        if args['depth'] < 0:
            if args['graph'] or args['inverse_graph']:
                args['depth'] = 3
            elif args['multipath']:
                args['depth'] = 25
            else:
                args['depth'] = 20

        if args['graph']:
            function = Function(args['graph'])
            for key in self._call_graph.keys():
                if key.name != function.name:
                    continue
                self.show_callees_recursive(key, max_depth=args['depth'], dot=args['view'],
                                            view_base_dir=args['view_base_dir'])
                break

            if args['view']:
                self.show_graphviz(args['view_type'])

        if args['inverse_graph']:
            self.build_callees()
            self.show_callers_recursive(Function(args['inverse_graph']),
                                        max_depth=args['depth'], dot=args['view'],
                                        view_base_dir=args['view_base_dir'])
            if args['view']:
                self.show_graphviz(args['view_type'])

        if args['batch_inverse_graph']:
            self.build_callees(fetch_src_info=False)
            with open(args['batch_inverse_graph'], 'rb') as stream:
                records = pickle.load(stream)
                connected_calls, cols = self.batch_get_callers(records)
                df = pd.DataFrame.from_records(connected_calls, columns=cols)
                df.to_csv("connected_calls_inv.csv", index=False)

        if args['batch_graph']:
            with open(args['batch_graph'], 'rb') as stream:
                records = pickle.load(stream)
                connected_calls, cols = self.batch_get_callees(records)
                df = pd.DataFrame.from_records(connected_calls, columns=cols)
                df.to_csv("connected_calls.csv", index=False)

        if args['path']:
            path_from, path_to = map(Function, args['path'].split('..'))
            for i in range(args['depth']):
                # try direct path first
                breadcrumbs = []
                self._dot_source = dot_source_top_down
                if self.find_path_recursive(path_from, path_to, breadcrumbs,
                                            max_depth=i, dot=args['view']):
                    if args['view']:
                        self.show_graphviz(args['view_type'])
                    return
                # try reverse path
                breadcrumbs = []
                self._dot_source = dot_source_top_down
                if self.find_path_recursive(path_to, path_from, breadcrumbs,
                                            max_depth=i, reverse=True, dot=args['view']):
                    if args['view']:
                        self.show_graphviz(args['view_type'])
                    return
            self.functionality_writer("Can't find code path between " + args['path'])

        if args['multipath']:
            self.build_callees()

            conf = cgu.read_configuration_file(args['config'])

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

            self._multipath_output = {}

            for i in range(args['depth']):
                logging.debug('Depth %d' % i)
                breadcrumbs = []
                self.find_multipath_recursive(path_from, path_to, breadcrumbs, max_depth=i)

            for syscall in multipath_order:
                if syscall in self._multipath_output:
                    br = self._multipath_output[syscall]
                    self.functionality_writer(cgu.ansi_highlight(syscall + ': ', '38;5;206') +
                                              ' <- '.join(str(b) for b in br))

        if args['map_trigger']:
            if not os.path.isfile(args['trgdb']):
                self.functionality_writer("Warning: Trigger database does not exist")
            for trigger in self._trigger_map:
                for callee in self._trigger_map[trigger]:
                    if callee.name == args['map_trigger']:
                        self.functionality_writer(trigger)

    def add_node_for_function(self, function, line_numbers, style="solid", view_base_dir="/"):
        url = ""
        if not view_base_dir.endswith("/"):
            view_base_dir += "/"
        if function.source_file:
            url = "file://" + view_base_dir + function.source_file

        fname = function.name
        dfname = cgu.demangle(function.name)
        if fname != dfname:
            fname = dfname + '\n' + fname
        if isinstance(line_numbers, list):
            # sometimes macro expansions result in multiple calls to same function in one line
            line_numbers = list(set(line_numbers))
        return '"%s" [label="%s\n%s\nline:%s", URL="%s", style=%s, color="%s"]\n' % (
            function.name,
            fname,
            function.source_file,
            str(line_numbers),
            url,
            style,
            color)

    def add_connection(self, caller, callee, color="black", direction="forward", view_base_dir="/", line_number=""):
        url = ""
        if not view_base_dir.endswith("/"):
            view_base_dir += "/"
        if callee.source_file:
            url = "file://" + view_base_dir + callee.source_file

        callee_args = list()
        if isinstance(line_number, list):
            line_number = list(set(line_number))
        # for arg in callee.args:
        #    callee_args.append(cgu.demangle(arg))

        return '"%s" -> "%s" [label="%s", color="%s", dir="%s", URL="%s"]\n' % (caller.name,
                                                                                callee.name,
                                                                                ', '.join(callee_args) + ' line: ' +
                                                                                str(line_number),
                                                                                color,
                                                                                direction,
                                                                                url)

    def show_callees_recursive(self, function, lvl=0, max_depth=999, dot=False, view_base_dir=""):
        if function.name in self._suppress_from_graph:
            return

        self._suppress_from_graph[function.name] = True

        if function not in self._call_graph:
            return

        callees = self._call_graph[function]
        if dot:
            self._dot_source += self.add_node_for_function(function, function.line_numbers,
                                                           view_base_dir=view_base_dir)
            for callee in callees:
                if callee.args:
                    self._dot_source += self.add_connection(function, callee, color="blue",
                                                            view_base_dir=view_base_dir,
                                                            line_number=callee.line_numbers)
                else:
                    self._dot_source += self.add_connection(function, callee, view_base_dir=view_base_dir,
                                                            line_number=callee.line_numbers)
                style = 'solid'
                if callee.indirect:
                    style = 'dashed'

                self._dot_source += self.add_node_for_function(callee, callee.line_numbers, style,
                                                               view_base_dir=view_base_dir)

            if lvl >= max_depth:
                self._dot_source += '"%s" -> "..."\n' % (function.name)
                return
        else:
            pad = ''
            for _ in range(lvl):
                pad += '  '

            callees_str = '%s%s -> %s' % (pad, function.name, ', '.join(str(c) for c in callees))
            if lvl % 2 == 0:
                self.functionality_writer(cgu.ansi_highlight(callees_str))
            else:
                self.functionality_writer(callees_str)

            if lvl >= max_depth:
                self.functionality_writer('%s  ...' % (pad))
                return

        for callee in callees:
            self.show_callees_recursive(callee, lvl + 1, max_depth, dot)

    def show_callers_recursive(self, function,
                               lvl=0, max_depth=999, dot=False, view_base_dir=""):
        if function.name in self._suppress_from_graph:
            return

        self._suppress_from_graph[function.name] = True

        if function not in self._inverse_call_graph:
            return

        pad = ''
        for _ in range(lvl):
            pad += '  '

        callers = self._inverse_call_graph[function]
        if dot:
            if function in self._call_graph:
                keys = list(self._call_graph.keys())
                function_in_call_graph = keys[keys.index(function)]
                line_numbers = function_in_call_graph.line_numbers
            else:
                line_numbers = []
            self._dot_source += self.add_node_for_function(function, line_numbers, view_base_dir=view_base_dir)
            for caller in callers:
                if caller.args:
                    self._dot_source += self.add_connection(function, caller, color="blue", direction="back",
                                                            view_base_dir=view_base_dir,
                                                            line_number=caller.line_numbers)
                else:
                    self._dot_source += self.add_connection(function, caller, direction="back",
                                                            view_base_dir=view_base_dir,
                                                            line_number=caller.line_numbers)
                style = 'solid'
                if caller.indirect:
                    style = 'dashed'

                (source_file, line_numbers) = self.get_caller_source_and_line_numbers(caller,
                                                                                      self._caller_source_and_line)

                self._dot_source += self.add_node_for_function(caller, line_numbers, style,
                                                               view_base_dir=view_base_dir)

            if lvl >= max_depth:
                self._dot_source += '"%s" -> "..." [dir=back]\n' % (function.name)
                return
        else:
            callers_str = '%s%s <- %s' % (pad, function, ', '.join(str(c) for c in callers))
            if lvl % 2 == 0:
                self.functionality_writer(cgu.ansi_highlight(callers_str))
            else:
                self.functionality_writer(callers_str)

            if lvl >= max_depth:
                self.functionality_writer('%s  ...' % (pad))
                return

        for caller in callers:
            self.show_callers_recursive(caller, lvl + 1, max_depth, dot,
                                        view_base_dir=view_base_dir)

    def find_path_recursive(self, path_from, path_to, breadcrumbs, lvl=0, max_depth=-1, reverse=False, dot=False):
        if lvl >= max_depth:
            return False

        breadcrumbs.append(path_from)

        if path_from not in self._call_graph:
            return False

        callees = self._call_graph[path_from]

        for callee in callees:
            if callee == path_to:
                breadcrumbs.append(path_to)
                if dot:
                    if not reverse:
                        self._dot_source += ' -> '.join(str(b) for b in breadcrumbs)
                    else:
                        self._dot_source += ' -> '.join(str(b) for b in breadcrumbs[::-1]) + ' [dir=back]'
                else:
                    if not reverse:
                        self.functionality_writer(' -> '.join(str(b) for b in breadcrumbs))
                    else:
                        self.functionality_writer(' <- '.join(str(b) for b in breadcrumbs[::-1]))
                return True
            else:
                if self.find_path_recursive(callee, path_to, list(breadcrumbs), lvl + 1, max_depth, reverse, dot):
                    return True

        return False

    def find_multipath_recursive(self, path_from, path_to, breadcrumbs, lvl=0, max_depth=-1):
        if lvl >= max_depth:
            return False

        breadcrumbs.append(path_from)

        if path_from not in self._inverse_call_graph:
            return False

        callees = self._inverse_call_graph[path_from]

        for callee in callees:
            if callee in path_to:
                br = breadcrumbs[::]
                br.append(callee)
                if not path_to[callee] in self._multipath_output:
                    self._multipath_output[path_to[callee]] = br
                del(path_to[callee])

        for callee in callees:
            if self.find_multipath_recursive(callee, path_to, list(breadcrumbs), lvl + 1, max_depth):
                return True

        return False

    def show_graphviz(self, view_type):
        self._dot_source += "}\n"
        filename = '/tmp/callgraph.%s' % view_type
        cgu.exec_cmd_with_stdin("dot -T%s -o%s && xdg-open %s" % (view_type, filename, filename), self._dot_source)

    def build_callees(self, fetch_src_info=True):
        self._inverse_call_graph = {}
        for caller in self._call_graph:
            for callee in self._call_graph[caller]:
                caller_new = Function(caller.name, callee.args, source_file=caller.source_file,
                                      line_numbers=callee.line_numbers)

                if fetch_src_info:
                    # Get file/line number of callee definition. Callees own file/linenumber tells where it's called
                    (source_file, line_numbers) = self.get_caller_source_and_line_numbers(
                        callee, self._caller_source_and_line)
                else:
                    (source_file, line_numbers) = ('', [])

                callee_new = Function(callee.name, callee.args, source_file=source_file,
                                      line_numbers=line_numbers)

                if callee_new not in self._inverse_call_graph:
                    self._inverse_call_graph[callee_new] = []
                self._inverse_call_graph[callee_new].append(caller_new)

    def get_caller_source_and_line_numbers(self, caller, source_and_line_db):
        if not source_and_line_db:
            for key in self._call_graph.keys():
                source_and_line_db[key] = (key.source_file, key.line_numbers)

        if caller in source_and_line_db:
            return source_and_line_db[caller]
        else:
            return ('', [])

    def batch_get_callees(self, func_records, extended=False):
        cols = ["Callee", "Caller", "Indirect"]
        call_connections = []
        dropped = []
        for record in func_records:
            funcname, *_ = record
            if funcname in self._suppress_from_graph:
                continue
            f = Function(funcname)
            if f not in self._call_graph:
                dropped.append(record)
                # Perhaps store as a NaN entry to database
                continue
            callees_of_f = self._call_graph[f]
            record_slot = []
            for callee_single in callees_of_f:
                if not extended:
                    record_slot.append((callee_single, funcname, callee_single.indirect))
                else:
                    raise NotImplementedError
            call_connections.extend(record_slot)

        return call_connections, cols

    def batch_get_callers(self, func_records, extended=False):
        call_connections = []
        dropped = []
        for record in func_records:
            funcname, *_ = record
            if funcname in self._suppress_from_graph:
                continue
            f = Function(funcname)
            if f not in self._inverse_call_graph:
                dropped.append(record)
                # Perhaps store as a NaN entry to database
                continue
            callers_of_f = self._inverse_call_graph[f]
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
