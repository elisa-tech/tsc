# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import subprocess
import os
import sys
import pytest
import shutil
import csv
from pathlib import Path
import pandas as pd

################################################################################

TESTS_DIR = Path(os.path.dirname(os.path.realpath(__file__)))
TEST_DATA_DIR = TESTS_DIR / "find_coverage_gaps_test_data"
TEST_RESOURCES_DIR = TESTS_DIR / "resources" / "find_coverage_gaps"
TEST_DATA_TAR = TEST_RESOURCES_DIR / "find_coverage_gaps_test_data.tar.bz2"
FIND_GAPS = TESTS_DIR / ".." / "scripts" / "find_coverage_gaps.py"

################################################################################


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
    cmd = [FIND_GAPS, "-h"]
    assert subprocess.run(cmd).returncode == 0


def test_find_gaps_basic(set_up_test_data):
    calls = TEST_DATA_DIR / "calls.csv"
    coverage = TEST_DATA_DIR / "coverage.csv"
    outfile = TEST_DATA_DIR / "gaps.csv"
    regex = "main"
    cmd = [
        FIND_GAPS,
        "--calls", calls,
        "--coverage", coverage,
        "--out", outfile,
        "--caller_function_regex", regex
    ]
    assert Path(calls).exists()
    assert Path(coverage).exists()
    assert subprocess.run(cmd).returncode == 0
    assert Path(outfile).exists()
    df = pd.read_csv(outfile)
    assert df.shape[0] > 1
    required_cols = ['call_stack', 'callee_coverage_gap']
    missing_cols = all(x in list(df.columns.values) for x in required_cols)
    assert missing_cols, "Missing expected columns: %s" % required_cols


def test_find_gaps_no_regex_matches(set_up_test_data):
    calls = TEST_DATA_DIR / "calls.csv"
    coverage = TEST_DATA_DIR / "coverage.csv"
    outfile = TEST_DATA_DIR / "gaps.csv"
    regex = "foobar"
    cmd = [
        FIND_GAPS,
        "--calls", calls,
        "--coverage", coverage,
        "--out", outfile,
        "--caller_function_regex", regex
    ]
    assert Path(calls).exists()
    assert Path(coverage).exists()
    assert subprocess.run(cmd).returncode == 0
    assert Path(outfile).exists()
    df = pd.read_csv(outfile)
    assert df.shape[0] == 0
    required_cols = ['call_stack', 'callee_coverage_gap']
    missing_cols = all(x in list(df.columns.values) for x in required_cols)
    assert missing_cols, "Missing expected columns: %s" % required_cols


def test_find_gaps_missing_func(set_up_test_data):
    calls = TEST_DATA_DIR / "calls.csv"
    coverage = TEST_DATA_DIR / "coverage.csv"
    outfile = TEST_DATA_DIR / "gaps.csv"
    regex = "missing_caller"
    cmd = [
        FIND_GAPS,
        "--calls", calls,
        "--coverage", coverage,
        "--out", outfile,
        "--caller_function_regex", regex
    ]
    assert Path(calls).exists()
    assert Path(coverage).exists()
    assert subprocess.run(cmd).returncode == 0
    assert Path(outfile).exists()
    df = pd.read_csv(outfile)
    assert df.shape[0] > 1
    required_cols = ['call_stack', 'callee_coverage_gap']
    missing_cols = all(x in list(df.columns.values) for x in required_cols)
    assert missing_cols, "Missing expected columns: %s" % required_cols


def test_find_gaps_err_invalid_cov(set_up_test_data):
    calls = TEST_DATA_DIR / "calls.csv"
    coverage = TEST_DATA_DIR / "coverage_foo.csv"
    outfile = TEST_DATA_DIR / "gaps.csv"
    regex = "main"
    cmd = [
        FIND_GAPS,
        "--calls", calls,
        "--coverage", coverage,
        "--out", outfile,
        "--caller_function_regex", regex
    ]
    assert Path(calls).exists()
    assert not Path(coverage).exists()
    assert subprocess.run(cmd).returncode == 1


def test_find_gaps_err_invalid_calls(set_up_test_data):
    calls = TEST_DATA_DIR / "calls_foo.csv"
    coverage = TEST_DATA_DIR / "coverage.csv"
    outfile = TEST_DATA_DIR / "gaps.csv"
    regex = "main"
    cmd = [
        FIND_GAPS,
        "--calls", calls,
        "--coverage", coverage,
        "--out", outfile,
        "--caller_function_regex", regex
    ]
    assert not Path(calls).exists()
    assert Path(coverage).exists()
    assert subprocess.run(cmd).returncode == 1


def test_find_gaps_err_invalid_maxdepth(set_up_test_data):
    calls = TEST_DATA_DIR / "calls.csv"
    coverage = TEST_DATA_DIR / "coverage.csv"
    outfile = TEST_DATA_DIR / "gaps.csv"
    regex = "main"
    cmd = [
        FIND_GAPS,
        "--calls", calls,
        "--coverage", coverage,
        "--out", outfile,
        "--caller_function_regex", regex,
        "--maxdepth", "0"
    ]
    assert Path(calls).exists()
    assert Path(coverage).exists()
    assert subprocess.run(cmd).returncode == 2


def test_find_gaps_err_cov_header(set_up_test_data):
    calls = TEST_DATA_DIR / "calls.csv"
    coverage = TEST_DATA_DIR / "coverage_err_header.csv"
    outfile = TEST_DATA_DIR / "gaps.csv"
    regex = "main"
    cmd = [
        FIND_GAPS,
        "--calls", calls,
        "--coverage", coverage,
        "--out", outfile,
        "--caller_function_regex", regex
    ]
    assert Path(calls).exists()
    assert Path(coverage).exists()
    assert subprocess.run(cmd).returncode == 1


def test_find_gaps_err_calls_header(set_up_test_data):
    calls = TEST_DATA_DIR / "calls_err_header.csv"
    coverage = TEST_DATA_DIR / "coverage.csv"
    outfile = TEST_DATA_DIR / "gaps.csv"
    regex = "main"
    cmd = [
        FIND_GAPS,
        "--calls", calls,
        "--coverage", coverage,
        "--out", outfile,
        "--caller_function_regex", regex
    ]
    assert Path(calls).exists()
    assert Path(coverage).exists()
    assert subprocess.run(cmd).returncode == 1


################################################################################

if __name__ == '__main__':
    pytest.main([__file__])

################################################################################
