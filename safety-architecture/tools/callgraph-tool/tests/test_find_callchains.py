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
TEST_RESOURCES_DIR = TESTS_DIR / "resources" / "find_callchains"
TEST_DATA_DIR = TESTS_DIR / "find_callchains_test_data"
CG_BIN = TESTS_DIR / ".." / "build" / "lib" / "crix-callgraph"
QUERY_FC = TESTS_DIR / ".." / "scripts" / "find_callchains.py"
# BC_GENERATE = TEST_RESOURCES_DIR / "generate_bitcodes.sh"
# EXPECTED = TEST_RESOURCES_DIR / "expected_calls.csv"
CALLS_FILE = TEST_RESOURCES_DIR / "chain_calls.csv"
CALLS_FILE_DUPL = TEST_RESOURCES_DIR / "chain_calls_dupl.csv"

################################################################################


@pytest.fixture(scope="session", autouse=True)
def set_up_session_test_data(request):
    # Run once at the start of test session, before any tests have been run
    print("session setup")
    assert Path(QUERY_FC).exists()
    assert Path(CG_BIN).exists()
    # Generate target bitcode files
#    assert Path(BC_GENERATE).exists()
#    cmd = [BC_GENERATE]
#    assert subprocess.run(cmd).returncode == 0
    os.chdir(TEST_RESOURCES_DIR)


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


def test_help():
    cmd = [QUERY_FC, "-h"]
    assert subprocess.run(cmd).returncode == 0


def generate_call_graph_from(target_bclist_file_name, outfile):
    target_bclist_file = TEST_RESOURCES_DIR / target_bclist_file_name
    assert Path(target_bclist_file).exists()

    # Generate calls.csv file from target_bclist_file
    cmd = [CG_BIN,
           "-o", outfile,
           "@%s" % target_bclist_file,
           ]
    assert subprocess.run(cmd).returncode == 0
    assert Path(outfile).exists()


def test_no_from_function(set_up_test_data):
    cmd = [QUERY_FC,
           "--calls", CALLS_FILE,
           "--from_function", "chain4",
           "--to_function", "chain3"]
    assert subprocess.run(cmd).returncode == 1


def test_no_to_function(set_up_test_data):
    cmd = [QUERY_FC,
           "--calls", CALLS_FILE,
           "--from_function", "chain2",
           "--to_function", "chain5"]
    assert subprocess.run(cmd).returncode == 1


def test_single_chain_right(set_up_test_data):
    EXPECTED = TEST_RESOURCES_DIR / "expect_single_chain_right.csv"
    outfile = TEST_DATA_DIR / "single_chain_right.csv"
    cmd = [QUERY_FC,
           "--calls", CALLS_FILE,
           "--from_function", "chain1",
           "--to_function", "chain3",
           "--direction", "right",
           "--out", outfile]
    assert subprocess.run(cmd).returncode == 0
    assert EXPECTED.exists()
    df_expected = pd.read_csv(EXPECTED)
    df_generated = pd.read_csv(outfile)
    df_diff = test_utils.df_difference(df_expected, df_generated)
    assert df_diff.empty, test_utils.df_to_string(df_diff)


def test_single_chain_left(set_up_test_data):
    EXPECTED = TEST_RESOURCES_DIR / "expect_single_chain_left.csv"
    outfile = TEST_DATA_DIR / "single_chain_left.csv"
    cmd = [QUERY_FC,
           "--calls", CALLS_FILE,
           "--from_function", "chain3",
           "--to_function", "chain1",
           "--direction", "left",
           "--out", outfile]
    assert subprocess.run(cmd).returncode == 0
    assert EXPECTED.exists()
    df_expected = pd.read_csv(EXPECTED)
    df_generated = pd.read_csv(outfile)
    df_diff = test_utils.df_difference(df_expected, df_generated)
    assert df_diff.empty, test_utils.df_to_string(df_diff)


