# How to visualize and query the callgraph data

This page documents instructions and examples on how to visualize and query the callgraph database.  

Table of Contents
=================

* [Setup](#setup)
* [Building kernel bitcode files with compiler optimizations disabled](#building-kernel-bitcode-files-with-compiler-optimizations-disabled)
    * [Patch compiler_attributes.h](#patch-compiler_attributesh)
    * [Build compilation database](#build-compilation-database)
    * [Build bitcode files](#build-bitcode-files)
    * [Run the crix-callgraph tool](#run-the-crix-callgraph-tool)
* [How to use the callgraph database](#how-to-use-the-callgraph-database)
    * [Example: functions called by sock_recvmsg](#example-functions-called-by-sock_recvmsg)
    * [Example: functions calling sock_recvmsg](#example-functions-calling-sock_recvmsg)
    * [Example: visualizing syscalls calling sock_recvmsg](#example-visualizing-syscalls-calling-sock_recvmsg)

## Setup
To begin, make sure you have gone through the following the setup instructions from the main [README](../README.md):
- [Getting started](../README.md#getting-started)
- [Build the crix-callgraph tool](../README.md#build-the-crix-callgraph-tool)

Additionally, in these instructions, we are going to use [bear](https://github.com/rizsotto/Bear) to generate the compilation database. Bear is available e.g. via Ubuntu package manager:
```
sudo apt install bear
```
The below instructions also assume you have setup the `$KERNEL` and `$CG_DIR` variables to contain the path to the target kernel tree and the callgraph-tool directories as explained in the main [README](../README.md).

## Building kernel bitcode files with compiler optimizations disabled
Compiler optimizations and function inlining impact the callgraph output: this is by design and generally desired.

In these instructions, however, we are going to use kernel bitcode files build with compiler optimizations disabled i.e. `-O0`. In addition, we are going to re-define the `__always_inline` macro to not force function inlines for any functions. The main reason for disabling both  the compiler optimizations and function inlining is to make the visualized function callgraphs more faithfully represent the C-source code, in order to make the call chains easier to follow from the source code.

#### Patch compiler_attributes.h
We need to edit the file include/linux/compiler_attributes.h macro `__always_inline` definition to disable forced function inlines as follows:
```
/* Around line 70: comment out
 * #define __always_inline                 inline __attribute__((__always_inline__))
 */

/* Re-define: */
#define __always_inline	inline
```
#### Build compilation database
```
cd $KERNEL

# Add correct version of clang to PATH
source $CG_DIR/env.sh

# Clean
make clean && make mrproper
# Clean possibly earlier generated bitcode files manually
find . -type f -name "*.bc" -and ! -name "timeconst.bc" -delete

# Generate defconfig
make defconfig CC=clang

# Set any missing configuration options to default without prompting
make olddefconfig CC=clang

# Build the kernel with clang, generating compile_commands.json
bear make CC=clang HOSTCC=clang -j$(nproc)
```
#### Build bitcode files
```
# Run compdb2bc.py to compile .bc files, notice the --append_arg='-g -O0':
# we want to compile with debug info and without compiler optimizations.
# Linking the kernel binary fails with -O0, but we are not linking
# the binary, only compiling individual c-files to bitcode:

cd $CG_DIR
./scripts/compdb2bc.py --compdb $KERNEL/compile_commands.json --v=2 \
--append_arg='-g -O0' > compdb2bc.log 2>&1

# List all generated bitcode files
cd $KERNEL
find ~+ -type f -name "*.bc" -and ! -name "timeconst.bc" > bitcodefiles.txt
``` 
#### Run the crix-callgraph tool
```
cd $CG_DIR

# To generate a callgraph database using the .bc files listed in
# $KERNEL/bitcodefiles.txt as input, run crix-callgraph as follows
# (the @-notation that allows specifying a list of input .bc files)

./build/lib/crix-callgraph @$KERNEL/bitcodefiles.txt -o callgraph_O0.csv

# Now, you can find the callgraph database in `callgraph_O0.csv`
```

## How to use the callgraph database

#### Example: functions called by sock_recvmsg
To visualize the functions called by `sock_recvmsg` run the following command:
```
# --csv callgraph_O0.csv: use the file callgraph_O0.csv as callgraph database file
# --function sock_recvmsg: start from the target function 'sock_recvmsg' (exact match) 
# --depth 1: include the first-level function calls from 'sock_recvmsg'
# --edge_labels: add caller source line numbers to the graph
# --out sock_recvmsg_d1.png: output png-image with filename 'sock_recvmsg_d1.png'

cd $CG_DIR
./scripts/query_callgraph.py --csv callgraph_O0.csv --function sock_recvmsg --depth 1 \
--edge_labels --out sock_recvmsg_d1.png
```
Output:

<img src=sock_recvmsg_d1.png>
<br /><br />

The output graph shows that function `sock_recvmsg` is defined in file net/socket.c on line 900. It calls three functions: `msg_data_left`, `security_socket_recvmsg`, and `sock_recvmsg_nosec`. The calls to these functions takes place from net/socket.c on lines 902, 902, and 904. The three called functions are defined in include/linux/socket.h:157, security/security.c:2127, and net/socket.c:883 respectively. Notice the node labels refer each function's definition, not declaration location.

Increasing the `--depth` argument makes the query_callgraph.py walk the call chains deeper. For instance, with `--depth 2`, the output becomes:

<img src=sock_recvmsg_d2.png>
<br /><br />

The output now shows one function call deeper into each function call chain starting from `sock_recvmsg`.

The dashed lines indicate indirect function calls: these are cases where the function call happens through a function pointer. Indirect function call targets are resolved by crix-callgraph using the type-analysis based on [crix](https://github.com/umnsec/crix) program.

#### Example: functions calling sock_recvmsg
To visualize the functions that can possibly call `sock_recvmsg` run the following command:
```
# --csv callgraph_O0.csv: use the file callgraph_O0.csv as callgraph database file
# --function sock_recvmsg: start from the target function 'sock_recvmsg' (exact match) 
# --depth 1: include the first-level function calls from 'sock_recvmsg'
# --edge_labels: add caller source line numbers to the graph
# --out sock_recvmsg_d1_inverse.png: output png-image with filename 'sock_recvmsg_d1.png'
# --inverse: instead of finding the functions called by sock_recvmsg, 
#            search functions that call sock_recvmsg

cd $CG_DIR
./scripts/query_callgraph.py --csv callgraph_O0.csv --function sock_recvmsg --depth 1 \
--edge_labels --out sock_recvmsg_d1_inverse.png --inverse
```
Output:

<img src=sock_recvmsg_d1_inverse.png>
<br /><br />

The output graph now shows that there are ten functions that can call `sock_recvmsg`: for instance, the function `io_recv`, which is defined in fs/io_uring.c on line 3906, calls `sock_recvmsg` on line 3947. The dashed line means that there is one function, namely `security_socket_sendmsg`, where `sock_recvmsg` is possibly called through a function pointer.

Again, increasing the `--depth` argument makes the query_callgraph.py walk the call chains deeper. For instance, with `--inverse` and `--depth 2`, the output becomes:

<img src=sock_recvmsg_d2_inverse.png>
<br /><br />

#### Example: visualizing syscalls calling sock_recvmsg
To visualize system calls that can possibly call `sock_recvmsg` run the following command:

```
# --csv callgraph_O0.csv: use the file callgraph_O0.csv as callgraph database file
# --function sock_recvmsg: start from the target function 'sock_recvmsg' (exact match) 
# --depth 4: include, at most, four levels of function calls from 'sock_recvmsg'
# --until_function '__x64_sys': stop drawing the call chain if the function name
                                matches regular expression '__x64_sys'
# --colorize: colorize graph node if function name matches the given regular expression
# --merge_edges: if a function calls another function on many different lines,
                 merge the calls and show only one line between the nodes.
# --out sock_recvmsg_syscalls.png: output png-image with the given filename
# --inverse: instead of finding the functions called by sock_recvmsg, 
#            search functions that call sock_recvmsg

cd $CG_DIR
./scripts/query_callgraph.py --csv callgraph_O0.csv --function sock_recvmsg --depth 4 \
--until_function '__x64_sys' --colorize '__x64_sys' --merge_edges \
--out sock_recvmsg_syscalls.png --inverse
```

We use the `--until_function` to stop drawing when the call chain reaches a function call whose name looks like a system call, that is, the function name begins with '__x64_sys'. Also, we use the `--colorize` option to highlight such function calls in the resulting output graph. The `--merge_edges` is used to reduce noise by including only one association between two function calls for cases where there would be many.

<img src=sock_recvmsg_syscalls.png>
<br /><br />

The output graph shows that there are three syscalls whose call chain might reach `sock_recvmsg`: `__x64_sys_recvfrom`, `__x64_sys_recv`, and `__x64_sys_socketcall` defined at net/socket.c:2066, net/socket.c:2077, and net/socket.c:2852 respectively.
