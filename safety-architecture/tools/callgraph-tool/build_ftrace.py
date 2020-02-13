# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import logging
import re

from llvm_parse import Function


def ftrace_function_graph_get_callees(caller_name, file, call_graph):
    logging.debug('Getting callees for ' + caller_name)

    caller = Function(caller_name)
    if caller not in call_graph:
        call_graph[caller] = []

    # ext4_mark_iloc_dirty() {
    re_call = re.compile(r'.+\|\s+(?P<name>.*)\(\)\s{')
    # map_id_up();
    re_callee = re.compile(r'.+\|\s+(?P<name>.*)\(\);')

    for line in file:
        if '}' in line:
            logging.debug('End block')
            break

        m = re_call.search(line)
        if m:
            callee_name = m.group('name').split('.')[0]
            ftrace_function_graph_get_callees(callee_name, file, call_graph)
        else:
            m = re_callee.search(line)
            if m:
                callee_name = m.group('name').split('.')[0]
            else:
                logging.debug('Ignoring line: ' + line)
                continue

        logging.debug('Found callee ' + callee_name)
        callee = Function(callee_name)
        if callee not in call_graph[caller]:
            logging.debug('Adding callee ' + callee_name + ' to ' + ' caller ' + caller_name)
            call_graph[caller].append(callee)


def ftrace_function_graph_enrich_call_graph(file, call_graph):
    # ext4_mark_iloc_dirty() {
    re_call = re.compile(r'.+\|\s+(?P<name>.*)\(\)\s{')

    for line in file:
        m = re_call.search(line)
        if m:
            caller_name = m.group('name').split('.')[0]
            logging.debug('Found caller: ' + caller_name)
            ftrace_function_graph_get_callees(caller_name, file, call_graph)
        else:
            logging.debug('Ignoring line: ' + line)


def ftrace_function_enrich_call_graph(file, call_graph):
    # run_syscall_tes-2431  [003] .......  1976.699558: dput <-path_put
    re_call = re.compile(r'.+\:\s(?P<callee>.*)\s\<\-(?P<caller>.*)')

    for line in file:
        m = re_call.search(line)
        if m:
            # run_syscall_tes-2431  [003] d..h1..  1976.700154:
            # cgroup_rstat_updated <-cgroup_base_stat_cputime_account_end.isra.7
            caller = Function(m.group('caller').split('.')[0])
            # run_syscall_tes-2431  [003] d..h1..  1976.700153:
            # cgroup_base_stat_cputime_account_end.isra.7 <-account_user_time
            callee = Function(m.group('callee').split('.')[0])
            logging.debug('Found caller: ' + caller.name + ' callee: ' + callee.name)

            if caller not in call_graph:
                call_graph[caller] = []
            if callee not in call_graph[caller]:
                logging.debug('Adding callee ' + callee.name + ' to ' + ' caller ' + caller.name)
                call_graph[caller].append(callee)
        else:
            logging.debug('Ignoring line: ' + line)


def ftrace_enrich_call_graph(ftrace_file, call_graph):
    logging.info('Enrich call_graph using ftrace file ' + ftrace_file)

    with open(ftrace_file) as file:
        for line in file:
            if line == '# tracer: function_graph\n':
                logging.info(ftrace_file + ' seems to be \"function_graph\" type ftrace')
                logging.info('Please note that there are some issues with this type, suggest using \"function\" type')
                return ftrace_function_graph_enrich_call_graph(file, call_graph)
            elif line == '# tracer: function\n':
                logging.info(ftrace_file + ' seems to be \"function\" type ftrace')
                return ftrace_function_enrich_call_graph(file, call_graph)