def test_single_link_both(set_up_test_data):
    EXPECTED = TEST_RESOURCES_DIR / "expect_single_chain_both.csv"
    outfile = TEST_DATA_DIR / "single_chain_both.csv"
    cmd = [QUERY_FC,
           "--calls", CALLS_FILE,
           "--from_function", "chain2",
           "--to_function", "^chain[0-9]$",
           "--direction", "both",
           "--out", outfile]
    assert subprocess.run(cmd).returncode == 0
    assert EXPECTED.exists()
    df_expected = pd.read_csv(EXPECTED)
    df_generated = pd.read_csv(outfile)
    df_diff = test_utils.df_difference(df_expected, df_generated)
    assert df_diff.empty, test_utils.df_to_string(df_diff)


def test_recursive_call(set_up_test_data):
    EXPECTED = TEST_RESOURCES_DIR / "expect_recursive_chains.csv"
    outfile = TEST_DATA_DIR / "recursive_chains.csv"
    cmd = [QUERY_FC,
           "--calls", CALLS_FILE,
           "--from_function", "recursive_call",
           "--to_function", "recursive_call",
           "--out", outfile]
    assert subprocess.run(cmd).returncode == 0
    assert EXPECTED.exists()
    df_expected = pd.read_csv(EXPECTED)
    df_generated = pd.read_csv(outfile)
    df_diff = test_utils.df_difference(df_expected, df_generated)
    assert df_diff.empty, test_utils.df_to_string(df_diff)


def test_from_function_with_fname(set_up_test_data):
    EXPECTED = TEST_RESOURCES_DIR / "expect_single_chain_right.csv"
    outfile = TEST_DATA_DIR / "single_chain_right.csv"
    cmd = [QUERY_FC,
           "--calls", CALLS_FILE,
           "--from_function", "test-chain.c:chain1",
           "--to_function", "chain3",
           "--direction", "right",
           "--out", outfile]
    assert subprocess.run(cmd).returncode == 0
    assert EXPECTED.exists()
    df_expected = pd.read_csv(EXPECTED)
    df_generated = pd.read_csv(outfile)
    df_diff = test_utils.df_difference(df_expected, df_generated)
    assert df_diff.empty, test_utils.df_to_string(df_diff)


def test_fname_misspelled(set_up_test_data):
    cmd = [QUERY_FC,
           "--calls", CALLS_FILE,
           "--from_function", "testchain.c:chain1",
           "--to_function", "chain3",
           "--direction", "right"]
    assert subprocess.run(cmd).returncode == 1


def test_function_ambiguous(set_up_test_data):
    cmd = [QUERY_FC,
           "--calls", CALLS_FILE_DUPL,
           "--from_function", "chain2",
           "--to_function", "chain[0-9]",
           "--direction", "both"]
    assert subprocess.run(cmd).returncode == 1


def test_function_specific(set_up_test_data):
    cmd = [QUERY_FC,
           "--calls", CALLS_FILE_DUPL,
           "--from_function", "test-chain.c:chain2",
           "--to_function", "chain[0-9]",
           "--direction", "both"]
    assert subprocess.run(cmd).returncode == 0

    EXPECTED = TEST_RESOURCES_DIR / "expect_function_filename_specific.csv"
    outfile = TEST_DATA_DIR / "function_filename_specific.csv"
    cmd = [QUERY_FC,
           "--calls", CALLS_FILE_DUPL,
           "--from_function", "test-chain-alt.c:chain2",
           "--to_function", "chain[0-9]",
           "--direction", "left",
           "--out", outfile]
    assert subprocess.run(cmd).returncode == 0
    assert EXPECTED.exists()
    df_expected = pd.read_csv(EXPECTED)
    df_generated = pd.read_csv(outfile)
    df_diff = test_utils.df_difference(df_expected, df_generated)
    assert df_diff.empty, test_utils.df_to_string(df_diff)


# def test_png_graph(set_up_test_data):
#    callgraph_csv = TEST_DATA_DIR / "calls.csv"
#    generate_call_graph_from("test-chain.bclist", callgraph_csv)
#    query_out = TEST_DATA_DIR / "graph.png"
#
#    cmd = [
#        QUERY_CG,
#        "--csv", callgraph_csv,
#        "--function", "main",
#        "--depth", "10",
#        "--out", query_out
#    ]
#
#    assert subprocess.run(cmd).returncode == 0
#    assert Path(query_out).exists()
#    # Check the output is valid png file
#    assert imghdr.what(query_out) == 'png'
#
#
################################################################################
