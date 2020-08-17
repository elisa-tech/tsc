#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import csv
import os
import sys
import logging
import pandas as pd

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), 'clang_indexer')))
import utils  # noqa

_LOGGER = logging.getLogger(utils.LOGGER_NAME)

################################################################################


class CoverageGapFinder():
    def __init__(self, csv_calls, csv_coverage, maxdepth, outfile):
        self.df_calls = df_from_csv_file(csv_calls)
        self.df_cov = df_from_csv_file(csv_coverage)
        self.maxdepth = maxdepth
        self.outfilename = outfile
        self.csvwriter = utils.CsvWriter(self.outfilename)

        self.df_cov.columns = self.df_cov.columns.str.lower()
        require_cols = ['function', 'filename', 'percent']

        if not all(x in list(self.df_cov.columns.values) for x in require_cols):
            logging.error(
                "Coverage file '%s' missing required headers: %s" % (
                    args['coverage_file'], require_cols))
            exit()
        # TODO: is this needed?
        if self.df_cov.isnull().values.any():
            logging.error(
                "Empty values in coverage data: %s" % args['coverage_file'])
            exit()
        self._write_header()

    def find_coverage_gaps(self, regex):
        # Find nodes where 'caller_function' matches regex
        df = df_regex_filter(self.df_calls, 'caller_function', regex)

        for row in df.itertuples():
            self._find_coverage_gap_from_caller(
                caller=row,
                depth=0,
                call_stack="'%s'" % row.caller_function)
        _LOGGER.info("wrote: %s" % self.outfilename)

    def _find_coverage_gap_from_caller(self, caller, depth, call_stack):
        if depth >= self.maxdepth:
            _LOGGER.log(utils.LOG_SPAM, "maxdepth reached, returning")
            return
        if not caller.caller_function:
            _LOGGER.warn("Missing caller_function: %s" % caller)
            return
        if not caller.callee_function:
            _LOGGER.warn("Missing callee_function: %s" % caller)
            return

        # Find the caller coverage
        caller_cov = 0
        df_caller_cov = self._get_coverage(caller.caller_function)
        if df_caller_cov is not None:
            caller_cov = cov_to_number(df_caller_cov['percent'].iloc[0])

        # Find the callee coverage
        callee_cov = 0
        df_callee_cov = self._get_coverage(caller.callee_function)
        if df_callee_cov is not None:
            callee_cov = cov_to_number(df_callee_cov['percent'].iloc[0])

        # Update depth and call_stack
        depth += 1
        call_stack = "%s ==> '%s'" % (call_stack, caller.callee_function)

        # Output csv row if coverage dropped
        if callee_cov < caller_cov:
            self._to_csv_row(
                caller, caller_cov, callee_cov, depth, call_stack)

        # Find next nodes
        df = df_regex_filter(
            self.df_calls, 'caller_function', "^%s$" % caller.callee_function)
        for row in df.itertuples():
            self._find_coverage_gap_from_caller(
                caller=row,
                depth=depth,
                call_stack=call_stack)

    def _get_coverage(self, funcname):
        df_cov = self.df_cov[(
            self.df_cov['function'] == funcname)]
        if df_cov.shape[0] <= 0:
            _LOGGER.warn(
                "Missing coverage info for function: %s" % funcname)
            return None
        elif df_cov.shape[0] > 1:
            _LOGGER.warn(
                "Multiple coverage values for function: %s" % funcname)
        return df_cov.head(1)

    def _write_header(self):
        header = \
            [
                "caller_filename",
                "caller_function",
                "caller_coverage",
                "callee_filename",
                "callee_function",
                "callee_coverage",
                "coverage_drop",
                "call_depth",
                "call_stack",
            ]
        self.csvwriter.write_arr(header)

    def _to_csv_row(self, caller, caller_cov, callee_cov, depth, call_stack):
        row = \
            [
                caller.caller_filename,
                caller.caller_function,
                caller_cov,
                caller.callee_filename,
                caller.callee_function,
                callee_cov,
                caller_cov - callee_cov,
                depth,
                call_stack,
            ]
        self.csvwriter.write_arr(row)

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
    return df[df[column].str.contains(regex, regex=True, na=False)]


def check_positive(val):
    intval = int(val)
    if intval <= 0:
        raise argparse.ArgumentTypeError("%s is not positive integer" % val)
    return intval


def cov_to_number(s):
    try:
        val = float(s)
        return 0 if pd.isna(val) else val
    except ValueError:
        return 0


def getargs():
    desc = "Find coverage gaps based on function call csv database "\
        "(CALLS) and function coverage file (COVERAGE)."

    epil = "Example: ./%s --calls calls.csv --coverage coverage.csv "\
        "--caller_function_regex "\
        "'^__x64_sys_' --maxdepth 4" % \
        os.path.basename(__file__)
    parser = argparse.ArgumentParser(description=desc, epilog=epil)

    required_named = parser.add_argument_group('required named arguments')
    help = "function call database csv file"
    required_named.add_argument('--calls', help=help, required=True)
    help = "function coverage file"
    required_named.add_argument('--coverage', help=help, required=True)
    help = "filter by caller_function (regular expression)"
    required_named.add_argument(
        '--caller_function_regex', help=help, required=True)

    help = "set the maxdepth, defaults to 3"
    parser.add_argument(
        '--maxdepth', nargs='?', help=help, type=check_positive, default=3)
    help = "Set the verbosity level (e.g. -vv for debug level)"
    parser.add_argument(
        '-v', '--verbose', help=help, action='count', default=0)
    help = "Set the output file name, default is 'coverage_drops.csv'"
    parser.add_argument(
        '--out', nargs='?', help=help, default='coverage_drops.csv')
    return parser.parse_args()


################################################################################


if __name__ == "__main__":
    args = getargs()

    utils.exit_unless_accessible(args.calls)
    utils.exit_unless_accessible(args.coverage)
    utils.setup_logging(verbosity=args.verbose)

    _LOGGER.info("reading input")
    cov = CoverageGapFinder(
        csv_calls=args.calls,
        csv_coverage=args.coverage,
        maxdepth=args.maxdepth,
        outfile=args.out)
    cov.find_coverage_gaps(args.caller_function_regex)

################################################################################
