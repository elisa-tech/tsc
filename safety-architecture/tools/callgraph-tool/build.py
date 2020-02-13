# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
import re
import tempfile

from enum import Enum
from llvm_parse import parse_llvm


DEF_LLVM_EXT = '.ll'
LLVM_EXT = ['.ll', '.llvm']


def valid_llvm_extensions():
    return LLVM_EXT


class BuildLogFormat(Enum):
    KERNEL_C = 'kernel_c'
    KERNEL_CLANG = 'kernel_clang'
    LL_CLANG = 'll_clang'
    CPLUSPLUS = 'c++'


def convert(build_log, build_log_format, temp_file):

    if BuildLogFormat.KERNEL_C == build_log_format or \
       BuildLogFormat.KERNEL_CLANG == build_log_format or \
       BuildLogFormat.CPLUSPLUS == build_log_format:
        print("plain log")
        return False, "."

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
                             '-Wno-free-nonheap-object']
    return unsupported_arguments


def get_unsupported_arguments_mips():
    unsupported_arguments = ['-msym32', '-fno-delete-null-pointer-checks', '-fmerge-constants',
                             '--param=allow-store-data-races=0', '-Wno-frame-address', '-Wno-format-truncation',
                             '-Wno-format-overflow', '-Wno-unused-but-set-variable', '-Werror=designated-init']
    return unsupported_arguments


def mips_modifications(cc_command):
    cc_command = cc_command.replace('-march=mips64r6', '-target mips64el')
    cc_command = cc_command.replace('-D__KERNEL__', '-D__KERNEL__ -D__linux__')
    return cc_command


class ClangCommand(object):

    def __init__(self, cc_command, arch, clang_path):
        self.command = cc_command
        self.cc_args = ''
        self.filename = ''
        self.output = None
        self.arch = arch
        self.clang_path = clang_path
        self._convert()

    def _convert(self):
        self._remove_unsupported_args()
        self._turn_of_optimizations()
        self.valid = self._extract_params()
        if self.valid:
            if self.arch == 'x86':
                self.command = "%s %s -g -fno-builtin -nobuiltininc -S -emit-llvm %s -o %s%s" % (
                    self.clang_path, self.cc_args, self.filename, self.filename, DEF_LLVM_EXT)
            elif self.arch == 'mips':
                self.command = "%s %s -g -fno-builtin -S -emit-llvm %s -o %s%s" % (
                    self.clang_path, self.cc_args, self.filename, self.filename, DEF_LLVM_EXT)

    def _turn_of_optimizations(self):
        # turn off function inlining
        self.command = self.command.replace('-O1', '-O0')
        self.command = self.command.replace('-O2', '-O0')
        self.command = self.command.replace('-O3', '-O0')

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
            logging.error("Encountered error running clang, aborting")
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
        m = re.search(r'gcc\s+(?P<cc_args>.+?)-c -o (?P<output>.+?\.o) (?P<filename>.+\.c)', self.command)
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

    def __init__(self, indirect_nodes, call_graph_lock, call_graph, args):
        self.indirect_nodes = indirect_nodes
        self.fast_build = args.fast_build
        self.call_graph_lock = call_graph_lock
        self.call_graph = call_graph
        self.build_exclude = [exclude.strip() for exclude in args.build_exclude.split(',')]
        self.arch = args.arch
        self.clang_path = args.clang
        self._select_command_type(args)

    def _select_command_type(self, args):
        self.Command = None
        if args.build_log_format == BuildLogFormat.KERNEL_C:
            self.Command = ClangKernelC
        elif args.build_log_format == BuildLogFormat.KERNEL_CLANG:
            self.Command = ClangKernel
        elif args.build_log_format == BuildLogFormat.LL_CLANG:
            self.Command = ClangLL
        elif args.build_log_format == BuildLogFormat.CPLUSPLUS:
            self.Command = ClangCpp
        else:
            logging.error("Not implemented log format: " + str(args.build_log_format))

    def __call__(self, cc_command):
        return self.build_llvms(cc_command)

    def build_llvms(self, cc_command):

        clang_command = self.Command(cc_command, self.arch, self.clang_path)
        if not clang_command.valid:
            return
        logging.info("Compile command: " + cc_command)
        # Ignore files/directories listed in build_exclude
        if clang_command.exclude_from_build(self.build_exclude):
            return
        success = True
        translation_unit = clang_command.translation_unit()
        if not self.fast_build or not os.path.isfile(translation_unit):
            success = clang_command()

        if success:
            with open(translation_unit, 'r') as stream:
                parse_llvm(stream, self.call_graph, self.call_graph_lock, self.indirect_nodes)

        logging.info("Clang command" + str(clang_command))