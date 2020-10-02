#!/usr/bin/env python3

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
import imghdr
import test_utils

################################################################################

TESTS_DIR = Path(os.path.dirname(os.path.realpath(__file__)))
TEST_RESOURCES_DIR = TESTS_DIR / "resources" / "filter"
TEST_DATA_DIR = TESTS_DIR / "filter_callgraph_test_data"
FILTER_CG = TESTS_DIR / ".." / "scripts" / "filter_callgraph.py"
CALLGRAPH_CSV = TEST_RESOURCES_DIR / "calls.csv"
EXPECT_ONE_COL_ONE_FILTER = TEST_RESOURCES_DIR / "expect_one_col_one_filter.csv"
EXPECT_ONE_COL_MULT_FILTER = TEST_RESOURCES_DIR / "expect_one_col_mult_filter.csv"
EXPECT_MULT_COL_ONE_FILTER = TEST_RESOURCES_DIR / "expect_mult_col_one_filter.csv"
EXPECT_MULT_COL_MULT_FILTER = TEST_RESOURCES_DIR / "expect_mult_col_mult_filter.csv"

################################################################################


@pytest.fixture(scope="session", autouse=True)
def set_up_session_test_data(request):
    # Run once at the start of test session, before any tests have been run
    print("session setup")
    request.addfinalizer(clean_up_session_test_data)
    assert Path(FILTER_CG).exists()
    # Generate target bitcode files
    cmd = ["mkdir", "-p", TEST_DATA_DIR]
    assert subprocess.run(cmd).returncode == 0


def clean_up_session_test_data():
    print("session cleanup")
    cmd = ["rm", "-rf", TEST_DATA_DIR]
    assert subprocess.run(cmd).returncode == 0


@pytest.fixture()
def set_up_test_data():
    print("test setup")
    shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)
    os.makedirs(TEST_DATA_DIR)
    yield "resource"
    print("test clean up")
    shutil.rmtree(TEST_DATA_DIR)


def test_one_col_one_filter(set_up_test_data):
    filter_out = TEST_DATA_DIR / "one_col_one_filter_calls.csv"
    cmd = [
        FILTER_CG,
        "--cols", "indirect_found_with",
        "--filters", "TA$",
        "--out", filter_out,
        "--calls", CALLGRAPH_CSV
    ]
    assert subprocess.run(cmd).returncode == 0
    assert Path(filter_out).exists()
    cmd = ["diff", filter_out, EXPECT_ONE_COL_ONE_FILTER]
    assert subprocess.run(cmd).returncode == 0


def test_one_col_mult_filter(set_up_test_data):
    filter_out = TEST_DATA_DIR / "one_col_mult_filter_calls.csv"
    cmd = [
        FILTER_CG,
        "--cols", "caller_filename",
        "--filters", "^mm", "^lib", "^include",
        "--out", filter_out,
        "--calls", CALLGRAPH_CSV
    ]
    assert subprocess.run(cmd).returncode == 0
    assert Path(filter_out).exists()
    cmd = ["diff", filter_out, EXPECT_ONE_COL_MULT_FILTER]
    assert subprocess.run(cmd).returncode == 0


def test_mult_col_one_filter(set_up_test_data):
    filter_out = TEST_DATA_DIR / "mult_col_one_filter_calls.csv"
    cmd = [
        FILTER_CG,
        "--cols", "caller_filename", "callee_filename",
        "--filters", "kernel",
        "--out", filter_out,
        "--calls", CALLGRAPH_CSV
    ]
    assert subprocess.run(cmd).returncode == 0
    assert Path(filter_out).exists()
    cmd = ["diff", filter_out, EXPECT_MULT_COL_ONE_FILTER]
    assert subprocess.run(cmd).returncode == 0


def test_mult_col_mult_filter(set_up_test_data):
    filter_out = TEST_DATA_DIR / "mult_col_mult_filter_calls.csv"
    cmd = [
        FILTER_CG,
        "--cols", "caller_function", "callee_filename",
        "--filters", "^__", "kernel",
        "--out", filter_out,
        "--calls", CALLGRAPH_CSV
    ]
    assert subprocess.run(cmd).returncode == 0
    assert Path(filter_out).exists()
    cmd = ["diff", filter_out, EXPECT_MULT_COL_MULT_FILTER]
    assert subprocess.run(cmd).returncode == 0


################################################################################
