# Using callgraph with C++ targets

This page documents how to use crix-callgraph with C++ targets.

Table of Contents
=================

* [Setup](#setup)
* [Simple C++ Example](#simple-c-example)
   * [Example program](#example-program)
   * [Compiling target program to bitcode](#compiling-target-program-to-bitcode)
   * [Generating callgraph database with crix-callgraph](#generating-callgraph-database-with-crix-callgraph)
   * [Visualizing callgraph database](#visualizing-callgraph-database)
* [C++ CMake example](#c-cmake-example)
   * [Compiling target program to bitcode](#compiling-target-program-to-bitcode-1)
   * [Generating callgraph database with crix-callgraph](#generating-callgraph-database-with-crix-callgraph-1)
   * [Visualizing callgraph database](#visualizing-callgraph-database-1)

## Setup
To begin, make sure you have gone through the following setup instructions from the main [README](../README.md):
- [Getting started](../README.md#getting-started) (no kernel sources are needed for this simple example)
- [Build the crix-callgraph tool](../README.md#build-the-crix-callgraph-tool)

## Simple C++ Example
### Example program
We use the following [demo program](../tests/resources/query-callgraph/test-cpp-demo.cpp) as our first example C++ target program:
```
// Demonstrate C++ callgraph with a simple example

#include <iostream>

using namespace std;

////////////////////////////////////////////////////////////////////////////////

class Worker 
{
public:
    virtual void do_init() = 0;
    virtual void do_work() = 0;
    virtual void run();
};


void Worker::run()
{
    cout << __PRETTY_FUNCTION__ << "\n";

    // Call implementation from the derived class:
    this->do_init();
    this->do_work();
}

////////////////////////////////////////////////////////////////////////////////

class DummyWorker: public Worker
{
public:
    void do_init();
    void do_work();
};

void DummyWorker::do_init()
{
    cout << __PRETTY_FUNCTION__ << "\n";
}
void DummyWorker::do_work()
{
    cout << __PRETTY_FUNCTION__ << "\n";
}

////////////////////////////////////////////////////////////////////////////////

int main()
{
    DummyWorker w;
    w.run();
    return 0;
}

////////////////////////////////////////////////////////////////////////////////
```
### Compiling target program to bitcode
```
# We assume $CG_DIR variable contains path to callgraph directory

# Add correct version of clang to PATH
source $CG_DIR/env.sh

# Compile test-cpp-demo.cpp to bitcode:
cd $CG_DIR/tests/resources/query-callgraph; \
clang++ -O0 -g -flto -fwhole-program-vtables -fvisibility=hidden \
    -emit-llvm -c -o test-cpp-demo.bc test-cpp-demo.cpp
```
Internally, crix-callgraph uses the LLVM type metadata that was originally introduced for CFI to identify the virtual call targets. Therefore, the target C++ bitcode needs to be build with -fwhole-program-vtables enabled. 

### Generating callgraph database with crix-callgraph
```
# Compile crix-callgraph if it wasn't compiled yet
cd $CG_DIR && make

# Generate callgraph based on the test-cpp-demo.bc
cd $CG_DIR/tests/resources/query-callgraph; \
$CG_DIR/build/lib/crix-callgraph --cpp_linked_bitcode test-cpp-demo.bc -o callgraph_test_cpp_demo.csv test-cpp-demo.bc

# Now, you can find the callgraph database in `callgraph_test_cpp_demo.csv`
```

### Visualizing callgraph database

To visualize the functions called by function `main` run the following command:
```
# --csv callgraph_test_cpp_demo.csv: use the file 'callgraph_test_cpp_demo.csv' as callgraph database file
# --function main: start from the target function 'main' (exact match) 
# --depth 3: include the function calls until depth 3 from 'main'
# --edge_labels: add caller source line numbers to the graph
# --out test_cpp_demo.png: output png-image with filename 'test_cpp_demo.png'

cd $CG_DIR/tests/resources/query-callgraph; \
$CG_DIR/scripts/query_callgraph.py --csv callgraph_test_cpp_demo.csv --function main --depth 3 \
--edge_labels --out test_cpp_demo.png
```
Output:

<img src=test_cpp_demo.png>
<br /><br />

The output graph shows that function `main` is defined in file [test-cpp-demo.cpp](../tests/resources/query-callgraph/test-cpp-demo.cpp) on line 47. It calls two functions: `DummyWorker` and `run`. The calls to these functions takes place from [test-cpp-demo.cpp](../tests/resources/query-callgraph/test-cpp-demo.cpp) on lines 49 and 50. The two called functions are defined in test-cpp-demo.cpp:29 and test-cpp-demo.cpp:18 respectively.

The call to function `DummyWorker` initiates from line 49 where the DummyWorker object `w` is initialized: this is the automatic call to constructor when the object of type DummyWorker is created. Further, the graph shows a call from the DummyWorker's constructor to function `Worker` which is the constructor for the base class. Neither DummyWorker or Worker implicitly define constructors, so the constructor line numbers are set to the line where each class is defined.

The dashed lines indicate indirect function calls. Calls from function `run` to functions `do_init` and `do_work` are shown as indirect calls in the graph, because virtual functions in C++ are implemented as function pointers. The targets of virtual function calls are correctly resolved to `do_init` and `do_work` functions defined on lines 36 and 40.

Finally, the calls to `cout` on lines 20, 38, and 42 initiate calls to function `_ZStlsISt11char_traitsIcEERSt13basic_ostreamIcT_ES5_PKc`. This function corresponds to the [mangled](https://en.wikipedia.org/wiki/Name_mangling) name for function `std::basic_ostream<char, std::char_traits<char> >& std::operator<<<std::char_traits<char> >(std::basic_ostream<char, std::char_traits<char> >&, char const*)`. By default, crix-callgraph demangles function names that have demangled names in the debug information. If you would like to see demangled names for all functions, try running crix-callgraph with option `--demangle_all`. Similarly, to not demangle any function names, try option `--demangle_none`.

## C++ CMake example
For an example of C++ CMake target program, we show how to generate callgraph from the crix-callgraph itself. This section assumes you have gone through the setup instructions from the main [README](../README.md) and have set the `CG_DIR` to contain the path to crix-callgraph as explained in the instructions from the main [README](../README.md).

Additionally, in these instructions, we are going to use [bear](https://github.com/rizsotto/Bear) to generate the compilation database. Bear is available e.g. via Ubuntu package manager:
```
sudo apt install bear
```

### Compiling target program to bitcode
```
cd $CG_DIR

# Add correct version of clang to PATH
source env.sh

# Compile crix-callgraph
make clean && make

# Generate compile-commands.json
cd build && make clean && bear make

# Compile bitcode files using compdb2bc.py:
cd lib && \
$CG_DIR/scripts/compdb2bc.py \
    --clang="$(which clang++)" \
    --compdb ../compile_commands.json \
    --v=2 \
    --append_arg='-g -O0 -flto -fwhole-program-vtables -fvisibility=hidden' \
    --keepcwd > compdb2bc.log 2>&1

# List all generated bitcode files
find ~+ -type f -name "*.bc" > bitcodefiles.txt

# Generate whole-program bitcode file
# by linking the set of .bc files listed in bitcodefiles.txt:
llvm-link @bitcodefiles.txt > wholeprogram.bc
```
Internally, crix-callgraph uses the LLVM type metadata that was originally introduced for CFI to identify the virtual call targets. Therefore, the target C++ bitcode needs to be build with -fwhole-program-vtables enabled. Resolving virtual call targets needs a single merged module: we use the llvm-link to merge the set of bitcode files into one whole-program bitcode file.

### Generating callgraph database with crix-callgraph
```
cd $CG_DIR/build/lib

# Generate callgraph database using the .bc files listed
# in bitcodefiles.txt as main input. Additionally, use the
# wholeprogram.bc to resolve the virtual call targets.
./crix-callgraph --cpp_linked_bitcode wholeprogram.bc @bitcodefiles.txt -o crix_callgraph.csv
```
Notice that we intentionally don't use the whole-program bitcode as main input to crix-callgraph. Instead, we use the list of individual pre-linked bitcode files (bitcodefiles.txt). On linking, llvm applies optimizations such as merging structurally identical struct types to avoid struct type duplication. Such struct type merging would make identifying indirect call targets less accurate, therefore, we use the pre-linked bitcode files as main input to crix-callgraph.

### Visualizing callgraph database

To visualize the functions called by function `main` run the following command:
```
cd $CG_DIR/build/lib

# --csv crix_callgraph.csv: use the file 'crix_callgraph.csv' as callgraph database file
# --function main: start from the target function 'main' (exact match) 
# --depth 1: include the function calls called by the 'main' function
# --edge_labels: add caller source line numbers to the graph
# --out test_crixcg_d1.png: output png-image with filename 'test_crixcg_d1.png'

$CG_DIR/scripts/query_callgraph.py --csv crix_callgraph.csv --function main --depth 1 \
--edge_labels --out test_crixcg_d1.png
```
Output:

<img src=test_crixcg_d1.png width=200>
<br /><br />

It's easy to lose track of relevant call chains in visualizing C++ functions due to the large amount of function calls to C++ libraries that might not be relevant from the main target program view point. For that reason, we use the [q](https://github.com/harelba/q) program to filter out C++ library functions from the callgraph database. To install q, follow the installatin instructions from [github](https://github.com/harelba/q).

```
cd $CG_DIR/build/lib

# -w all        : input quoting mode 'all'
# -W all        : output quoting mode 'all'
# -H            : input includes a header line 
# -d,           : field delimiter is ','
# -O            : output header line
q -w all -W all -H -d, -O  \
    "select * from crix_callgraph.csv \
        where callee_filename not like '/usr/lib%' and \
        callee_filename != ''" \
    > crix_callgraph_filtered.csv 
```

Then, re-run the earlier visualization query using the crix_callgraph_filtered.csv as an input csv:
```
cd $CG_DIR/build/lib

$CG_DIR/scripts/query_callgraph.py --csv crix_callgraph_filtered.csv --function main --depth 1 \
--edge_labels --out test_crixcg_filtered_d1.png
```
Output:

<img src=test_crixcg_filtered_d1.png>
<br /><br />

The output graph shows that function `main` is defined in file [Analyzer.cc](../src/lib/Analyzer.cc) on line 117 (below graph was generated with the HEAD at commit 01e8bd13). It calls two functions: `run` and `resolveVirtualCallTargets`. The calls to these functions takes place from [Analyzer.cc](../src/lib/Analyzer.cc) on lines 178 and 181. The two called functions are defined in Analyzer.cc:65 and Callgraph.cc:912 respectively.

If we increase the `--depth` to 3, the output becomes:

<img src=test_crixcg_filtered_d3.png>
<br /><br />

Notice the indirect calls from function Analyzer.cc:`run`: the three virtual function calls on Analyzer.cc lines 75, 94, and 110 all have the same type bool(Module*). Since the header file, Analyzer.h, includes default implementation for the virtual functions, the three functions from Analyzer.h are possible targets to all three virtual calls (doInitialization, foFinalization, and do ModulePass). In addition, possible targets include the implementations in the inherited class in file CallGraph.cc.

