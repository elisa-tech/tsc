# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import multiprocessing
import os
import re
import sys
import tempfile

from cgutils import read_configuration_file
from enum import Enum
from llvm_parse import parse_llvm, Function

DEF_LLVM_EXT = '.ll'
LLVM_EXT = ['.ll', '.llvm']


def valid_llvm_extensions():
    return LLVM_EXT


def get_build_root(buildpath):
    path = os.path.expanduser(buildpath)
    if not os.path.isdir(path):
        path = os.path.dirname(path)
    return os.path.abspath(os.path.normpath(path))


class BuildLogFormat(Enum):
    KERNEL_C = 'kernel_c'
    KERNEL_CLANG = 'kernel_clang'
    LL_CLANG = 'll_clang'
    AST_CLANG = 'ast_clang'
    CPLUSPLUS = 'c++'


def build_indirect_nodes(config, call_graph):
    indirect_nodes = []

    if 'Indirect' in config:
        for operation, callees in config['Indirect'].items():
            caller = Function(operation, indirect=True)
            if caller not in call_graph:
                call_graph[caller] = []
                indirect_nodes.append(operation)

    return indirect_nodes


def get_missing_nodes(config, call_graph, dso_declare):
    # only add the indirect edges for nodes that were found in the source
    if 'Indirect' in config:
        for operation, callees in config['Indirect'].items():
            caller = Function(operation, indirect=True)
            for callee in callees:
                callee = Function(callee)
                if callee in call_graph:
                    call_graph[caller].append(callee)

    for func in dso_declare:
        if func not in call_graph:
            call_graph[func] = []

    missing_nodes = []
    for node_out in call_graph:
        for node_in in call_graph[node_out]:
            if node_in not in call_graph.keys() and node_in not in missing_nodes:
                logging.info("Missing node: %s found in the edge from %s" % (node_in.name, node_out.name))
                missing_nodes.append(node_in)
    nodes = [Function(node.name, args=node.args) for node in missing_nodes]
    return nodes


def clang_indexer_build(args, call_graph):
    CLANG_INDEXER_PATH = os.path.dirname(os.path.abspath(__file__)) + '/clang_indexer/'
    sys.path.append(CLANG_INDEXER_PATH)

    import utils
    from clang_find_calls import find_function_calls
    from convert_db import calls_to_db

    cg_parser = utils.setup_callgraph_parser(args.build[0], args.build_exclude)
    find_function_calls(cg_parser)
    calls_file = cg_parser.parse_args().out
    calls_to_db(calls_file, call_graph)


def build_call_graph(args, call_graph):
    args.projroot = args.projroot if args.projroot else get_build_root(args.build[0])
    args.build[0] = convert_build_file(args.build[0], args.build_log_format)

    if args.build_log_format == BuildLogFormat.AST_CLANG:
        clang_indexer_build(args, call_graph)
        return

    config = read_configuration_file(args.config)
    indirect_nodes = build_indirect_nodes(config, call_graph)

    manager = multiprocessing.Manager()
    call_graph_lock = manager.Lock()
    tmp_call_graph = manager.dict()
    tmp_dso_declare = manager.list()

    with open(args.build[0], "r") as ins:
        try:
            pool = multiprocessing.Pool(multiprocessing.cpu_count())
            engine = Engine(indirect_nodes, call_graph_lock, tmp_call_graph, tmp_dso_declare, args)
            pool.map(engine, ins)
        finally:  # To make sure processes are closed in the end, even if errors happen
            pool.close()
            pool.join()

    call_graph.update(tmp_call_graph)
    dso_declare = set(tmp_dso_declare)
    missing_nodes = get_missing_nodes(config, call_graph, dso_declare)
    for node in missing_nodes:
        call_graph[node] = []


def convert(build_log, build_log_format, temp_file):

    if BuildLogFormat.KERNEL_C == build_log_format or \
       BuildLogFormat.KERNEL_CLANG == build_log_format or \
       BuildLogFormat.CPLUSPLUS == build_log_format or \
       BuildLogFormat.AST_CLANG == build_log_format:
        logging.info("plain log")
        return False, "."

    if BuildLogFormat.LL_CLANG == build_log_format:
        # scan build_log dir
        ll_files = []
        valid_ext = valid_llvm_extensions()
        for root, _, fnames in os.walk(build_log):
            for fname in fnames:
                for ext in valid_ext:
                    if fname.endswith(ext):
                        ll_files.append(os.path.join(root, fname))
                        break
        temp_file.write('\n'.join(ll_files))
        return True, '.'

    raise ValueError("Not implemented log format: " + str(build_log_format))


