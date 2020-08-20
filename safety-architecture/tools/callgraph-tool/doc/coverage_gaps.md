<!--
SPDX-FileCopyrightText: 2019 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# Coverage Gaps
Having the target system callgraph and the function-local code coverage for each function exercised during a test run, we can combine the information to find coverage gaps.

Coverage gaps are callgraph subtrees where the potential for code coverage improvement is greatest based on the function coverage and the callgraph subtree size rooted with the specific function call. This instruction shows how [find_coverage_gaps.py](../find_coverage_gaps.py) can be used to identify such coverage gaps.

## Getting Started
You need a callgraph database in csv format. Follow the instructions from [setup.md](setup.md) to generate the callgraph for your target system. Then follow the instructions from the section [Converting callgraph database to CSV](setup.md#converting-callgraph-database-to-csv) to convert the pickle database to CSV format.

You also need the code coverage information. The expected format is a CSV file, with at least the following headers: `Filename,Function,Percent`. See [todo](link_here.md) for an example of how to generate such coverage information from a syzkaller test run.

## Finding Coverage Gaps
For the sake of example, let's assume we have the following callgraph and the coverage information as shown in the graph:
<img src=sys_mmap.png width="1000">

To find functions where the potential for code coverage improvement is greatest, run [find_coverage_gaps.py](../find_coverage_gaps.py) as follows:
```
./find_coverage_gaps.py \
  --calls target_callgraph.csv \
  --coverage targe_coverage.csv \
  --caller_function_regex '^__x64_sys_mmap$' \
  --maxdepth 3 \
  --out sys_mmap_gcov.csv
```

The above command runs [find_coverage_gaps.py](../find_coverage_gaps.py) with the specified callgraph database and coverage information (`--calls` and `--coverage`). It finds functions where the function name matches regular expression `^__x64_sys_mmap$` and follows each call chain starting from the matching functions. For each matching call chain, it calculates the coverage gap for all functions in the chain following the caller-callee relations to a point where caller reaches at most `--maxdepth 3` depth. The resulting output is stored in `sys_mmap_gcov.csv`.

In the following section, we use the `csvsql` and `csvlook` from the [csvkit](https://csvkit.readthedocs.io/en/latest/index.html) suite to view and query the output data.

In this simple example, the output contains only five caller-callee pairs as shown in the below table:
```
# Use csvsql to output only the specified columns to make the output more readable
# Sort by callee_coverage_gap descending to make the largest coverage gaps appear at the top
# Use csvlook to render the output as ascii table:

csvsql --query \
  "select \
      caller_function,callee_function,callee_coverage,call_stack,callee_coverage_gap \
    from sys_mmap_gcov \
    order by callee_coverage_gap desc" \
  sys_mmap_gcov.csv | csvlook 

| caller_function | callee_function     | callee_coverage | call_stack                                                                         | callee_coverage_gap |
| --------------- | ------------------- | --------------- | ---------------------------------------------------------------------------------- | ------------------- |
| fput            | fput_many           |           72,73 | __x64_sys_mmap ==> 'ksys_mmap_pgoff' ==> 'fput' ==> 'fput_many'                    |              0,818… |
| vm_mmap_pgoff   | do_mmap             |           92,68 | __x64_sys_mmap ==> 'ksys_mmap_pgoff' ==> 'vm_mmap_pgoff' ==> 'do_mmap'             |              0,512… |
| vm_mmap_pgoff   | down_write_killable |           66,67 | __x64_sys_mmap ==> 'ksys_mmap_pgoff' ==> 'vm_mmap_pgoff' ==> 'down_write_killable' |              0,333… |
| vm_mmap_pgoff   | __mm_populate       |           95,45 | __x64_sys_mmap ==> 'ksys_mmap_pgoff' ==> 'vm_mmap_pgoff' ==> '__mm_populate'       |              0,182… |
| ksys_mmap_pgoff | __audit_mmap_fd     |            0,00 | __x64_sys_mmap ==> 'ksys_mmap_pgoff' ==> '__audit_mmap_fd'                         |              0,000… |

```

The five caller-callee pairs are the cases where the callee coverage is not 100% in the example graph. Since the output is ordered descending by callee_coverage_gap, the topmost entry (`fput ==> fput_many`) indicates the callee where the potential for code coverage improvement is greatest. The value of the callee_coverage_gap is based on the coverage, as well as the subtree size rooted to the specific callee function when walking the call chain at most `--maxdepth 3` callers deep. 

For instance, the last entry (`ksys_mmap_pgoff ==> __audit_mmap_fd`) callee_coverage_gap is zero even though the coverage is worse (0%) than the coverage for the first entry (72.73%). The reason is that `__audit_mmap_fd` is a at the end of the call chain so possible coverage improvement would not lead to coverage improvements in any new subtrees. Conversely, the first entry callee `fput_many` is associated to subtree with three nodes. Therefore, the impact of possible coverage improvement for callee `fput_many` is potentially  bigger considering the overall coverage.

Notice the output also contains the full call stack starting from the function that initially matched the regular expression `^__x64_sys_mmap$`, making it easier to navigate the call chain considered in the calculation.

