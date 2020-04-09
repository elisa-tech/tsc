<!--
SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)

SPDX-License-Identifier: Apache-2.0
-->

# Call Graph Tool for Linux Kernel (using static analysis)

## Summary

Call Graph is tool for studying call graphs between different function calling paths in Linux. 


## Prerequisites
```
pip3 install -r requirements.txt
```
In order to be able to generate the call graph database, it is required to install llvm tools
```
sudo apt install llvm
```
Except for the default Clang available on the system, user can generate custom toolchain and 
use it with the callgraph tool. See [clang setup](doc/clangsetup.md) for more information.

Raw data (pickle-file) needs to be generated before inspecting the call graphs. For testing purposes there is call_graph.pickle in repository which is generated from Linux v4.19.99 (default config).
You can find instructions on how to generate this file down below.
If you have generated pickle-file, please continue to section about inspecting the callgraph data. 

## Generating the call graph raw data 

0. ASM GOTO 
Depending on the choice of clang version used, it might be necessary to disable support for ASM GOTO in the compilation process. If clang version is greater or equal 9, it is safe to
skip this step. Otherwise, check the section about older Clang versions in the [clang setup](doc/clangsetup.md) file. One convenient way to get the latest Clang is to use scripts provided within [ClangBuildLinux](https://github.com/ClangBuiltLinux/tc-build) repository.

### Build Log options

Callgraph tool support various build options which can be selected with --build_log_format option:
* kernel\_c
* kernel\_clang
* ll\_clang

Default option is _kernel\_c_. The instructions in this document assume the default option. For more details about other options see the detailed [documentation](doc/buildlogoptions.md) for build log options.


1. Collect verbose build log for Linux kernel like so:
```
make defconfig
make -j `nproc` V=1 &> buildlog.txt
```

2. Still executing from kernel root, feed build log to callgraph-tool (this option uses system clang):
```
callgraph-tool.py --build ./buildlog.txt
```

In order to use custom clang build, user can specify the path to the executable binary so that the callgraph-tool will use this instead of the default clang
version on the system: 

```
callgraph-tool.py --build buildlog.txt --clang $HOME/llvm-project/build/bin/clang-10
```
The output is stored in the file call_graph.pickle (name can be user specified via --db option).

_Support for different architectures:_
Callgraph can analyse buildlog for different target architectures. Currently, the supported versions are 'x86', which is a default, and 'mips'. The
appropriate architecture can be selected using --arch command line option. When using mips option, it is recommended to use the newest clang version, i.e.
```
callgraph-tool.py --build buildlogmips.txt --arch mips --clang $HOME/llvm-project/build/bin/clang-10
```
Setting up the cross-compiling environment is out of scope of this documentation.

3. Optional. Callgraph-tool has (experimental) support for inclusion of dynamic data from ftrace logs into the callgraph database
```
callgraph-tool.py --ftrace_enrich --ftrace ftrace.log
```
The output is stored in the file \<original pickle database\>.ftrace

4. Optional. Trigger map database can be generated from the call graph database and configuration file. See [configuration documents](doc/configuration.md) for more details about the configuration file and trigger maps.
```
callgraph-tool.py --build_trigger_map --db call_graph.pickle --config configuration.yaml
```
The output is stored in the file trigger_call_map.pickle (name can be user specified via --trgdb option).

### Fast callgraph build
Callgraph tool supports reusing existing _llvm_ files generated in the previous build using the _--fast_build_ option. This feature is useful during the tool development process.

### Exclude from build
Specific files and folders can be skipped from build using the --exclude_from_build command line option. The arguments are provided as comma separated list. If any word
in a list is contained in the path name to a processed file it will be skipped.

## Inspecting the call graph data

Script can be used from any directory. 

### Who can call this function?

The below query answers the question: what functions can call `__ip6_rt_update_pmtu`, and consequently,
what functions can call those functions?

```
callgraph-tool.py --inverse_graph __ip6_rt_update_pmtu
```
Output:
```
__ip6_rt_update_pmtu <- ip6_update_pmtu, ip6_rt_update_pmtu
  ip6_update_pmtu <- ah6_err, esp6_err, ip6_sk_update_pmtu, icmpv6_err
    ip6_sk_update_pmtu <- __udp6_lib_err, rawv6_err
      __udp6_lib_err <- udpv6_err(udp_table), udplitev6_err(udplite_table)
        ...
      rawv6_err <- raw6_icmp_error
        ...
```

### Which functions this function can call?

This query is the inverse of the above one.  The output can get pretty long, default recursion depth is 3.

Also, a few debug functions are suppressed (modify the script if you wish to see them), and every function
only appears once to avoid circular links.

```
callgraph-tool.py --graph __ip6_rt_update_pmtu --depth 0
```
Output:
```
__ip6_rt_update_pmtu -> dst_metric_locked, inet6_sk, dst_confirm_neigh, dst_mtu, rt6_cache_allowed_for_pmtu, rt6_do_update_pmtu, rt6_update_exception_stamp_rt, __rcu_read_lock, rcu_read_unlock, ip6_rt_cache_alloc, rt6_insert_exception, dst_release_immediate
```

### Find code path between two functions

```
callgraph-tool.py --path vfs_write..__x64_sys_write
```
Output:
```
vfs_write <- ksys_write <- __do_sys_write <- __se_sys_write <- __x64_sys_write
```

### Find all code paths between a given function and functions listed in configuration.yaml

```
callgraph-tool.py  --multipath find_extend_vma
```
Output:
```
read: find_extend_vma <- __get_user_pages <- get_user_pages_unlocked <- get_user_pages_fast <- iov_iter_get_pages_alloc <- nfs_direct_read_schedule_iovec <- nfs_file_direct_read <- nfs_file_read <- file_operations.read_iter <- call_read_iter <- new_sync_read <- __vfs_read <- vfs_read <- ksys_read <- __do_sys_read <- __se_sys_read <- __x64_sys_read
mmap: find_extend_vma <- __get_user_pages <- populate_vma_page_range <- __mm_populate <- mm_populate <- vm_mmap_pgoff <- ksys_mmap_pgoff <- __do_sys_mmap <- __se_sys_mmap <- __x64_sys_mmap
mprotect: find_extend_vma <- __get_user_pages <- populate_vma_page_range <- mprotect_fixup <- do_mprotect_pkey <- __do_sys_mprotect <- __se_sys_mprotect <- __x64_sys_mprotect
...
```
### Batch processing

Callgraph tool provides support for batch processing. The options _--batch\_graph_ and _--batch\_inverse\_graph_ are analogous to the _--graph_ and _--inverse_graph__. In this case the input is file with the list of the functions (line separated). The output is table (*.csv file) containing the information about the function that can be called from (connected_calls.csv) or can call functions in the input (connected_calls_inv.csv), respectively.

## Speed up the startup time

Loading the databases (call graph and trigger map) takes significant amount of time. In order to speed up the processing for repeated queries tool can be used in service/client mode.
In one terminal start (optionally providing the alternative database locations ):
```
callgraph-tool.py -s
```
In another terminal add the `-c` flag to the command you want to execute, for example:
```
callgraph-tool.py -c  --multi_path find_extend_vma
```
Only one instance of server is allowed on the system at the same time.



## License
This project is licensed under the Apache license, version 2.0 - see the Apache-2.0.txt file for details.