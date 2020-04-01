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
BADFIXCOMMON = TESTS_DIR / ".." / "badfixcommon.py"


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
    cmd = [BADFIXCOMMON, "-h"]
    assert subprocess.run(cmd).returncode == 0


def test_badfixcommon_basic(set_up_test_data):
    """
    Test badfixcommon.py runs correctly
    """

    # First, run badfixstats.py to generate two test databases
    db1 = TEST_DATA_DIR / "badfixstats_out.csv"
    gitdir = TEST_DATA_DIR / "stable_4.19.2"
    cmd = [BADFIXSTATS,
           "--git-dir", gitdir,
           "--out", db1,
           "--no-merge-datapoints",
           "v4.19^..v4.19.1"]
    print(cmd)
    assert subprocess.run(cmd).returncode == 0
    assert db1.exists()

    db2 = TEST_DATA_DIR / "badfixstats_out.csv"
    gitdir = TEST_DATA_DIR / "stable_4.19.2"
    cmd = [BADFIXSTATS,
           "--git-dir", gitdir,
           "--out", db2,
           "--no-merge-datapoints",
           "v4.19^..v4.19.2"]
    print(cmd)
    assert subprocess.run(cmd).returncode == 0
    assert db2.exists()

    # Then, run the badfixcommon.py using the generated databases
    outname = TEST_DATA_DIR / "badfixcommon_out__"
    cmd = [BADFIXCOMMON,
           "--out", outname,
           db1,
           db2,
           ]
    print(cmd)
    assert subprocess.run(cmd).returncode == 0
    assert Path("%scommon.csv" % outname).exists()
    assert Path("%scsv1_unique.csv" % outname).exists()
    assert Path("%scsv2_unique.csv" % outname).exists()
    assert Path("%smerged.csv" % outname).exists()

    # 'db2' and 'merged' should have the same commits. We simply
    # check here that both have the same number of commits
    df_db2 = df_from_csv_file(db2)
    df_db2 = df_db2[['Commit_hexsha']].drop_duplicates()
    df_db2 = df_db2[df_db2['Commit_hexsha'].notnull()]
    df_merged = df_from_csv_file(Path("%smerged.csv" % outname))
    df_merged = df_merged[['Commit_hexsha']].drop_duplicates()
    df_merged = df_merged[df_merged['Commit_hexsha'].notnull()]
    assert df_db2.shape[0] == df_merged.shape[0]


def test_badfixcommon_self(set_up_test_data):
    """
    Test badfixcommon.py generates expected output when input databases
    are the same
    """

    # First, run badfixstats.py to generate a test database
    db1 = TEST_DATA_DIR / "badfixstats_out.csv"
    gitdir = TEST_DATA_DIR / "stable_4.19.2"
    cmd = [BADFIXSTATS,
           "--git-dir", gitdir,
           "--out", db1,
           "--no-merge-datapoints",
           "v4.19^..v4.19.1"]
    print(cmd)
    assert subprocess.run(cmd).returncode == 0
    assert db1.exists()

    # Then, run the badfixcommon.py using the generated database
    outname = TEST_DATA_DIR / "badfixcommon_out__"
    cmd = [BADFIXCOMMON,
           "--out", outname,
           db1,
           db1,
           ]
    print(cmd)
    assert subprocess.run(cmd).returncode == 0
    assert Path("%scommon.csv" % outname).exists()
    assert Path("%scsv1_unique.csv" % outname).exists()
    assert Path("%scsv2_unique.csv" % outname).exists()
    assert Path("%smerged.csv" % outname).exists()

    # There should be unique commits in either
    df_csv1 = df_from_csv_file(Path("%scsv1_unique.csv" % outname))
    df_csv2 = df_from_csv_file(Path("%scsv2_unique.csv" % outname))
    assert df_csv1.shape[0] == 0
    assert df_csv2.shape[0] == 0


if __name__ == '__main__':
    pytest.main([__file__])
