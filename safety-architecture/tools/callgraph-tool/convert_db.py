#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import csv
import numpy as np
import pandas as pd

from db import GraphDb
from llvm_parse import Function


def loadcalls(callsfile):
    df = pd.read_csv(callsfile)
    return df


def convert_nan(value, outval):
    if pd.isnull(value):
        return outval
    return value


def convert_to_indirect(value):
    value = convert_nan(value, False)
    return True if value == 'indirect' else False


def convert_from_indirect(indirect):
    return 'indirect' if indirect else 'direct'


def convert_to_line_numbers(line_numbers):
    value = convert_nan(line_numbers, None)
    return [value] if value else None


def convert_from_line_numbers(line_numbers):
    if line_numbers:
        return ",".join([str(int(num)) for num in line_numbers])
    return ""


def extractcall(row):
    caller_name = row['caller_function']
    if caller_name is np.nan:
        return (None, None)
    caller_file = convert_nan(row['caller_filename'], "")
    caller_line = convert_to_line_numbers(row['caller_line'])
    caller_indr = convert_to_indirect(row['caller_calltype'])
    caller = Function(name=caller_name,
                      source_file=caller_file,
                      line_numbers=caller_line,
                      indirect=caller_indr)
    callee_name = row['callee_function']
    if callee_name is np.nan:
        return (None, None)
    callee_file = convert_nan(row['callee_filename'], "")
    callee_line = convert_to_line_numbers(row['callee_line'])
    callee_indr = convert_to_indirect(row['callee_calltype'])
    callee = Function(name=callee_name,
                      source_file=callee_file,
                      line_numbers=callee_line,
                      indirect=callee_indr)

    return (caller, callee)


def calls_to_db(infile, db):
    df = loadcalls(infile)
    total = 0
    skipped = 0
    for idx, row in df.iterrows():
        total = idx
        caller, callee = extractcall(row)
        if caller is None or callee is None:
            skipped += 1
            continue

        if caller not in db:
            db[caller] = []
        if callee not in db[caller]:
            db[caller].append(callee)

    return skipped, total


def db_to_calls(db, outfile):
    header = ["caller_filename", "caller_line", "caller_function", "caller_calltype",
              "callee_filename", "callee_line", "callee_function", "callee_calltype"]
    table = []
    for caller in db:
        caller_cols = [caller.source_file, convert_from_line_numbers(caller.line_numbers),
                       caller.name, convert_from_indirect(caller.indirect)]
        for callee in db[caller]:
            callee_cols = [callee.source_file, convert_from_line_numbers(callee.line_numbers),
                           callee.name, convert_from_indirect(callee.indirect)]
            row = caller_cols + callee_cols
            table.append(row)

    df = pd.DataFrame(table, columns=header)
    df.to_csv(outfile, index=False, quoting=csv.QUOTE_ALL)


def getargs():
    desc = \
        "Simple tool for converting call graph database pickle to clang indexer csv format"
    epil = "Example: ./convert_db.py call_graph.pickle --out cg_calls.csv"
    parser = argparse.ArgumentParser(description=desc, epilog=epil)

    help = "Call graph database in pickle file format. Output from callgraph-tool build"
    parser.add_argument('db', help=help)

    help = "Name of the output CSV file"
    parser.add_argument('--out', nargs='?', help=help, default="calls.csv")

    return parser.parse_args()

################################################################################


if __name__ == '__main__':
    args = getargs()

    db = GraphDb(args.db)
    db.open()
    print("[+] Converting pickle database to csv format. Please wait...")
    db_to_calls(db, args.out)

################################################################################
