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
BADFIXPLOT = TESTS_DIR / ".." / "badfixplot.py"
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


def test_help():
    """
    Test help
    """
    cmd = [BADFIXPLOT, "-h"]
    assert subprocess.run(cmd).returncode == 0


def test_badfixplot_basic(set_up_test_data):
    """
    Test badfixplot.py runs correctly
    """

    # First, run badfixstats.py to generate the database
    outfile = TEST_DATA_DIR / "badfixstats_out.csv"
    gitdir = TEST_DATA_DIR / "stable_4.19.2"
    cmd = [BADFIXSTATS,
           "--git-dir", gitdir,
           "--out", outfile,
           "--no-merge-datapoints",
           "v4.19^..v4.19.2"]
    print(cmd)
    assert subprocess.run(cmd).returncode == 0
    assert outfile.exists()

    # Then, run the badfixplot.py using the generated database
    infile = outfile
    outfile = TEST_DATA_DIR / "badfixplot_out"
    cmd = [BADFIXPLOT,
           "--out", outfile,
           infile]
    print(cmd)
    assert subprocess.run(cmd).returncode == 0

    # Check some html files got generated
    assert Path("%s__summary.html" % outfile).exists()
    assert Path("%s__absolute_number_of_commits.html" % outfile).exists()


def test_badfixplot_num_commits(set_up_test_data):
    """
    Test badfixplot.py runs generates expected output
    """

    # First, run badfixstats.py to generate the database
    outfile = TEST_DATA_DIR / "badfixstats_out.csv"
    gitdir = TEST_DATA_DIR / "stable_4.19.2"
    cmd = [BADFIXSTATS,
           "--git-dir", gitdir,
           "--out", outfile,
           "--no-merge-datapoints",
           "v4.19.1..v4.19.2"]
    print(cmd)
    assert subprocess.run(cmd).returncode == 0
    assert outfile.exists()

    # Then, run the badfixplot.py using the generated database
    infile = outfile
    outfile = TEST_DATA_DIR / "badfixplot_out"
    cmd = [BADFIXPLOT,
           "--out", outfile,
           "--include_plotlyjs", "cdn",
           infile]
    print(cmd)
    assert subprocess.run(cmd).returncode == 0

    # Check some html files got generated
    assert Path("%s__summary.html" % outfile).exists()
    assert Path("%s__absolute_number_of_commits.html" % outfile).exists()

    # Sanity check the generated js:
    # There should be exactly 362 commits in v4.19.2
    absfile = Path("%s__absolute_number_of_commits.html" % outfile)
    re_commits = re.compile(r'Commits: (?P<days>\d+)')
    commits = None
    with open(absfile, 'r') as f:
        for line in f:
            match = re_commits.search(line)
            if match:
                commits = match.group('days')
                break
    assert int(commits) == 362


def test_badfixplot_none(set_up_test_data):
    """
    Test badfixstats.py with a badfixdb with no badfixes
    """

    # First, run badfixstats.py to generate the database
    outfile = TEST_DATA_DIR / "badfixstats_out.csv"
    gitdir = TEST_DATA_DIR / "stable_4.19.2"
    cmd = [BADFIXSTATS,
           "--git-dir", gitdir,
           "--out", outfile,
           "--no-merge-datapoints",
           "v4.19^..v4.19"]
    print(cmd)
    assert subprocess.run(cmd).returncode == 0
    assert outfile.exists()

    # Then, run the badfixplot.py using the generated database
    infile = outfile
    outfile = TEST_DATA_DIR / "badfixplot_out"
    cmd = [BADFIXPLOT,
           "--out", outfile,
           "--include_plotlyjs", "cdn",
           infile]
    print(cmd)
    assert subprocess.run(cmd).returncode == 0

    # Check some html files got generated
    assert Path("%s__summary.html" % outfile).exists()
    assert Path("%s__absolute_number_of_commits.html" % outfile).exists()


if __name__ == '__main__':
    pytest.main([__file__])
