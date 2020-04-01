#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2019 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: GPL-2.0-only

"""
This file contains integration test cases for badfixstats.py
"""

import subprocess
import os
import sys
import pytest
import re
from pathlib import Path
import shutil
import pandas as pd

TESTS_DIR = Path(os.path.dirname(os.path.realpath(__file__)))
TEST_DATA_DIR = TESTS_DIR / "testdata"
TEST_DATA_TAR = TESTS_DIR / "testdata.tar.bz2"
BADFIXSTATS = TESTS_DIR / ".." / "badfixstats.py"


@pytest.fixture()
def set_up_test_data():
    print("setup")
    shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)
    assert subprocess.call(
        ["tar", "-xjf", TEST_DATA_TAR, "--directory", TESTS_DIR]) == 0
    yield "resource"
    print("clean up")
    shutil.rmtree(TEST_DATA_DIR)


def df_from_csv_file(name):
    df = pd.read_csv(name, na_values=['None'], keep_default_na=True)
    df.reset_index(drop=True, inplace=True)
    return df


def test_help():
    """
    Test help
    """
    cmd = [BADFIXSTATS, "-h"]
    assert subprocess.run(cmd).returncode == 0


def test_badfixstats_basic(set_up_test_data):
    """
    Test badfixstats.py runs correctly
    """
    outfile = TEST_DATA_DIR / "badfixstats_out.csv"
    gitdir = TEST_DATA_DIR / "stable_4.19.2"
    indexfile = TEST_DATA_DIR / "index.pickle"
    cmd = [BADFIXSTATS,
           "--git-dir", gitdir,
           "--out", outfile,
           "--index-file", indexfile,
           "v4.19^..v4.19.2"]
    print(cmd)
    assert subprocess.run(cmd).returncode == 0
    assert outfile.exists()

    # There should be exactly 3 badfixes in the specified range
    df = df_from_csv_file(outfile)
    df = df[['Badfix_hexsha']].drop_duplicates()
    df = df[df['Badfix_hexsha'].notnull()]
    assert df.shape[0] == 3


def test_badfixstats_no_badfixes(set_up_test_data):
    """
    Test badfixstats.py on a rev range with no badfixes
    """
    outfile = TEST_DATA_DIR / "badfixstats_out.csv"
    gitdir = TEST_DATA_DIR / "stable_4.19.2"
    indexfile = TEST_DATA_DIR / "index.pickle"
    cmd = [BADFIXSTATS,
           "--git-dir", gitdir,
           "--out", outfile,
           "--index-file", indexfile,
           "v4.19^..v4.19"]
    print(cmd)
    assert subprocess.run(cmd).returncode == 0
    assert outfile.exists()

    # There should be no badfixes in the specified range
    df = df_from_csv_file(outfile)
    df = df[['Badfix_hexsha']].drop_duplicates()
    df = df[df['Badfix_hexsha'].notnull()]
    assert df.shape[0] == 0


def test_badfixstats_no_merge_datapoints(set_up_test_data):
    """
    Test badfixstats.py with --no-merge-datapoints
    """
    outfile = TEST_DATA_DIR / "badfixstats_out.csv"
    gitdir = TEST_DATA_DIR / "stable_4.19.2"
    indexfile = TEST_DATA_DIR / "index.pickle"
    cmd = [BADFIXSTATS,
           "--git-dir", gitdir,
           "--out", outfile,
           "--index-file", indexfile,
           "--no-merge-datapoints",
           "v4.19^..v4.19.2"]
    print(cmd)
    assert subprocess.run(cmd).returncode == 0
    assert outfile.exists()

    # There should be exactly 3 badfixes in the specified range
    df = df_from_csv_file(outfile)
    df = df[['Badfix_hexsha']].drop_duplicates()
    df = df[df['Badfix_hexsha'].notnull()]
    assert df.shape[0] == 3


if __name__ == '__main__':
    pytest.main([__file__])
