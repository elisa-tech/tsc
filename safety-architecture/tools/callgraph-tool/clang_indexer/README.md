<!--
SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)

SPDX-License-Identifier: Apache-2.0
-->

# Clang Indexer
This repository is a collection of scripts for generating function call database using libclang via python bindings.

## Getting Started
Install following requirements:
```
$ sudo apt install python3 python3-pip
```

In addition, the scripts rely on a number of python packages specified in requirements.txt. You can install the required packages with:
```
$ pip3 install -r requirements.txt
```

## Building Compilation Database
Scripts require JSON compilation database to provide the information for how the target compilation units should be processed. For Makefile-based projects, such as the linux kernel, we recommend generating the compilation database by using [bear](https://github.com/rizsotto/Bear). Bear is available via e.g. Ubuntu package manager:
```
$ sudo apt install bear
```

As an example, the below commands generate a compilation database for stable-linux v5.6 'tinyconfig':
```
$ cd ~
$ git clone git://git.kernel.org/pub/scm/linux/kernel/git/stable/linux-stable.git
$ cd linux-stable
$ git checkout linux-5.6.y
$ make tinyconfig
$ bear make -j8
```

Bear intercepts the build commands and generates a compilation database 'compile_commands.json'.

## Building Database of Function Calls
[clang_find_calls.py](clang_find_calls.py) builds CSV database that lists both direct and indirect function calls based on user-specified compilation database.

As an example, the below command generates call database for the v5.6 tinyconfig, for which we generated the compilation database in the previous section.
```
$ ./clang_find_calls.py --compdb ~/linux-stable/compile_commands.json --isystem none
```

By default, on the first invocation [clang_find_calls.py](clang_find_calls.py) downloads the latest clang release from https://github.com/llvm/llvm-project/releases and then uses the downloaded libclang to parse the AST tree.

When generating the call database for kernel builds or files, you should include the `--isystem none`  argument, so to not include the system headers into the compilation commands.

The above command dumps all direct and indirect function calls for the whole compilation database. To generate call database for one translation unit (file), use the argument `--file`. For example, to generate call database for compilation unit `arch/x86/mm/init.c`:
```
$ ./clang_find_calls.py --compdb ~/linux-stable/compile_commands.json --file ~/linux-stable/arch/x86/mm/init.c --isystem none
```

The tool attempts to resolve the indirect calls by parsing the AST tree. The results are not perfect, and in some cases resolving the indirect call fails. Indeed, there are many types of indirect calls that the tool does not support at the moment. As an example, function call via function pointer array or function call via function pointer received as a return statement from another function call will fail. See [tests](tests/resources) for simplified example C test programs that are used in testing. These examples also document the kind of indirect calls [clang_find_calls.py](clang_find_calls.py) should be able to resolve. See [Makefile](Makefile) target `test` for details on running the tool against these test programs, or against your own C programs.


## Helper Tools
Below tools might help in testing and debugging, as well as help understand the AST trees. Usage and command line arguments are similar in all tools.

#### Dumping AST database
[clang_index_dump.py](clang_index_dump.py) dumps the whole AST database in CSV format. The output is extremely wordy, containing all AST nodes from all translation units in the specified compilation database. To dump the AST database from one translation unit only, use the `--file` argument.

As an example, the below command dumps the AST database from compilation unit `arch/x86/mm/init.c`:
```
$ ./clang-indexer.py --compdb ~/linux-stable/compile_commands.json --file ~/linux-stable/arch/x86/mm/init.c --isystem none
```

#### AST Treeview
[clang_ast_treeview.py](clang_ast_treeview.py) dumps the AST database using asciitree, similarly to clang ast-view. The output is an ascii tree that shows the parent-child relationship between the tree nodes.

As an example, the below command dumps the AST database from compilation unit `~/hello/hello.c`, excluding the bloat from system include headers (see argument `--regex`):
```
./clang_ast_treeview.py --compdb ~/hello/compile_commands.json --file ~/hello/hello.c --regex '(^((?!include).)*$)'
```

