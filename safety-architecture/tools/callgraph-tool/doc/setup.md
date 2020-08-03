<!--
SPDX-FileCopyrightText: 2019 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# Setup example: Ubuntu 18.04.4
These are instructions for how to setup callgraph on Ubuntu 18.04.4. In addition, it includes some typical example uses of the callgraph tool.

## Getting Started
Checkout callgraph:
```
git clone https://github.com/elisa-tech/workgroups.git
CG_DIR=$(pwd)/workgroups/safety-architecture/tools/callgraph-tool
```

Install required python packages:
```
cd $CG_DIR
pip3 install -r requirements.txt
```

You also need the target kernel source tree. For the sake of example, we use the mainline tree:
```
git clone https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
KERNEL=$(pwd)/linux
```

## Generating callgraph database
To make use of the tool, you first need to generate callgraph database relevant for your kernel source tree and configuration. Callgraph supports a number of ways to generate the database, see: [buildlogoptions.md](https://github.com/elisa-tech/workgroups/blob/master/safety-architecture/tools/callgraph-tool/doc/buildlogoptions.md) for full details. We use the the `--build_log_format kernel_clang` as an example here.

First, we download clang with `clang_download.py`:
```
cd $CG_DIR/clang_indexer
./clang_download.py
```

Next, we build the kernel with the relevant configuration using clang. We use the `defconfig` configuration and compile using the version of clang we just downloaded.

To generate the configuration file for `defconfig`, run the following:
```
cd $KERNEL
make clean
make CC=$CG_DIR/clang_indexer/clang/bin/bin/clang defconfig
```

Then, build the kernel using clang:
```
cd $KERNEL
make -j $(nproc) CC=$CG_DIR/clang_indexer/clang/bin/bin/clang V=1 2>&1 | tee build.log
```

Finally, generate callgraph pickle database based on the generated build.log:
```
cd $KERNEL
$CG_DIR/callgraph-tool.py \
  --build $KERNEL/build.log \
  --clang $CG_DIR/clang_indexer/clang/bin/bin/clang \
  --build_log_format kernel_clang \
  --db $CG_DIR/db.pickle
```

The resulting callgraph database is stored in `$CG_DIR/db.pickle`.

## Querying callgraphs
Once the database is generated, it can be used to query and visualize function callgraphs.

As an example, to query callgraph starting from function `__x64_sys_close` with max depth of four function calls, you would run:
```
./callgraph-tool.py --db $CG_DIR/db.pickle --graph __x64_sys_close --depth 4
```
By default, the output is in textual format:
```
__x64_sys_close -> __se_sys_close
  __se_sys_close -> __do_sys_close
    __do_sys_close -> __close_fd
      __close_fd -> _raw_spin_lock, __put_unused_fd, __raw_spin_unlock, filp_close
```
To view the same graph visually, add `--view` argument to the command:
```
./callgraph-tool.py --db $CG_DIR/db.pickle --graph __x64_sys_close --depth 4 --view
```
Which outputs the callgraph as an image:
<img src=sys_close.png width="900">
