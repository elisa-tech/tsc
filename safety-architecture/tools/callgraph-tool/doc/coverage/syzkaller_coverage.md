# Syzkaller coverage

[`syzkaller`](https://github.com/google/syzkaller) is an unsupervized coverage-guided kernel fuzzer. It generates programs (according to specific rules) which are used for testing the Linux kernel and exposing the bugs. This process is guided based on the coverage statistics of the generated programs.

## Obtaining syzkaller coverage

The configuration for the Linux kernel needs to be modified according to the [instructions]([200~https://github.com/google/syzkaller/blob/master/docs/linux/setup_ubuntu-host_qemu-vm_x86-64-kernel.md). This configuration needs to be used when generating the call graph database. 
Program counters that were executed during the syzkaller run can be obtained through `/rawcover` http request handler in `syz-manager` web interface. This data can be saved to a file and then converted into syzkaller coverage data using the `syz-cover` tool's `csv` export option. 
The resulting data has following format:
```
Filename,Function,Covered PCs,Total PCs
/home/user/linux/arch/x86/entry/vsyscall/vsyscall_64.c,addr_to_vsyscall_nr,0,2
/home/user/linux/arch/x86/entry/vsyscall/vsyscall_64.c,emulate_vsyscall,0,50
/home/marijo/linux/arch/x86/entry/vsyscall/vsyscall_64.c,gate_vma_name,0,1
...
/home/user/linux/sound/sound_core.c,cleanup_soundcore,0,1
/home/user/linux/sound/sound_core.c,init_soundcore,0,4
/home/user/linux/sound/sound_core.c,sound_devnode,0,5
```
Details on the file format and the conversion from PC values into coverage database are explained [here](https://github.com/google/syzkaller/blob/master/docs/linux/coverage.md).
This data can be converted into CallGraph tool suitable format using the script [format_coverage.py](../../scripts/format_coverage):
```
format_coverage.py
    --format syzkaller
    --project_root /home/user/
    --coverage syz_coverage.csv
    --out callgraph_coverage.csv