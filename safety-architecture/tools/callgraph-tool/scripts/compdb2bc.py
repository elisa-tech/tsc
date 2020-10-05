#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import re
import argparse
import logging
import multiprocessing
import utils

###############################################################################

_LOGGER = logging.getLogger(utils.LOGGER_NAME)
_FILEDIR = os.path.dirname(os.path.realpath(__file__))

###############################################################################


def set_clang_bindings_and_lib(bindings, libclang):
    if not bindings:
        raise ValueError("Invalid bindings file: %s" % bindings)
    _LOGGER.debug("Setting python bindings: %s" % bindings)

    # Raise ImortError if clang.cindex module was loaded from somewhere else
    # prior to calling this function
    if 'clang.cindex' in sys.modules:
        raise ImportError(
            "Module 'clang.cindex' has been loaded outside compdb2bc.py")

    # Import the python bindings to global scope
    cindex_path = os.path.join(os.path.dirname(bindings), '..')
    sys.path.insert(0, cindex_path)
    import clang.cindex as cindex
    global cl
    cl = cindex

    # Set libclang library file
    if not libclang:
        raise ValueError("Invalid libclang file: %s" % libclang)
    _LOGGER.debug("Setting libclang: %s" % libclang)
    cl.Config.set_compatibility_check(True)
    cl.Config.set_library_file(libclang)


################################################################################


class BitcodeCompiler():
    def __init__(self, compdb, srcfile=None, append_arg="", clang=""):
        self.compdbpath = os.path.dirname(os.path.abspath(compdb))
        self.append_args = list(append_arg.split(" "))
        self.append_args = [x for x in self.append_args if x]
        self.srcfile = srcfile
        self.clang_bin = clang
        _LOGGER.debug("Using python bindings: %s" % str(cl))

    def generate_bitcode(self):
        # Paths in compile_commands.json are relative so we need to chdir
        cwd = os.getcwd()
        os.chdir(self.compdbpath)
        self._compile()
        # Change working directory back to where it was
        os.chdir(cwd)

    def _compile(self):
        compdb = cl.CompilationDatabase.fromDirectory(self.compdbpath)
        if self.srcfile:
            commands = compdb.getCompileCommands(self.srcfile)
        else:
            commands = compdb.getAllCompileCommands()

        cpu_count = multiprocessing.cpu_count()
        _LOGGER.debug("Starting compile jobs (processes=%s)" % cpu_count)

        with multiprocessing.Pool(processes=cpu_count) as pool:
            results = []
            for cc in commands:
                if cc.filename.lower().endswith('.s'):
                    _LOGGER.warning(
                        "Ignoring assembly source file: %s" % cc.filename)
                    continue
                # Arguments from compdb
                arglist = [arg for arg in cc.arguments]
                # Replace first argument (compiler) with clang
                arglist.pop(0)
                arglist.insert(0, self.clang_bin)
                # Add arguments: -c -emit-llvm
                arglist.insert(1, "-c")
                arglist.insert(2, "-emit-llvm")
                # Add ".bc" postfix to the original output filename
                for i, value in enumerate(arglist):
                    if value == "-o" and len(arglist) > i:
                        if not arglist[i + 1].endswith(".bc"):
                            arglist[i + 1] = "%s.bc" % arglist[i + 1]
                # Additional arguments from command line
                arglist = arglist + self.append_args
                result = pool.apply_async(utils.exec_cmd, [arglist])
                results.append(result)

            # Wait for all the processes to exit
            for result in results:
                result.wait()

        _LOGGER.debug("All compile jobs completed")


################################################################################


def command_line_args(scriptdir):
    parser = argparse.ArgumentParser()

    desc = \
        "Script generates bitcode files given a compilation database "\
        "COMPDB. It writes the output bitcode files to where the original "\
        "object files were written. Option --append_arg allows specifying "\
        "additional build arguments, or to overwrite original build "\
        "arguments. Notice the script only builds individual source "\
        "files to bitcode without linking them."

    epil = "Example: ./%s --compdb ~/linux-stable/compile_commands.json" % \
        os.path.basename(__file__)
    parser.description = desc
    parser.epilog = epil

    help = "File path to target file (to make the script build "\
        "only the specified translation unit (file) instead "\
        "of all translation units in the COMPDB"
    parser.add_argument('--file', help=help, default=None)

    help = "Additional string to append to compiler args"
    parser.add_argument('--append_arg', nargs='?', help=help, default="")

    required_named = parser.add_argument_group('required named arguments')
    help = "File path to compilation database (generated e.g. with bear)"
    required_named.add_argument('--compdb', help=help, required=True)

    help = "File path to libclang dynamic library (libclang.so)"
    path = os.path.join(scriptdir, '/usr/lib/llvm-10/lib/libclang.so')
    parser.add_argument('--libclang', help=help, default=path)

    help = "File path to libclang python bindings (cindex.py)"
    path = os.path.join(
        scriptdir, '/usr/lib/python3/dist-packages/clang/cindex.py')
    parser.add_argument('--cindexpy', help=help, default=path)

    help = "File path to clang binary"
    path = os.path.join(scriptdir, '/usr/lib/llvm-10/bin/clang')
    parser.add_argument('--clang', help=help, default=path)

    help = "Set the verbose level (defaults to --v=1)"
    parser.add_argument('--verbose', help=help, type=int, default=1)

    return parser.parse_args()

################################################################################


def compdb2bc(args):
    set_clang_bindings_and_lib(args.cindexpy, args.libclang)
    compiler = BitcodeCompiler(
        compdb=args.compdb,
        srcfile=args.file,
        append_arg=args.append_arg,
        clang=args.clang,
    )
    compiler.generate_bitcode()


if __name__ == "__main__":
    args = command_line_args(_FILEDIR)
    utils.setup_logging(verbosity=args.verbose)
    utils.exit_unless_accessible(args.compdb)
    utils.exit_unless_accessible(args.file)
    compdb2bc(args)

################################################################################
