<!--
SPDX-FileCopyrightText: 2019 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# Coverage Gaps
Having the target system callgraph and the function-local code coverage for each function exercised during a test run, we can combine the information to find coverage gaps.

Coverage gaps are callgraph subtrees where the potential for code coverage improvement is greatest based on the function coverage and the callgraph subtree size rooted with the specific function call. This instruction shows how [find_coverage_gaps.py](../../scripts/find_coverage_gaps.py) can be used to identify such coverage gaps.

## Getting Started
You need a callgraph database in csv format. Follow the instructions from [README.md](../../README.md) to generate the callgraph for your target system.

You also need the code coverage information. The expected format is a CSV file, with at least the following headers: `Filename,Function,Percent`. See [todo](link_here.md) for an example of how to generate such coverage information from a syzkaller test run.

## Finding Coverage Gaps
For the sake of example, let's assume we have the following callgraph and the coverage information as shown in the graph (the multiple paths in the image are collated using `merge_edges` for better visibility):
<img src=ksys_mmap_pgoff.png width="1100">

To find functions where the potential for code coverage improvement is greatest, run [find_coverage_gaps.py](../../find_coverage_gaps.py) as follows:
```
./find_coverage_gaps.py \
  --calls target_callgraph.csv \
  --coverage target_coverage.csv \
  --caller_function_regex '^ksys_mmap_pgoff$' \
  --maxdepth 2 \
  --out ksys_mmap_pgoff_cov.csv
```

The above command runs [find_coverage_gaps.py](../../scripts/find_coverage_gaps.py) with the specified callgraph database and coverage information (`--calls` and `--coverage`). It finds functions where the function name matches regular expression `^ksys_mmap_pgoff$` and follows each call chain starting from the matching functions. For each call chain, it calculates the coverage gap for all functions in the chain following the caller-callee relations to a point where caller reaches at most `--maxdepth 2` depth. The resulting output is stored in `ksys_mmap_pgoff_cov.csv`.

In the following section, we use the `csvsql` and `csvlook` from the [csvkit](https://csvkit.readthedocs.io/en/latest/index.html) suite to view and query the output data.

In this simple example, the output contains only the excerpt caller-callee pairs as shown in the below table:
```
# Use csvsql to output only the specified columns to make the output more readable
# Sort by callee_coverage_gap descending to make the largest coverage gaps appear at the top
# Use csvlook to render the output as ascii table:

csvsql --query \
  "select \
      caller_function,callee_function,callee_coverage,callee_coverage_gap,call_stack \
    from ksys_mmap_pgoff_cov \
    order by callee_coverage_gap desc" \
  ksys_mmap_pgoff_cov.csv | csvlook 

| caller_function              | callee_function                  | callee_coverage_gap | callee_coverage | callee_subtree_size |
| ---------------------------- | -------------------------------- | ------------------- | --------------- | ------------------- |
| ksys_mmap_pgoff              | hugetlb_file_setup               |            148,667… |         66,667… |                 446 |
| hugetlb_file_setup           | hugetlb_reserve_pages            |             90,632… |         26,316… |                 123 |
| vm_mmap_pgoff                | do_mmap                          |             75,286… |         55,714… |                 170 |
| vm_mmap_pgoff                | do_mmap                          |             75,286… |         55,714… |                 170 |
| vm_mmap_pgoff                | do_mmap                          |             75,286… |         55,714… |                 170 |
| hugetlb_file_setup           | iput                             |             40,912… |         61,765… |                 107 |
| hugetlb_file_setup           | hugetlbfs_get_inode              |             26,400… |         40,000… |                  44 |
| hugetlb_file_setup           | user_shm_lock                    |             20,000… |          0,000… |                  20 |
| vm_mmap_pgoff                | __mm_populate                    |             19,111… |         55,556… |                  43 |
| hugetlb_file_setup           | user_shm_unlock                  |              4,000… |          0,000… |                   4 |
| hugetlb_file_setup           | alloc_file_pseudo                |              3,833… |         83,333… |                  23 |
...
| ksys_mmap_pgoff              | __sanitizer_cov_trace_pc         |              0,000… |          0,000… |                   0 |
| fput                         | __sanitizer_cov_trace_pc         |              0,000… |          0,000… |                   0 |
```

These caller-callee pairs are the cases where the callee coverage is not 100% in the example graph. Since the output is ordered descending by callee_coverage_gap, the topmost entry (`ksys_mmap_pgoff ==> hugetlb_file_setup`) indicates the callee where the potential for code coverage improvement is greatest. The value of the callee_coverage_gap is based on the coverage, as well as the subtree size rooted to the specific callee function considering the call chain at most `--maxdepth 2` callers deep. 

For the entry lower in the table (`hugetlb_file_setup ==> usr_shm_unlock`) callee_coverage_gap is much smaller even though the coverage is worse (0%) than the coverage for the first entry (66.667%). The reason is that `__audit_mmap_fd` is at the end of the call chain so possible coverage improvement would not lead to coverage improvements in any new subtrees. Conversely, the first entry callee for the first entry on the above table is associated to subtree with many nodes. Therefore, the impact of possible coverage improvement for callee `hugetlb_file_setup` is potentially bigger considering the overall coverage.
There are many entries to `__sanitizer_cov_trace_pc`. These are the calls inserted by the compiler in order to be able to track the coverage but they are not relevant in discussion for increasing the overall coverage.

The output [CSV](ksys_mmap_pgoff_cov.csv) also contains the full call stack starting from the function that initially matched the regular expression `^ksys_mmap_pgoff$`, making it easier to navigate the call chain considered in the calculation. We do not show it here for better readability.
