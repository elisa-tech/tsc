import argparse
import json
import os
import re


def raw_to_compile_commands(fp, cwd):
    dbase = []
    for entry in fp:
        command = {'directory': cwd}

        m = None
        if 'clang' in entry:
            m = re.search(r'clang\S*\s+(?P<cc_args>.+?)-c -o (?P<output>.+?\.o) (?P<filename>.+\.c)', entry)
        elif 'gcc' in entry:
            m = re.search(r'cc\S*\s+(?P<cc_args>.+?)-c -o (?P<output>.+?\.o) (?P<filename>.+\.c)', entry)
        if m:
            command['file'] = m.group('filename')
            command['command'] = entry.strip()
            dbase.append(command)
    return dbase


def main():
    logfile = os.path.expanduser("~/kernel-sandbox/buildlog.txt")
    cwd = os.path.dirname(logfile)
    with open(logfile, 'r') as buildlog:
        dbase = raw_to_compile_commands(buildlog, cwd)
        if dbase:
            outfile = os.path.join(cwd, "compile_commands.json")
            with open(outfile, "w") as handle:
                json.dump(dbase, handle, sort_keys=True, indent=4)


if __name__ == "__main__":
    main()
