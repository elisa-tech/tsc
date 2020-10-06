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


def syzkaller_calculate_cov(df_cov, project_root=None):
    require_cols = ['filename', 'function', "covered pcs", "total pcs"]
    df_cov.columns = df_cov.columns.str.lower()
    if not all(x in list(df_cov.columns.values) for x in require_cols):
        _LOGGER.error(
                "Coverage file missing required headers: %s" % require_cols)
        exit(1)
    df_cov['percent'] = (df_cov['covered pcs'] * 100) / df_cov['total pcs']
    if project_root:
        # TODO: append path separator if does not exist
        df_cov['filename'] = df_cov['filename'].str.replace(project_root, "")
    return df_cov


def getargs():
    desc = "Convert the input coverage file into format suitable for CallGraph tool usage"
    epil = "Example: ./%s --format syzkaller "\
        "--coverage coverage.input --out coverage.csv" % \
        os.path.basename(__file__)

    parser = argparse.ArgumentParser(description=desc, epilog=epil)

    help = "Path to source root. Specify if you want paths in coverage data to be stored"\
        " relative to the project root"
    parser.add_argument("--project_root", help=help, default="")
    help = "Format of the coverage input file"
    parser.add_argument("--format", help=help, required=True, choices=["syzkaller"])
    help = "File with coverage data in specified format"
    parser.add_argument("--coverage", help=help, required=True)
    help = "Output file where data in CallGraph tool format will be exported"
    parser.add_argument('--out', help=help, required=True)
    help = "Set the verbosity level (e.g. -vv for debug level)"
    parser.add_argument(
        '-v', '--verbose', help=help, action='count', default=1)
    return parser.parse_args()


if __name__ == '__main__':
    args = getargs()

    utils.exit_unless_accessible(args.coverage)
    utils.setup_logging(verbosity=args.verbose)

    if args.format == "syzkaller":
        df = df_from_csv_file(args.coverage)
        df = syzkaller_calculate_cov(df, args.project_root)
        df_to_csv_file(df, args.out)