def convert_build_file(build_file_url, build_log_format):

    logging.info("Build file format: " + str(build_log_format))
    build_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
    needed_conversion, directory = convert(build_file_url, build_log_format, build_file)
    if needed_conversion:
        logging.info("Build log file needed conversion.")
        os.chdir(directory)
        build_file_url = build_file.name
        build_file.flush()
    return build_file_url


def get_unsupported_arguments_x86():
    unsupported_arguments = ['-mno-fp-ret-in-387', '-mpreferred-stack-boundary=3', '-mpreferred-stack-boundary=2',
                             '-mskip-rax-setup', '-fno-var-tracking-assignments', '-mrecord-mcount',
                             '-fconserve-stack', '-fno-code-hoisting', '-fsched-pressure',
                             '-mindirect-branch=thunk-extern', '-mindirect-branch=thunk-inline',
                             '-mindirect-branch-register',
                             '-fno-canonical-system-headers', '-Wunused-but-set-parameter',
                             '-Wno-free-nonheap-object', '-fasan-shadow-offset=0xdffffc0000000000',
                             '-fno-conserve-stack']
    return unsupported_arguments


def get_unsupported_arguments_mips():
    unsupported_arguments = ['-msym32', '-fno-delete-null-pointer-checks', '-fmerge-constants',
                             '--param=allow-store-data-races=0', '-Wno-frame-address', '-Wno-format-truncation',
                             '-Wno-format-overflow', '-Wno-unused-but-set-variable', '-Werror=designated-init',
                             '-femit-struct-debug-baseonly', '-Wimplicit-fallthrough']
    return unsupported_arguments


def mips_modifications(cc_command):
    cc_command = cc_command.replace('-march=mips64r6', '-target mips64el')
    cc_command = cc_command.replace('-D__KERNEL__', '-D__KERNEL__ -D__linux__')
    return cc_command


class ClangCommand(object):

    def __init__(self, cc_command, arch, clang_path, isystem='auto'):
        self.command = cc_command
        self.cc_args = ''
        self.filename = ''
        self.output = None
        self.arch = arch
        self.clang_path = clang_path
        self.isystem = isystem
        self._convert()

    def _builtin(self):
        builtin = ''
        if self.isystem == 'auto':
            builtin = ''
        else:
            builtin = '-fno-builtin'
            if self.arch == 'x86':
                builtin += ' -nobuiltininc'
        return builtin

    def _convert(self):
        self._remove_unsupported_args()
        # self._turn_of_optimizations()
        self.valid = self._extract_params()
        if self.valid:
            builtin = self._builtin()
            self.command = "%s %s -g %s -S -emit-llvm %s -o %s%s" % (
                    self.clang_path, self.cc_args, builtin, self.filename, self.filename, DEF_LLVM_EXT)

    def _turn_of_optimizations(self):
        # turn off function inlining
        optim_flags = ['-O1', '-O2', '-O3', '-Ofast', '-Os', '-Oz', '-Og', '-O4']
        for of in optim_flags:
            self.command = self.command.replace(of, '')

    def _remove_unsupported_args(self):
        unsupported_arguments = get_unsupported_arguments_x86()
        for arg in unsupported_arguments:
            self.command = self.command.replace(arg, '')
        if self.arch == 'mips':
            unsupported_arguments = get_unsupported_arguments_mips()
            for arg in unsupported_arguments:
                self.command = self.command.replace(arg, '')
            self.command = mips_modifications(self.command)

    def translation_unit(self):
        return "%s%s" % (self.filename, DEF_LLVM_EXT)

    def __call__(self):
        if os.system(self.command) != 0:
            logging.error("Encountered error running clang on %s, aborting", self.translation_unit())
            return False
        return True

    def __str__(self):
        return self.command

    def _extract_params(self):
        return None


