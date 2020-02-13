# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import logging
import subprocess
import yaml

from collections import OrderedDict


def debug_output_callgraph(call_graph):
    for caller in call_graph:
        for callee in call_graph[caller]:
            logging.debug(caller.name + ' (' + caller.source_file + ':' + str(caller.line_numbers) + ') calling ' +
                          callee.name + ' in ' + str(callee.source_file) + ' at lines ' + str(callee.line_numbers))


def ansi_highlight(text, color='37;1'):
    return "\033[%sm%s\033[0m" % (color, text)


def demangle(name):
    cmd = 'c++filt ' + name
    pipe = subprocess.run(args=cmd, stdout=subprocess.PIPE, shell=True, encoding='utf-8')
    output = str(pipe.stdout).strip()

    return output


def exec_cmd_with_stdin(cmd, input):
    pipe = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, encoding='utf-8')
    stdout, stderr = pipe.communicate(input=input)
    if pipe.returncode != 0:
        raise ValueError(stderr)
    return stdout


def ordered_load(stream, Loader=yaml.Loader, object_pairs_hook=OrderedDict):
    '''Like yaml.safe_load, but preserves order of keys in dictionaries'''
    class OrderedLoader(Loader):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))

    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    return yaml.load(stream, OrderedLoader)


def read_configuration_file(file_name):
    with open(file_name, 'r') as stream:
        obj = ordered_load(stream)
        return obj