# Callgraph tool file formats

This document explains briefly various files that are used with the callgraph-tool for buidling the callgraph database data,
configure tool behavior or enrich the visualization data.

# Build input

The build input consists typically of build logs collected during the compilation process. However, there are different ways how these logs
need to be collected depending on the selected _build_log_format_ option.
For Linux source code compiling one can
simply enable verbose process with V=1 option and pipe the command line output to build log file. This feature is used in collecting the build logs for build log formats kernel_c and 
kernel_clang.

ll_clang build log format accepts directory where files produced with -emit-llvm clang switch are stored. It recursively collects the list of files with (.ll and .llvm) extensions in the
source directory and stores it to a /tmp directory into a file with random unique name. Thereafter, build proceeds similarly to the kernel_c or kernel_clang build options.
ast_clang build log format uses [compilation database](http://clang.llvm.org/docs/JSONCompilationDatabase.html) in JSON format collected using _bear_ tool.

## Database file

There are two ways to store the callgraph database: Python pickle format and csv files.

### Pickle database
Default option is to store the callgraph database in pickle file. This is simply a dump of dict type object with the keys being caller functions
and values being function callees. This database format can also be seamlessly loaded into _networkx_ graph processing library.

### CSV database
Pickle database can be converted into human readable CSV format using convert_db.py script. When clang_indexer backend is used, i.e. --build_log_format=clang_ast, the database is first produced in CSV format and then converted internally into pickle format to match other build formats. In this case, 

## Settings file

Purpose of the settings file is to have easily reproducable and shareable working setup. Instead of typing the command line options, all the settings can be stored in a JSON file. 

## Configuration file
Configuration file is used to specify indirect calls in the source code. The callgraph-tool is able to detect indirect calls automatically but there are still some use-cases that are not supported. Using manual configuration to circumvent this can result in more compact graph database.

## Coverage information
Coverage information is provided for visualization purposes. This information is produced using various covarage tools (KCOV, GCOV) and preprocessed into CSV format. It is supplied to callgraph-tool using the --coverage_file option. The CSV columns must have following names:

    * filename - path to source file (REQUIRED)
    * function - function name (REQUIRED)
    * coverage - coverage percentage (decimal value or NAN) (OPTIONAL)
    * lines - number of lines of code in function (OPTIONAL)