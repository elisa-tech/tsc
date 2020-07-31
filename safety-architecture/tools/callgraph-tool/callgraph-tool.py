#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import json
import logging
import multiprocessing
import os
import Pyro4

from build import build_call_graph, BuildLogFormat
from build_ftrace import ftrace_enrich_call_graph
from build_trigger import build_trigger_map, TriggerEngine
from db import GraphDb
from service import Service

multiprocessing.set_start_method('spawn', True)  # VS Code runtime error fix


class LoadFromSettings(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        with values as f:
            setattr(namespace, "file", f.name)
            settings = json.load(f)
            cmd = settings["args"]
            for k, v in cmd.items():
                if not k.startswith('-'):
                    k = '--' + k
                option = [k]
                if isinstance(v, list):
                    v = ','.join(v)
                if v:
                    option.append(v)
                parser.parse_args(option, namespace)
            pass


def print_env(args):
    if args.verbose:
        logging.info("Callgraph execution env")
        env = vars(args)
        keys = list(env.keys())
        keys.sort()
        for key in keys:
            logging.info("    " + key + ": " + str(env[key]))


def get_args():
    parser = argparse.ArgumentParser(description='Call graph tool', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--file', '-f', type=open, action=LoadFromSettings, help='Settings file for callgraph')
    parser.add_argument('--config', default=os.path.dirname(os.path.realpath(__file__)) + '/configuration.yaml',
                        help='Use alternative configuration file.')
    parser.add_argument('--trgdb', default=os.path.dirname(os.path.realpath(__file__)) + '/trigger_call_map.pickle',
                        help='Use alternative trigger call db file. Can be used with build and search.')
    parser.add_argument('--db', default=os.path.dirname(os.path.realpath(__file__)) + '/call_graph.pickle',
                        help='Use alternative db file. Can be used with build and search.')
    parser.add_argument('--verbose', '-vv', action='store_true',
                        help='Verbose traces.')

    # Build arguments
    build_args = parser.add_argument_group('Build arguments')
    build_args.add_argument('--build', '-b', metavar='BUILDLOG', nargs=1, help='Build call graph from build log.')
    build_args.add_argument('--build_log_format', '-blf',
                            type=BuildLogFormat, metavar='FORMAT', default=BuildLogFormat.KERNEL_C.value,
                            help='Set build log format. (default: %(default)s)\n'
                            '  ' + BuildLogFormat.KERNEL_C.value + ' = reads linux kernel build log format. '
                            '(make V=1 | tee buildlog.txt)\n'
                            '  ' + BuildLogFormat.KERNEL_CLANG.value + ' = reads ClangBuiltLinux build log format\n'
                            '  ' + BuildLogFormat.LL_CLANG.value + ' = uses existing clang .ll files\n'
                            '  ' + BuildLogFormat.AST_CLANG.value + ' = reads compile_commands.json database\n'
                            '  ' + BuildLogFormat.CPLUSPLUS.value + ' = plain build log from c++ builds')
    build_args.add_argument('--build_exclude', '-be', default='tools,scripts', help='Exclude files/directories')
    build_args.add_argument('--projroot', default='', help='Path to the source code for which we build call graph.\n'
                            'If not specified, path is deduced from build argument.')
    build_args.add_argument('--build_trigger_map', action='store_true', help='Build flat trigger map only')
    build_args.add_argument('--arch', default='x86', help='Target architecture')
    build_args.add_argument('--clang', default='clang', help='Path to clang executable')
    build_args.add_argument('--ftrace', '-ft', default=os.path.dirname(os.path.realpath(__file__)) + '/ftrace.log',
                            help='Enrich call graph using ftrace.')
    build_args.add_argument('--ftrace_enrich', '-fe', action='store_true',
                            help='Enrich current call_graph and '
                            'write enriched call_graph as <original pickle file>.ftrace')
    build_args.add_argument('--fast_build', '-fb', action='store_true',
                            help='Enable to quick build without recompiling sources (reuse existing llvm files)')

    # Search arguments
    search_args = parser.add_argument_group('Search arguments')

    search_args.add_argument('--graph', '-g', metavar='FUNCTION', help='Get call graph of a function')
    search_args.add_argument('--depth', '-d', default=-1, type=int,
                             help='Max recursion depth.  Default is 3 for call graph, 20 for path, 25 for multipath.')
    search_args.add_argument('--inverse_graph', '-i', metavar='FUNCTION', help='Get inverse call graph of a function')
    search_args.add_argument('--path', '-p', metavar='FUNCTION',
                             help='Find code path between two functions (separated with ..)')
    help_mp = 'Find possible code paths from the given function to all functions listed in configuration.yaml'
    search_args.add_argument('--multipath', '-mp', metavar='FUNCTION', help=help_mp)
    search_args.add_argument('--map_trigger', '-ms', metavar='FUNCTION',
                             help='Map function to triggers specified in configuration.yaml')
    search_args.add_argument('--view', '-v', action='store_true', help='View with graphviz')
    search_args.add_argument('--view_type', '-vt', default='svg', help='View type: pdf or png (default: pdf)')
    search_args.add_argument('--view_base_dir', '-vb', default="", help='Set base dir for the source file links')
    search_args.add_argument('--normalize_path', '-np', default=0, type=int,
                             help='On loading the DB, chop n-levels starting from the leftmost part of all '
                             'file paths')
    search_args.add_argument('--coverage_file', '-cf', default=None,
                             help='On viewing the graph, visually highlight the functions listed in the '
                             'specified file to indicate test coverage')

    # Search optimization arguments
    search_op_args = parser.add_argument_group('Search optimization arguments')
    search_op_args.add_argument('--service', '-s', action='store_true', help='Start or restart service')
    search_op_args.add_argument('--client', '-c', action='store_true',
                                help='Connect to service and forward args to it')
    search_op_args.add_argument('--no_indirect', '-ni', action='store_true', help='Ignore indirect paths')
    search_op_args.add_argument('--batch_graph', '-bg',
                                help='File with Python list of function calls (in pickle format)')
    search_op_args.add_argument('--batch_inverse_graph', '-big',
                                help='File with Python list of function calls (in pickle format)')

    return parser.parse_args()


def main():
    args = get_args()

    log_format = '\033[30;1m%(levelname)s:\033[0m %(message)s'
    log_level = logging.INFO

    if args.verbose:
        log_level = logging.DEBUG

    logging.basicConfig(format=log_format, level=log_level)

    if args.coverage_file and not os.path.isfile(args.coverage_file):
        logging.error("File not found or no permissions: \"%s\"" % args.coverage_file)
        exit(1)

    print_env(args)

    call_graph = GraphDb(args.db)
    trigger_map = GraphDb(args.trgdb)

    if args.build and (os.path.isfile(args.build[0]) or os.path.isdir(args.build[0])):
        build_call_graph(args, call_graph)
        call_graph.save()

    if args.ftrace_enrich and os.path.isfile(args.ftrace):
        call_graph.open()
        ftrace_enrich_call_graph(args.ftrace, call_graph)
        ftrace_db = GraphDb(args.db + '.ftrace')
        ftrace_db.update(call_graph)
        ftrace_db.save()

    if args.build_trigger_map:
        call_graph.open()
        trigger_map.update(build_trigger_map(call_graph, args.config))
        trigger_map.save()

    if args.client:
        try:
            existing_service = open(Service.SERVICE_FILE, 'r').read()
            service = Pyro4.Proxy(existing_service)
            # Have to be print as it have to be unformatted for internal functionality
            print(service.serve(vars(args)))
        except IOError:
            logging.error("Service is not running, run %s -s" % __file__)
            exit(1)
    else:
        if os.path.isfile(args.trgdb):
            trigger_map.open()

        call_graph.open()
        call_graph.normalize_paths(args.normalize_path)

        if args.service:
            if os.path.isfile(Service.SERVICE_FILE):
                logging.error('Service already running or there is a stale file %s' % Service.SERVICE_FILE)
                return

            daemon = Pyro4.Daemon()
            uri = daemon.register(Service(call_graph, trigger_map))
            logging.info('Started service %s' % uri)

            with open(Service.SERVICE_FILE, "w") as stream:
                stream.write(str(uri))

            daemon.requestLoop()

            os.remove(Service.SERVICE_FILE)
        else:
            service = Service(call_graph, trigger_map)
            service.parse(vars(args))


if __name__ == "__main__":
    main()
