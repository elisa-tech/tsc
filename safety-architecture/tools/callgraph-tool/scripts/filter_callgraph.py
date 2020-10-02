#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import csv
import logging
import os
import pandas as pd

import utils

_LOGGER = logging.getLogger(utils.LOGGER_NAME)

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
    _LOGGER.info("wrote: %s" % name)


def df_regex_filter(df, column, regex):
    return df[~df[column].str.contains(regex, regex=True, na=False)]


def getargs():
    desc = "Filter the call graph database in CSV format based on the column values"
    epil = "Example: ./%s  --cols caller_function "\
        "--filters '^__x64_sys_' --calls callgraph.csv" % \
        os.path.basename(__file__)

    parser = argparse.ArgumentParser(description=desc, epilog=epil)

    help = "List of columns to filter. Number of cols must be either one or match the"\
        " number of arguments passed to --filter_regex option. In case that the only one"\
        " value is specified it is broadcasted for all the regex values."
    parser.add_argument("--cols", nargs="+", help=help, required=True)
    help = "Regular expresion for filtering the rows. Number of arguments must be either one"\
        " or match number of arguments passed to --cols option. In case that only one value"\
        " is specified it is broadcasted for all the columns. "
    parser.add_argument("--filters", nargs="+", help=help, required=True)
    help = "Set the verbosity level (e.g. -vv for debug level)"
    parser.add_argument(
        '-v', '--verbose', help=help, action='count', default=1)
    help = "Function call database csv file"
    parser.add_argument('--calls', help=help, required=True)
    help = "The output CSV file. If not specified the resulting file will be stored"\
           "to the same directory where input file resides and will use the name of the"\
           "original file with 'filtered_' prefix"
    parser.add_argument('--out', help=help, default="")
    return parser.parse_args()


if __name__ == '__main__':
    args = getargs()

    utils.exit_unless_accessible(args.calls)
    utils.setup_logging(verbosity=args.verbose)

    cols, col_cnt = args.cols, len(args.cols)
    filters, filters_cnt = args.filters, len(args.filters)

    if filters_cnt == 1:
        # broadcast
        filters = [filters[0]] * col_cnt
        filters_cnt = col_cnt

    if col_cnt == 1:
        # broadcast
        cols = [cols[0]] * filters_cnt
        col_cnt = filters_cnt

    if filters_cnt == col_cnt:
        d = zip(cols, filters)
        df = df_from_csv_file(args.calls)
        for col, regex in d:
            df = df_regex_filter(df, col, regex)

        if args.out:
            out = args.out
        else:
            filename = os.path.basename(args.calls)
            path = os.path.dirname(args.calls)
            out = os.path.join(path, "filtered_" + filename)

        df_to_csv_file(df, out)
