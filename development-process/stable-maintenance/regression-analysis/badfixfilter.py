#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2019 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: GPL-2.0-only

import argparse
import csv
import os
import sys

import pandas as pd

################################################################################


def df_from_csv_file(name):
    df = pd.read_csv(name, na_values=[''], keep_default_na=False)
    df.reset_index(drop=True, inplace=True)
    return df


def df_to_csv_file(df, name):
    df.to_csv(
        path_or_buf=name,
        quoting=csv.QUOTE_ALL,
        sep=",", index=False, encoding='utf-8')
    print("[+] Wrote: %s" % name)


def filter_csv(db, column, filter, out):
    # Dataframe from db-file
    df_db = df_from_csv_file(db)

    # Dataframe from filter
    df_filter = pd.read_csv(filter, header=None, names=['filter'])
    df_filter.reset_index(drop=True, inplace=True)
    df_filter.drop_duplicates(inplace=True)

    # Merge to filter df_db
    df = df_db.merge(
        df_filter,
        how='left',
        left_on=[column],
        right_on=['filter'],
        indicator=True,
    )

    # Only keep the rows that are in both
    df = df[df['_merge'] == 'both']

    # Drop the intermediate columns 'filter' and 'merge'
    df.drop(['filter', '_merge'], axis=1, inplace=True)
    df_to_csv_file(df, out)


def exit_unless_accessible(filename):
    if not os.path.isfile(filename):
        sys.stderr.write(
            "Error: file not found or no permissions: %s\n" % filename)
        sys.exit(1)


def getargs():
    desc = \
        "Filter data generated with badfixstats.py. "\
        "Given badfix database (--db), "\
        "filter the database by only outputting "\
        "the rows where specified column (--col) values match "\
        "any of the lines in the text file (--filter). "\

    epil = "Example: ./%s --db badfixdb.csv --col Commit_hexsha "\
        "--filter patchlist.txt" % \
        os.path.basename(__file__)
    parser = argparse.ArgumentParser(description=desc, epilog=epil)

    required_named = parser.add_argument_group('required named arguments')
    help = "CSV database to be filtered (output from badfixstats.py)"
    required_named.add_argument('--db', help=help, required=True)

    help = "CSV database column name"
    required_named.add_argument('--col', help=help, required=True)

    help = "Text file specifying the accepted values, one value per line"
    required_named.add_argument('--filter', help=help, required=True)

    help = \
        "set the output file name, default is the db-name, prefixed with "\
        " __filtered.csv"
    parser.add_argument('--out', nargs='?', help=help, default='')

    return parser.parse_args()

################################################################################


if __name__ == "__main__":
    args = getargs()

    exit_unless_accessible(args.db)
    exit_unless_accessible(args.filter)

    out = args.out
    if not out:
        out = "%s__filtered.csv" % args.db

    filter_csv(args.db, args.col, args.filter, out)

################################################################################
