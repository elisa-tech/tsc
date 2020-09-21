<!--
SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)

SPDX-License-Identifier: Apache-2.0
-->

# Build Log Options

### KERNEL_C

Originally, Callgraph tool relied on the combination of the aforementioned compilers to produce static call graph of the Linux source. The basic idea is simple: collect the compilation log of the build process and rerun every command from the log with Clang in place of GCC with a small modification. Instead of producing object code that should be linked into final executable, the target output is intermediate and unoptimized LLVM code (emit-llvm option, target file extension commonly ".ll"). This files are then parsed to extract relevant information. In terminology of the Callgraph Tool we refer to this option as a build log format KERNEL_C (command line option --build_log_format kernel_c).

The first problem that manifests itself with this approach is that these commands often contain GCC specific options not supported directly by Clang compiler. Simple solution is to just remove those (along with any optimization options) before running the Clang command. As different configurations and architectures are used, the tool needs to be frequently updated to accommodate for new, yet unseen unsupported options. If the tool cannot process it after this modification, it is simply ignored in the processing pipeline.
The other problem with this approach is more subtle. As we drop down different options the output becomes a less faithful representation of the original. Also, even if the Clang introduces compatible options in newer versions, it would be hard to inspect every dropped option and remove it from the tool. 

## Clang Built Linux

Clang Built Linux is a community effort to establish Clang (llvm tools) as peer to GCC (GNU tools) when it comes to compiler of choice for building Linux kernel. The associated scripts and files can be found at https://github.com/ClangBuiltLinux/tc-build. It also contains convenient scripts for installation of the newest Clang version and target specific binutils.

In the context of the issues that occur with the implementation of KERNEL_C build log option, Clang Built Linux comes as a possible means to a solution of the mentioned problem and simplification of the tool. Two approaches were developed in utilizing the scripts:

1. collecting the buildlog from the clang compilation process in a similar fashion as existing KERNEL_C format. We refer to this approach as KERNEL_CLANG in the following text.
2. modifying the build procedure (Makefiles) to produce the target (".ll") files immediately and using the Callgraph Tool for postprocessing. We refer to this approach as LL_CLANG  in the following text.

### KERNEL_CLANG

This approach is very similar to the KERNEL_C option. The following patch needs to be applied to the tc-build/kernel/build.sh as a prerequisite:

```
--- build.sh    2020-02-12 12:49:15.110105491 +0100
+++ build.sh    2020-02-12 12:51:32.961613310 +0100
@@ -85,7 +85,7 @@
  
 # SC2191: The = here is literal. To assign by index, use ( [index]=value ) with no spaces. To keep as literal, quote it.
 # shellcheck disable=SC2191
-MAKE=( make -j"$(nproc)" -s CC=clang O=out )
+MAKE=( make -j"$(nproc)" CC=clang O=out )
  
 set -x
```
After that, the build log is simply collected with the following command (from the tc-build/kernel directory):
```
./build.sh -t X86
./scripts/gen_compile_commands.py
```

Once the compilation is complete, we can proceed with the creation of the call_graph.pickle database. By default, the build folder is called out, so we run the following command from the tc-build/kernel/linux-5.5/out directory:
```
$PATH_TO_CGTOOL/callgraph-tool.py --build compile_commands.json \
                                  --build_log_format kernel_clang \
                                  --clang $HOME/ClangBuiltLinux/tc-build/build/llvm/stage2/bin/clang-11
```
The --build_log_format command line option needs to be set to kernel_clang value. In this example Clang (version 11) was built with llvm-build.py script provided in ClangBuiltLinux. In the callgraph tool this log is parsed to find the compilation commands, rerun them with optimizations turned off and to emit the LLVM IR files. From this point on, files are further processed to extract the required function information in a same manner as with KERNEL_C option.


### LL_CLANG In comparison to the previous approaches, LL_CLANG does not require capturing the build logs but it assumes the existence of previously generated .ll (or .llvm) files in the build folder. For the Linux project it is possible to tweak script/Makefiles.build in order to produce intermediate files as a side-effect of the compilation process.  The advantage of this approach is that it can be used to build call graph for any project for which we are able to produce the IR files.  Example command to create the call graph database is:
```
$PATH_TO_CGTOOL/callgraph-tool.py --build $HOME/ClangBuiltLinux/tc-build/kernel/linux-5.5/out \
                                  --build_log_format ll_clang
```
Here, the argument to --build command line option is a directory (instead of build log file as was the case with other build log formats). The callgraph tool walks that directory recursively and picks up the files that end with .ll or .llvm. Those files are considered to be in the Clang IR format and it parses them in the same way as in previous steps. Since the intermediate files are already produced there is no need to specify Clang location for this --build_log_format option.

## Clang AST Backend

### AST\_CLANG

This option uses clang\_indexer backend in order to generate callgraph information. It assumes that Clang tools are available in the clang\_indexer directory. The tools can be downloaded simply by running clang\_download.py script in the directory. The argument to --build option is compile commands database in JSON format. This database can easily be constructed using _bear_ tool. This database needs to be in the root of analyzed source directory. See README.md in clang\_indexer directory for more details.
Example command to create the call graph database is:
```
$PATH_TO_CGTOOL/callgraph-tool.py --build $HOME/linux-stable/compile_commands.json \
                                  --build_log_format ast_clang \
                                  --clang $PATH_TO_CGTOOL/clang_indexer/clang/bin/bin/clang
```
