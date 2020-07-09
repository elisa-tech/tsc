<!--
SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)

SPDX-License-Identifier: Apache-2.0
-->

# Collecting gcov data for call graph visualization

## Prerequisities
In order to follow the steps provided in this document it is necessary to have at least GCC minimum version 8 on the system. Also, for creating Debian Stretch image it is
required to install debootstrap package:
```
sudo apt install gcc-8 qemu-system-x86 debootstrap
```
The instructions assume that all necessary files are extracted into folder at path $HOME/kernel-sandbox.
```
mkdir $HOME/kernel-sandbox
tar -xf covviz.tar.xz --directory $HOME/kernel-sandbox
```

## Creating Linux image for Qemu run

In order to collect coverage information for callgraph visulization it is necessary to create Linux image with gcov options enabled.
We followed instructions provided in Google's syzkaller [documentation](https://github.com/google/syzkaller/blob/master/docs/linux/setup_ubuntu-host_qemu-vm_x86-64-kernel.md). Additionally, we included GCOV related configuration options as noted in Linux gcov [documentation](https://www.kernel.org/doc/html/v4.14/dev-tools/gcov.html). The resulting configuration (_covconfig_) is a part of this repository (archive file). In order to reproduce the results it is necessary to run following commands in the kernel-sandbox dir:
```
cd $HOME/kernel-sandbox
git clone git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
cd linux
git checkout 7c30b859a947535f2213277e827d7ac7dcff9c84
cp ../covconfig  .config
make CC=gcc-8 olddefconfig
make -j `nproc`
```
In kernel-sandbox directory create subdirectory for stretch image:
```
mkdir stretch && cd stretch
wget https://raw.githubusercontent.com/google/syzkaller/master/tools/create-image.sh -O create-image.sh
chmod +x create-image.sh
./create-image.sh
```
Using the _run_qemu.sh_ script one can boot the kernel which automatically starts ssh server. This is required to transfer the files to and from the
Qemu virtual machine.


# Stress-ng run
[stress-ng](https://wiki.ubuntu.com/Kernel/Reference/stress-ng) is application for stress testing a computer system. We use it to execute particular
jobs and generate coverage information for system call related subparts of the linux kernel. stress-g needs to be compiled with static libraries. In
kernel-sandbox directory issue following commands:
```
git clone git://kernel.ubuntu.com/cking/stress-ng.git
cd stress-ng
make clean
STATIC=1 make
```
After the stress-ng is successfully built run the following command:
```
./cp_sng.sh
```
This will transfer test scripts to the virtual machine target. Script _jobs.sh_ contains list of stress-ng stressor commands to execute.

# Collecting the data and conversion to callgraph coverage format

After the test scripts are successfully copied, on the target (virtual) machine issue test.sh command in the /root directory.
This will run stress-ng jobs and collect the data into coverage\_data.tar.gz archive.

On host machine, run the script for copying back the coverage data:
```
./collect.sh
```
This will copy coverage\_data.tar.gz in the kernel-sandbox directory. Run following commands to create gcov summary file in CSV format:

```
./convert.sh
```

This command creates coverage data in visualization format suitable for callgraph-tool. For
each detected function it creates a single row containing source file information, function name, coverage percentage and number of lines for function. Missing values are filled with NAN (not a number) values.
