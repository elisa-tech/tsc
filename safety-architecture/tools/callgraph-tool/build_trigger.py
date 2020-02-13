# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import cgutils as cgu
import multiprocessing

from collections import OrderedDict
from llvm_parse import Function


class TriggerEngine(object):

    def __init__(self, trigger_map_ignore_calls, tmp_trigger_map, trigger_map_lock, trigger_calls, call_graph):
        self.trigger_map_ignore_calls = trigger_map_ignore_calls
        self.tmp_trigger_map = tmp_trigger_map
        self.trigger_map_lock = trigger_map_lock
        self.trigger_calls = trigger_calls
        self.call_graph = call_graph

    def __call__(self, args):
        trigger, entry_point = args
        print('Prepare map for ' + trigger)

        if isinstance(entry_point, list):
            for point in entry_point:
                self.prepare_flat_call_list(point)
                with self.trigger_map_lock:
                    self.tmp_trigger_map.setdefault(trigger, [])
                    self.tmp_trigger_map[trigger] += list(self.trigger_calls)
        else:
            self.prepare_flat_call_list(entry_point)
            with self.trigger_map_lock:
                self.tmp_trigger_map[trigger] = list(self.trigger_calls)

    def get_list_of_calls(self, caller, trigger_calls):
        if caller not in self.call_graph:
            return

        for callee in self.call_graph[caller]:
            if callee in self.trigger_calls or callee in self.trigger_map_ignore_calls:
                continue

            self.trigger_calls.append(callee)
            self.get_list_of_calls(callee, self.trigger_calls)

    def prepare_flat_call_list(self, syscall):
        self.trigger_calls = []

        syscall_func = Function(syscall)
        self.get_list_of_calls(syscall_func, self.trigger_calls)


def build_trigger_map(call_graph, config_file):

    cgu.debug_output_callgraph(call_graph)

    trigger_map = OrderedDict()
    trigger_map_ignore_calls = []

    conf = cgu.read_configuration_file(config_file)
    for call in conf['TriggerMapIgnore']:
        ignore_call = Function(call)
        trigger_map_ignore_calls.append(ignore_call)

    manager = multiprocessing.Manager()
    trigger_map_lock = manager.Lock()
    tmp_trigger_map = manager.dict()
    trigger_calls = manager.list()

    try:
        pool = multiprocessing.Pool(multiprocessing.cpu_count())
        engine = TriggerEngine(trigger_map_ignore_calls, tmp_trigger_map, trigger_map_lock, trigger_calls, call_graph)
        pool.map(engine, conf['Direct'].items())

    finally:  # To make sure processes are closed in the end, even if errors happen
        pool.close()
        pool.join()

    trigger_map.update(tmp_trigger_map)
    return trigger_map