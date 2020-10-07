# Using callgraph with simple C example

This page shows an example of using callgraph with a simple C example program.

Table of Contents
=================

* [Setup](#setup)
* [Example program](#example-program)
* [Compiling target program to bitcode](#compiling-target-program-to-bitcode)
* [Generating callgraph database with crix-callgraph](#generating-callgraph-database-with-crix-callgraph)
* [Visualizing callgraph database](#visualizing-callgraph-database)

## Setup
To begin, make sure you have gone through the following setup instructions from the main [README](../README.md):
- [Getting started](../README.md#getting-started) (no kernel sources are needed for this simple example)
- [Build the crix-callgraph tool](../README.md#build-the-crix-callgraph-tool)

## Example program
We use the following [demo program](../tests/resources/query-callgraph/test-demo.c) as an example target program:
```
// Demonstrate callgraph with a clumsy example

#include <stdio.h>
#include <string.h>

#define MAX_INPUT_LEN 10

typedef void (*fptr_t)(char *);

struct reader_a
{
    fptr_t read;
    int other_data;
};

struct reader_b
{
    fptr_t read;
    char *other_data;
};

void flush()
{
    char c;
    while ((c = getchar()) != '\n' && c != EOF)
        ;
}

char *gets(char *);
void read_no_check(char *buffer)
{
    printf("Input to %s: ", __func__);
    gets(buffer);
}

void read_with_check(char *buffer)
{
    printf("Input to %s: ", __func__);
    if (fgets(buffer, MAX_INPUT_LEN, stdin))
        if (!strchr(buffer, '\n'))
            flush();
}

int main()
{
    char input[MAX_INPUT_LEN];
    struct reader_a safe = {.read = read_with_check};
    struct reader_b unsafe = {.read = read_no_check};
    safe.read(input);
    unsafe.read(input);
    return 0;
}
```

## Compiling target program to bitcode
```
# We assume $CG_DIR variable contains the path to callgraph directory
# Add correct version of clang to PATH
source $CG_DIR/env.sh

# Compile test-demo.c to bitcode, including debug info
cd $CG_DIR/tests/resources/query-callgraph; \
clang -O0 -g -emit-llvm -c -o test-demo.bc test-demo.c
```

## Generating callgraph database with crix-callgraph
```
# Compile crix-callgraph if it wasn't compiled yet
cd $CG_DIR && make

# Generate callgraph based on the test-demo.bc
cd $CG_DIR/tests/resources/query-callgraph; \
$CG_DIR/build/lib/crix-callgraph test-demo.bc -o callgraph_test_demo.csv

# Now, you can find the callgraph database in `callgraph_test_demo.csv`
```

## Visualizing callgraph database

To visualize the functions called by function `main` run the following command:
```
# --csv callgraph_test_demo.csv: use the file callgraph_test_demo.csv as callgraph database file
# --function main: start from the target function 'main' (exact match) 
# --depth 3: include the function calls at depth 3 from 'main'
# --edge_labels: add caller source line numbers to the graph
# --colorize 'gets': colorize graph node if function name matches the given regular expression
# --out test_demo.png: output png-image with filename 'test_demo.png'

cd $CG_DIR
./scripts/query_callgraph.py --csv callgraph_test_demo.csv --function main --depth 3 \
--edge_labels --colorize 'gets' --out test_demo.png
```
Output:

<img src=test_demo.png>
<br /><br />

The output graph shows that function `main` is defined in file test-demo.c on line [44](https://github.com/elisa-tech/workgroups/blob/dc07cf1474f6c693f7087723f53e22c88a259d93/safety-architecture/tools/callgraph-tool/tests/resources/query-callgraph/test-demo.c#L44). It calls two functions: `read_with_check` and `read_no_check`. The calls to these functions takes place from test-demo.c on lines [49](https://github.com/elisa-tech/workgroups/blob/dc07cf1474f6c693f7087723f53e22c88a259d93/safety-architecture/tools/callgraph-tool/tests/resources/query-callgraph/test-demo.c#L49) and [50](https://github.com/elisa-tech/workgroups/blob/dc07cf1474f6c693f7087723f53e22c88a259d93/safety-architecture/tools/callgraph-tool/tests/resources/query-callgraph/test-demo.c#L50). The dashed lines indicate indirect function calls: both calls happen through a function pointer. The two called functions are defined in test-demo.c:[36](https://github.com/elisa-tech/workgroups/blob/dc07cf1474f6c693f7087723f53e22c88a259d93/safety-architecture/tools/callgraph-tool/tests/resources/query-callgraph/test-demo.c#L36) and test-demo.c:[30](https://github.com/elisa-tech/workgroups/blob/dc07cf1474f6c693f7087723f53e22c88a259d93/safety-architecture/tools/callgraph-tool/tests/resources/query-callgraph/test-demo.c#L30) respectively. Notice the node labels refer each function's definition, not declaration location. We colorized nodes where the function name matches regular expression 'gets': there's one such function, which is called from function `read_no_check`. Notice the filename and line number information is missing from the C library functions (strchr, fgets, printf, gets): these are external functions, for which the callgraph does not include any other information except the function name.
