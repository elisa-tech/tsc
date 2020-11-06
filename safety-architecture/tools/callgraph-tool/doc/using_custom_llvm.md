# Crix-callgraph with custom LLVM 

This page documents instructions on how to use crix-callgraph with custom version of LLVM.  

## Setup
To begin, make sure you have gone through the setup instructions from the main [README](../README.md#getting-started). In this example, we will be using the mainline tree as the target kernel:
```
cd ~   # wherever you prefer to clone the kernel tree to
git clone https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
cd linux
git checkout master
```

The below instructions assume you have setup the `$KERNEL` and `$CG_DIR` variables to contain the path to the target kernel tree and the callgraph-tool directories as explained in the main [README](../README.md).

## Getting LLVM binaries
We will download pre-built llvm binaries from https://github.com/llvm/llvm-project/releases using the [clang_download.py](../scripts/clang_download.py) helper script. [clang_download.py](../scripts/clang_download.py) currently supports Ubuntu 18.04 and Ubuntu 20.04 host systems. For any other distribution or operating system you might have to manually download the llvm binaries or build llvm from sources. If you prefer building your own llvm binaries from the sources, note that crix-callgraph has been tested with llvm-10 and llvm-11 releases and might not work with newer releases.
```
cd $CG_DIR

# Download pre-built binaries
./scripts/clang_download.py

# Now, you can find pre-built binaries from `$CG_DIR/clang/bin/bin`
```
## Building crix-callgraph with custom LLVM
To compile crix-callgraph using the custom version of LLVM, run:
```
cd $CG_DIR

# Make sure correct version of clang is in $PATH. 
# Notice the argument './clang' which indicates the directory that
# contains the clang binaries somewhere in the directory hierarchy
source env.sh ./clang

# Clean
make clean

# Build crix-callgraph using LLVM libraries from specified
# directory (LLVM_DIR) expecting the specified LLVM version
# (LLVM_VERSION)
make LLVM_DIR=./clang/bin/ LLVM_VERSION=11.0.0

# Now, you can find the executable in `build/lib/crix-callgraph`
```
## Building kernel with custom LLVM
Make sure the correct version of clang is in the PATH before any other version of clang by setting the environment with `cd $CG_DIR && source env.sh ./clang` before building the kernel. Then, follow the instructions e.g. from the main [README](../README.md#generate-bitcode-files-from-the-target-program) to build the kernel and generate bitcode files.