class ClangLL(ClangCommand):
    def __call__(self):
        return os.path.isfile(self.filename)

    def __str(self):
        return self.filename

    def translation_unit(self):
        return self.filename

    def _extract_params(self):
        return True

    def exclude_from_build(self, ex_iterable):
        return any(exclude in self.filename for exclude in ex_iterable)

    def _convert(self):
        self.valid = True
        self.filename = self.command.strip()


class ClangKernelC(ClangCommand):
    def _extract_params(self):
        m = re.search(r'gcc\S*\s+(?P<cc_args>.+?)-c -o (?P<output>.+?\.o) (?P<filename>.+\.c)', self.command)
        if m:
            self.cc_args = m.group('cc_args')
            self.output = m.group('output')
            self.filename = m.group('filename')
            return True
        return False

    def exclude_from_build(self, ex_iterable):
        return any(exclude in self.output for exclude in ex_iterable)


class ClangKernel(ClangCommand):
    def _extract_params(self):
        m = re.search(r'clang\S*\s+(?P<cc_args>.+?)-c -o (?P<output>.+?\.o) (?P<filename>.+\.c)', self.command)
        if m:
            self.cc_args = m.group('cc_args')
            self.output = m.group('output')
            self.filename = m.group('filename')
            return True
        return False

    def _convert(self):
        # self._turn_of_optimizations()
        self.valid = self._extract_params()
        if self.valid:
            builtin = self._builtin()
            self.command = "%s %s -g %s -S -emit-llvm %s -o %s%s" % (
                    self.clang_path, self.cc_args, builtin, self.filename, self.filename, DEF_LLVM_EXT)

    def exclude_from_build(self, ex_iterable):
        return any(exclude in self.output for exclude in ex_iterable)


class ClangCpp(ClangCommand):
    def _extract_params(self):
        m = re.search(r'.*c\+\+\s+(?P<cc_args>.+?)\s-c\s(?P<filename>.+\.(cc|cpp))', self.command)
        if m:
            self.cc_args = m.group('cc_args')
            self.filename = m.group('filename')
            return True
        return False

    def exclude_from_build(self, ex_iterable):
        return any(exclude in self.filename for exclude in ex_iterable)


class Engine(object):

    def __init__(self, indirect_nodes, call_graph_lock, call_graph, declare_dso, args):
        self.indirect_nodes = indirect_nodes
        self.fast_build = args.fast_build
        self.call_graph_lock = call_graph_lock
        self.call_graph = call_graph
        self.build_exclude = [exclude.strip() for exclude in args.build_exclude.split(',')]
        self.arch = args.arch
        self.clang_path = args.clang
        self.declare_dso = declare_dso
        self.isystem = args.isystem
        self._select_command_type(args)

    def _select_command_type(self, args):
        self.Command = None
        if args.build_log_format == BuildLogFormat.KERNEL_C:
            self.Command = ClangKernelC
        elif args.build_log_format == BuildLogFormat.KERNEL_CLANG:
            self.Command = ClangKernel
        elif args.build_log_format == BuildLogFormat.LL_CLANG:
            self.Command = ClangLL
            self.build_exclude = [args.projroot + '/' +
                                  exclude for exclude in self.build_exclude]
        elif args.build_log_format == BuildLogFormat.CPLUSPLUS:
            self.Command = ClangCpp
        else:
            logging.error("Not implemented log format: " + str(args.build_log_format))

    def __call__(self, cc_command):
        return self.build_llvms(cc_command)

    def build_llvms(self, cc_command):
        clang_command = self.Command(cc_command, self.arch, self.clang_path, self.isystem)
        if not clang_command.valid:
            return
        logging.debug("Compile command: " + cc_command)
        # Ignore files/directories listed in build_exclude
        if clang_command.exclude_from_build(self.build_exclude):
            return
        success = True
        translation_unit = clang_command.translation_unit()
        if not self.fast_build or not os.path.isfile(translation_unit):
            success = clang_command()

        if success:
            with open(translation_unit, 'r') as stream:
                parse_llvm(stream, self.call_graph, self.call_graph_lock, self.indirect_nodes, self.declare_dso)

        logging.debug("Clang command: " + str(clang_command))
