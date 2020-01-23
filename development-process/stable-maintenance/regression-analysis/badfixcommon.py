#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2019 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: GPL-2.0-only

import argparse
import csv
import os
import sys

import pandas as pd
from tabulate import tabulate

################################################################################


class CommonStats:
    def __init__(self, outprefix, csv_file1, csv_file2):
        self.df_csv1 = self._from_csv_file(csv_file1)
        self.df_csv2 = self._from_csv_file(csv_file2)
        self.csv1_name = "%scsv1_unique.csv" % outprefix
        self.csv2_name = "%scsv2_unique.csv" % outprefix
        self.common_name = "%scommon.csv" % outprefix
        self.merged_name = "%smerged.csv" % outprefix
        self.csv_file1 = csv_file1
        self.csv_file2 = csv_file2
        self.list_uniq1 = []
        self.list_common = []
        self.df_uniq1 = None
        self.df_uniq2 = None
        self.df_common = None
        self.df_merged = None
        self._categorize()
        self._create_merged()

    def _from_csv_file(self, name):
        df = pd.read_csv(name, na_values=['None'], keep_default_na=True)
        df[['Badfix_datetime', 'Commit_datetime']] = \
            df[['Badfix_datetime', 'Commit_datetime']].apply(pd.to_datetime, utc=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def _to_csv_file(self, df, name):
        df.to_csv(
            path_or_buf=name,
            quoting=csv.QUOTE_ALL,
            sep=",", index=False, encoding='utf-8')
        print("[+] Wrote: %s" % name)

    def to_csv(self):
        self._to_csv_file(self.df_uniq1, self.csv1_name)
        self._to_csv_file(self.df_uniq2, self.csv2_name)
        self._to_csv_file(self.df_common, self.common_name)
        self._to_csv_file(self.df_merged, self.merged_name)

    def print_table(self):
        df = self.df_uniq1
        uniq_regrs1 = 0
        uniq_commits1 = df.shape[0]
        if uniq_commits1 > 0:
            uniq_regrs1 = df[df['Badfix_hexsha'].notnull()].shape[0]

        df = self.df_uniq2
        uniq_regrs2 = 0
        uniq_commits2 = df.shape[0]
        if uniq_commits2 > 0:
            uniq_regrs2 = df[df['Badfix_hexsha'].notnull()].shape[0]

        df = self.df_common
        uniq_regrs_common = 0
        uniq_commits_common = df.shape[0]
        if uniq_commits_common > 0:
            uniq_regrs_common1 = df[df['Badfix_hexsha__1'].notnull()].shape[0]
            uniq_regrs_common2 = df[df['Badfix_hexsha__2'].notnull()].shape[0]
            uniq_regrs_common = \
                df[(
                    df['Badfix_hexsha__1'].notnull() & df['Badfix_hexsha__2'].notnull()
                )].shape[0]

        df = self.df_merged
        uniq_regrs_merged = 0
        uniq_commits_merged = df.shape[0]
        if uniq_commits_merged > 0:
            uniq_regrs_merged = df[df['Badfix_hexsha'].notnull()].shape[0]

        orig_commits_csv1 = uniq_commits1 + uniq_commits_common
        orig_regrs_csv1 = uniq_regrs1 + uniq_regrs_common1
        orig_commits_csv2 = uniq_commits2 + uniq_commits_common
        orig_regrs_csv2 = uniq_regrs2 + uniq_regrs_common2

        table = []
        headers = ['File', 'Explanation', 'Commits', 'Regressions']
        table.append([self.csv_file1, "In: CSV1", orig_commits_csv1, orig_regrs_csv1])
        table.append([self.csv_file2, "In: CSV2", orig_commits_csv2, orig_regrs_csv2])
        table.append([self.csv1_name, "Out: unique in CSV1", uniq_commits1, uniq_regrs1])
        table.append([self.csv2_name, "Out: unique in CSV2", uniq_commits2, uniq_regrs2])
        table.append([self.common_name, "Out: common", uniq_commits_common, uniq_regrs_common])
        table.append([self.merged_name, "Out: merged", uniq_commits_merged, uniq_regrs_merged])
        print("[+] Overlap summary:")
        print(tabulate(table, headers, tablefmt="fancy_grid"))

    def _create_merged(self):
        # Merged commits are the combination of unique commits from
        # the below three categories:
        # (1) Commits that are unique in csv1 (self.df_uniq1)
        # (2) Commits that are unique in csv2 (self.df_uniq2)
        # (3) Commits that are common (self.df_common)

        # (1) and (2): simply concat the commits from df_uniq1 and df_uniq2
        df_concat = [self.df_uniq1, self.df_uniq2]
        # (3): For the common commits, the following cases need to be handled
        # separately:
        #   (a) not a regression in either branch
        #   (b) regression in branch1 but not in branch2
        #   (c) regression in branch2 but not in branch1
        #   (d) regression in branch1 and in branch2
        #   For (a) and (d): Use data from the branch where the commit first occurred

        a_d_idx = ~(self.df_common['Badfix_hexsha__1'].isnull() ^ self.df_common['Badfix_hexsha__2'].isnull())
        a_d_left = self.df_common[a_d_idx]['Commit_datetime__1'] < \
            self.df_common[a_d_idx]['Commit_datetime__2']
        a_d_right = ~a_d_left
        a_d_left_idx = a_d_left[a_d_left].index
        a_d_right_idx = a_d_right[a_d_right].index

        b_idx = self.df_common['Badfix_hexsha__1'].notnull() & self.df_common['Badfix_hexsha__2'].isnull()
        c_idx = self.df_common['Badfix_hexsha__1'].isnull() & self.df_common['Badfix_hexsha__2'].notnull()

        # [.., df_a_d_left, df_a_d_right, df_b, df_c]
        df_concat.append(self.df_common.iloc[a_d_left_idx].filter(like='__1'))
        df_concat.append(self.df_common.iloc[a_d_right_idx].filter(like='__2'))
        df_concat.append(self.df_common.loc[b_idx].filter(like='__1'))
        df_concat.append(self.df_common.loc[c_idx].filter(like='__2'))

        # Ensure all the dataframe have same column names
        columns = self.df_csv1.columns

        for df in df_concat:
            df.columns = columns
        self.df_merged = pd.concat(df_concat, axis=0, ignore_index=True)
        # Sort by "Commit_datetime" and "Commit_hexsha"
        self.df_merged.sort_values(by=['Commit_datetime', 'Commit_hexsha'], inplace=True)

    def _categorize(self):
        self.rows_left = []
        self.rows_right = []

        subset = ['Commit_upstream_hexsha', 'Badfix_upstream_hexsha',
                  'Commit_hexsha', 'Commit_summary', 'Commit_datetime']
        df_csv2 = pd.DataFrame(self.df_csv2, columns=subset)
        for idx, row in self.df_csv1.iterrows():
            commit_hexsha = row['Commit_hexsha']
            commit_upstream = row['Commit_upstream_hexsha']
            badfix_upstream = row['Badfix_upstream_hexsha']
            # Both commit_upstream and badfix_upstream are missing:
            if pd.isnull(badfix_upstream) and pd.isnull(commit_upstream):
                # ==> Use Commit_hexsha to find matches in csv2:
                col = 'Commit_hexsha'
                self._categorize_one(idx, row, df_csv2, col, commit_hexsha)
            # Badfix_upstream_hexsha is not missing:
            elif not pd.isnull(badfix_upstream) and pd.isnull(commit_upstream):
                # ==> Use Badfix_upstream_hexsha to find matches in csv2:
                col = 'Badfix_upstream_hexsha'
                self._categorize_one(idx, row, df_csv2, col, badfix_upstream)
            # Commit_upstream_hexsha is not missing
            elif not pd.isnull(commit_upstream):
                # ==> Use Commit_upstream_hexsha to find matches in csv2:
                col = 'Commit_upstream_hexsha'
                self._categorize_one(idx, row, df_csv2, col, commit_upstream)

        df_common1 = self.df_csv1.iloc[self.rows_left, :].reset_index(drop=True)
        df_common2 = self.df_csv2.iloc[self.rows_right, :].reset_index(drop=True)
        self.df_common = \
            pd.concat([df_common1.add_suffix('__1'), df_common2.add_suffix('__2')], axis=1)
        # Rows that are unique in csv1
        self.df_uniq1 = pd.DataFrame(self.list_uniq1, columns=self.df_csv1.columns)
        # Rows that are unique in csv2
        self.df_csv2.drop(index=self.rows_right, inplace=True)
        self.df_uniq2 = self.df_csv2

    def _categorize_one(self, idx, row, df_other, colname, val_self):
        df_common = df_other[df_other[colname] == val_self]
        matching_rows = df_common.shape[0]
        if matching_rows == 0:
            # No matches in df_other: value is unique in csv1
            self.list_uniq1.append(row)
            return
        elif matching_rows == 1:
            # One match in df_other: the match in df_common is the common row
            common_idx = df_common.index[0]
        elif matching_rows > 1:
            # Multiple matches: we need to determine the match based on
            # additional other criteria. First, filter matches based on
            # 'Commit_summary'
            summary = row['Commit_summary']
            df_summary = df_common[df_common['Commit_summary'] == summary]
            matching_summaries = df_summary.shape[0]
            if matching_summaries > 1:
                # Multiple matching summaries: select the common row based on
                # closest 'Commit_datetime'
                diff = abs(row['Commit_datetime'] - df_summary['Commit_datetime'])
                common_idx = diff.sort_values().index[0]
            elif matching_summaries == 1:
                common_idx = df_summary.index[0]
            elif matching_summaries == 0:
                raise ValueError('No matching commit summary')

        # Join common rows
        self.rows_left.append(idx)
        self.rows_right.append(common_idx)
        # Remove the found row from the 'other' csv
        df_other.drop(common_idx, 'rows', inplace=True)

################################################################################


def exit_unless_accessible(filename):
    if not os.path.isfile(filename):
        sys.stderr.write(
            "Error: file not found or no permissions: %s\n" % filename)
        sys.exit(1)


def getargs():
    desc = \
        "Generate output that describes the overlap between two branches, "\
        "based on CSV input from badfixstats.py. "\
        "Script determines the overlap based on upstream references. "\
        "In the script's output, \"common\" refers to commits or regressions "\
        "that occur in both input branches, "\
        "whereas, \"merged\" refers to commits "\
        "or regressions that are unique among all the commits in the two "\
        "branches."

    epil = "Example: ./%s linux_stable__v4.19.csv linux_stable__v4.14.csv" % \
        os.path.basename(__file__)
    parser = argparse.ArgumentParser(description=desc, epilog=epil)

    help = "CSV database for the first branch (output from badfixstats.py)"
    parser.add_argument('CSV1', nargs=1, help=help)

    help = "CSV database for the second branch (output from badfixstats.py)"
    parser.add_argument('CSV2', nargs=1, help=help)

    help = "set the output file name prefix"
    parser.add_argument('--out', nargs='?', help=help, default='')

    return parser.parse_args()

################################################################################


if __name__ == "__main__":
    args = getargs()
    csv_file1 = args.CSV1[0]
    csv_file2 = args.CSV2[0]
    outprefix = args.out

    if not outprefix:
        outprefix = ""

    exit_unless_accessible(csv_file1)
    exit_unless_accessible(csv_file2)

    print("[+] Reading input csv files, this might take a few minutes")
    stats = CommonStats(outprefix, csv_file1, csv_file2)
    stats.print_table()
    stats.to_csv()
