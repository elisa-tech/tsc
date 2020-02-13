<!--
SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)

SPDX-License-Identifier: Apache-2.0
-->

# Clang v10
The recent version of clang introduced the support for ASM GOTO constructs. However, clang v10 is currently in the development phase and not yet available for download from the official repository. Therefore, it is necessary for the user to do this process manually at the moment (Ubuntu 18.04 LTS has clang version 6 by default).

The source files can be obtained from the llvm page by checking out LLVM (including related subprojects like Clang):

```
git clone https://github.com/llvm/llvm-project.git
```
or manually downloading the zip of the project (https://github.com/llvm/llvm-project/archive/master.zip).

The next step is to build the clang executable. First, we create the build directory (in tree build is not supported) and set up the cmake options

For Unix make:
```
cd $HOME/llvm-project
mkdir build && cd build
cmake -G "Unix Makefiles" -DLLVM_ENABLE_PROJECTS="clang" -DCMAKE_BUILD_TYPE=Release ../llvm
make -jN (where N is up to the number of cores available on the computer)
```
If you prefer Ninja:

Prerequisite is to install with: apt-get install ninja-build
```
cd $HOME/llvm-project
mkdir build_ninja && cd build_ninja
cmake -G 'Ninja' -DLLVM_ENABLE_PROJECTS="clang" -DCMAKE_BUILD_TYPE=Release ../llvm
```
Cmake step takes up to a minute. Compiling step can take up to couple of hours depending on the setup and available HW resources.

By default, make process compiles for all the supported targets. The default value includes: AArch64, AMDGPU, ARM, BPF, Hexagon, Mips, MSP430, NVPTX, PowerPC, Sparc, SystemZ, X86, XCore. One can select only the subset using the LLVM_TARGETS_TO_BUILD option. A semicolon delimited list controlling which targets will be built and linked into llvm (e.g. -DLLVM_TARGETS_TO_BUILD="X86;Mips" to build only for x86 and mips architectures).

CMAKE_BUILD_TYPE option tells cmake what type of build you are trying to generate files for. As the default is Debug (targeted to the contributors of the project) it is necessary to manually change this to the Release option in order to reduce the output size and speed (Debug version is orders of magnitude slower than the Release). Valid options are Debug, Release, RelWithDebInfo, and MinSizeRel.


# Older Clang versions and ASM GOTO
If you are using older version of clang (prior to version 9) the building process won't work by default because the 'asm goto' optimization was not supported yet. Depending on the version of the Linux kernel for which the call graph is being generated there are various ways to work around this issue (in 2019 the asm goto related definitions were moved from Makefiles to KConfig files).
In versions where asm goto support is controlled with configuration file (newer releases), run the following command:
```
sed -i "s/#define asm_volatile_goto(x...)/#define asm_volatile_goto(x...) \/\//g" $KERNEL_DIRECTORY/include/linux/compiler_types.h
```
For older versions, parts of the Makefile need to be disabled:
```
sed -i s/"CC_HAVE_ASM_GOTO := 1"/"#CC_HAVE_ASM_GOTO := 1"/g  $KERNEL_DIRECTORY/Makefile
sed -i s/"KBUILD_CFLAGS += -DCC_HAVE_ASM_GOTO"/"#KBUILD_CFLAGS += -DCC_HAVE_ASM_GOTO"/g  $KERNEL_DIRECTORY/Makefile
sed -i s/"KBUILD_AFLAGS += -DCC_HAVE_ASM_GOTO"/"#KBUILD_AFLAGS += -DCC_HAVE_ASM_GOTO"/g  $KERNEL_DIRECTORY/Makefile
```
For x86, comment out the @exit 1 line on failed ifndef CC_HAVE_ASM_GOTO block in the _arch/x86/Makefile_.