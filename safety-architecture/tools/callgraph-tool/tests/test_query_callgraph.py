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
TEST_RESOURCES_DIR = TESTS_DIR / "resources" / "query-callgraph"
TEST_DATA_DIR = TESTS_DIR / "query_callgraph_test_data"
CG_BIN = TESTS_DIR / ".." / "build" / "lib" / "crix-callgraph"
QUERY_CG = TESTS_DIR / ".." / "scripts" / "query_callgraph.py"
BC_GENERATE = TEST_RESOURCES_DIR / "generate_bitcodes.sh"
EXPECTED = TEST_RESOURCES_DIR / "expected_calls.csv"

################################################################################


@pytest.fixture(scope="session", autouse=True)
def set_up_session_test_data(request):
    # Run once at the start of test session, before any tests have been run
    print("session setup")
    request.addfinalizer(clean_up_session_test_data)
    assert Path(QUERY_CG).exists()
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


def test_help():
    cmd = [QUERY_CG, "-h"]
    assert subprocess.run(cmd).returncode == 0


def test_png_graph(set_up_test_data):
    callgraph_csv = TEST_DATA_DIR / "calls.csv"
    generate_call_graph_from("test-chain.bclist", callgraph_csv)
    query_out = TEST_DATA_DIR / "graph.png"

    cmd = [
        QUERY_CG,
        "--csv", callgraph_csv,
        "--caller_function", "main",
        "--depth", "10",
        "--out", query_out
    ]

    assert subprocess.run(cmd).returncode == 0
    assert Path(query_out).exists()
    # Check the output is valid png file
    assert imghdr.what(query_out) == 'png'


def test_png_graph_edge_labels(set_up_test_data):
    callgraph_csv = TEST_DATA_DIR / "calls.csv"
    generate_call_graph_from("test-chain.bclist", callgraph_csv)
    query_out = TEST_DATA_DIR / "graph.png"

    cmd = [
        QUERY_CG,
        "--csv", callgraph_csv,
        "--caller_function", "main",
        "--depth", "10",
        "--edge_labels",
        "--out", query_out
    ]

    assert subprocess.run(cmd).returncode == 0
    assert Path(query_out).exists()
    # Check the output is valid png file
    assert imghdr.what(query_out) == 'png'


def test_csv_graph(set_up_test_data):
    callgraph_csv = TEST_DATA_DIR / "calls.csv"
    generate_call_graph_from("test-chain.bclist", callgraph_csv)
    query_out = TEST_DATA_DIR / "graph.csv"

    cmd = [
        QUERY_CG,
        "--csv", callgraph_csv,
        "--caller_function", "main",
        "--depth", "10",
        "--out", query_out
    ]

    assert subprocess.run(cmd).returncode == 0
    assert Path(query_out).exists()
    # Check the output is valid csv
    df_generated = pd.read_csv(query_out)
    assert not df_generated.empty


def test_csv_graph_inverse(set_up_test_data):
    callgraph_csv = TEST_DATA_DIR / "calls.csv"
    generate_call_graph_from("test-chain.bclist", callgraph_csv)

    query_out = TEST_DATA_DIR / "graph.csv"
    cmd = [
        QUERY_CG,
        "--csv", callgraph_csv,
        "--caller_function", "main",
        "--depth", "10",
        "--out", query_out
    ]
    assert subprocess.run(cmd).returncode == 0
    assert Path(query_out).exists()

    query_out_inverse = TEST_DATA_DIR / "graph_inverse.csv"
    cmd = [
        QUERY_CG,
        "--csv", callgraph_csv,
        "--caller_function", "say_hello",
        "--depth", "10",
        "--inverse",
        "--out", query_out_inverse
    ]

    assert subprocess.run(cmd).returncode == 0
    assert Path(query_out_inverse).exists()

    # When 'depth' covers the entire callgraph, the output from
    # the two above commands should be the same, except for column
    # 'call_depth': below, we remove that column from both outputs and
    # compare the two dataframes

    df_csv = pd.read_csv(query_out)
    assert not df_csv.empty
    df_csv = df_csv.drop('call_depth', 1)
    df_csv = df_csv.sort_values(by=['caller_line'])

    df_csv_inv = pd.read_csv(query_out_inverse)
    assert not df_csv_inv.empty
    df_csv_inv = df_csv_inv.drop('call_depth', 1)
    df_csv_inv = df_csv_inv.sort_values(by=['caller_line'])

    df_diff = test_utils.df_difference(df_csv, df_csv_inv)
    assert df_diff.empty, test_utils.df_to_string(df_diff)


################################################################################
