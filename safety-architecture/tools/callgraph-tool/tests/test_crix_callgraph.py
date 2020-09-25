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
import test_utils

################################################################################


TESTS_DIR = Path(os.path.dirname(os.path.realpath(__file__)))
TEST_RESOURCES_DIR = TESTS_DIR / "resources" / "crix-callgraph"
TEST_DATA_DIR = TESTS_DIR / "crix_callgraph_test_data"
CG_BIN = TESTS_DIR / ".." / "build" / "lib" / "crix-callgraph"
BC_GENERATE = TEST_RESOURCES_DIR / "generate_bitcodes.sh"
EXPECTED = TEST_RESOURCES_DIR / "expected_calls.csv"


################################################################################


@pytest.fixture(scope="session", autouse=True)
def set_up_session_test_data(request):
    # Run once at the start of test session, before any tests have been run
    print("session setup")
    request.addfinalizer(clean_up_session_test_data)
    assert Path(CG_BIN).exists()
    # Generate target bitcode files
    assert Path(BC_GENERATE).exists()
    cmd = [BC_GENERATE]
    assert subprocess.run(cmd).returncode == 0
    os.chdir(TEST_RESOURCES_DIR)


def clean_up_session_test_data():
    print("session cleanup")
    os.chdir(TEST_RESOURCES_DIR)
    cmd = ["make", "clean"]
    assert subprocess.run(cmd).returncode == 0


@pytest.fixture()
def set_up_test_data():
    print("test setup")
    shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)
    os.makedirs(TEST_DATA_DIR)
    yield "resource"
    print("test clean up")
    shutil.rmtree(TEST_DATA_DIR)


def df_regex_filter(df, col, regex):
    return df[df[col].str.contains(regex, regex=True, na=False)]


def check_function_calls_from(target_bclist_file_name):
    target_bclist_file = TEST_RESOURCES_DIR / target_bclist_file_name
    assert Path(target_bclist_file).exists()

    # Generate calls.csv file from target_bclist_file
    outfile = TEST_DATA_DIR / "calls.csv"
    cmd = [CG_BIN,
           "-o", outfile,
           "@%s" % target_bclist_file,
           ]
    assert subprocess.run(cmd).returncode == 0
    assert Path(outfile).exists()

    # Check the generated contents matches expected
    assert EXPECTED.exists()
    df_expected = pd.read_csv(EXPECTED)
    caller_regex = "^%s" % os.path.splitext(target_bclist_file_name)[0]
    df_expected = df_regex_filter(df_expected, "caller_filename", caller_regex)
    df_generated = pd.read_csv(outfile)
    df_diff = test_utils.df_difference(df_expected, df_generated)
    assert df_diff.empty, test_utils.df_to_string(df_diff)


def test_help():
    cmd = [CG_BIN, "-h"]
    assert subprocess.run(cmd).returncode == 0


def test_cg_test_template(set_up_test_data):
    check_function_calls_from("cg-test-template.bclist")


def test_mlta(set_up_test_data):
    check_function_calls_from("test-mlta.bclist")


def test_opt(set_up_test_data):
    check_function_calls_from("test-opt.bclist")


def test_inline(set_up_test_data):
    check_function_calls_from("test-inline.bclist")


def test_asminline(set_up_test_data):
    check_function_calls_from("test-asminline.bclist")


def test_cast_struct(set_up_test_data):
    check_function_calls_from("test-cast-struct.bclist")


def test_cast_fptr(set_up_test_data):
    check_function_calls_from("test-cast-fptr.bclist")


def test_bitfield(set_up_test_data):
    check_function_calls_from("test-bitfield.bclist")


def test_escape(set_up_test_data):
    check_function_calls_from("test-escape.bclist")


def test_sizeof(set_up_test_data):
    check_function_calls_from("test-sizeof.bclist")


################################################################################
