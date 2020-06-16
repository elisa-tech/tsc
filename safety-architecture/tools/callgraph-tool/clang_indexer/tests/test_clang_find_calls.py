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
TEST_RESOURCES_DIR = TESTS_DIR / "resources"
TEST_DATA_DIR = TESTS_DIR / "clang_find_calls_test_data"
CLANG_FIND = TESTS_DIR / ".." / "clang_find_calls.py"
COMPDB_GENERATE = TEST_RESOURCES_DIR / "generate_compile_commands.sh"
COMPDB = TEST_RESOURCES_DIR / "compile_commands.json"
EXPECTED = TEST_RESOURCES_DIR / "expected_calls.csv"


################################################################################


def df_to_string(df):
    return \
        "\n" + \
        df.to_string(
            max_rows=None,
            max_cols=None,
            index=False,
            justify='left') + \
        "\n"


def df_difference(df_left, df_right):
    df = df_left.merge(
        df_right,
        how='outer',
        indicator=True,
    )
    # Keep only the rows that differ (that are not in both)
    df = df[df['_merge'] != 'both']
    # Rename 'left_only' and 'right_only' values in '_merge' column
    df['_merge'] = df['_merge'].replace(['left_only'], 'EXPECTED ==>  ')
    df['_merge'] = df['_merge'].replace(['right_only'], 'RESULT ==>  ')
    # Re-order columns: last column ('_merge') becomes first
    cols = df.columns.tolist()
    cols = cols[-1:] + cols[:-1]
    df = df[cols]
    # Rename '_merge' column to empty string
    df = df.rename(columns={"_merge": ""})
    return df

################################################################################


@pytest.fixture(scope="session", autouse=True)
def set_up_session_test_data(request):
    # Run once at the start of test session, before any tests have been run
    print("session setup")
    request.addfinalizer(clean_up_session_test_data)
    # Generate COMPDB
    assert Path(COMPDB_GENERATE).exists()
    cmd = [COMPDB_GENERATE]
    assert subprocess.run(cmd).returncode == 0
    assert Path(COMPDB).exists()


def clean_up_session_test_data():
    print("session cleanup")
    Path(COMPDB).unlink()


@pytest.fixture()
def set_up_test_data():
    print("test setup")
    shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)
    # TODO: clang?
    os.makedirs(TEST_DATA_DIR)
    yield "resource"
    print("test clean up")
    shutil.rmtree(TEST_DATA_DIR)


def check_function_calls_from(target_c_file_name):
    target_c_file = TEST_RESOURCES_DIR / target_c_file_name
    assert Path(COMPDB).exists()
    assert Path(target_c_file).exists()

    # Generate calls.csv file from target_c_file
    outfile = TEST_DATA_DIR / "calls.csv"
    cmd = [CLANG_FIND,
           "--compdb", COMPDB,
           "--out", outfile,
           "--file", target_c_file,
           ]
    assert subprocess.run(cmd).returncode == 0
    assert Path(outfile).exists()

    # Check the generated contents matches expected
    assert EXPECTED.exists()
    df_expected = pd.read_csv(EXPECTED)
    df_expected = df_expected[df_expected['caller_filename'] == target_c_file_name]
    df_generated = pd.read_csv(outfile)
    df_diff = df_difference(df_expected, df_generated)
    assert df_diff.empty, df_to_string(df_diff)


def test_help():
    cmd = [CLANG_FIND, "-h"]
    assert subprocess.run(cmd).returncode == 0


def test_clang_find_direct(set_up_test_data):
    check_function_calls_from("direct.c")


def test_clang_find_indirect_local_var_1(set_up_test_data):
    check_function_calls_from("indirect_local_var_1.c")


def test_clang_find_indirect_local_var_2(set_up_test_data):
    check_function_calls_from("indirect_local_var_2.c")


def test_clang_find_indirect_local_var_3(set_up_test_data):
    check_function_calls_from("indirect_local_var_3.c")


def test_clang_find_indirect_local_var_4(set_up_test_data):
    check_function_calls_from("indirect_local_var_4.c")


def test_clang_find_indirect_global_var_1(set_up_test_data):
    check_function_calls_from("indirect_global_var_1.c")


def test_clang_find_indirect_struct_1(set_up_test_data):
    check_function_calls_from("indirect_struct_1.c")


def test_clang_find_indirect_struct_2(set_up_test_data):
    check_function_calls_from("indirect_struct_2.c")


def test_clang_find_indirect_struct_3(set_up_test_data):
    check_function_calls_from("indirect_struct_3.c")


def test_clang_find_indirect_struct_list_init_1(set_up_test_data):
    check_function_calls_from("indirect_struct_list_init_1.c")


def test_clang_find_indirect_struct_list_init_2(set_up_test_data):
    check_function_calls_from("indirect_struct_list_init_2.c")


def test_clang_find_indirect_struct_list_init_3(set_up_test_data):
    check_function_calls_from("indirect_struct_list_init_3.c")


def test_clang_find_indirect_struct_list_init_4(set_up_test_data):
    check_function_calls_from("indirect_struct_list_init_4.c")


def test_clang_find_indirect_struct_list_init_5(set_up_test_data):
    check_function_calls_from("indirect_struct_list_init_5.c")


def test_clang_find_indirect_struct_list_init_6(set_up_test_data):
    check_function_calls_from("indirect_struct_list_init_6.c")


def test_clang_find_indirect_struct_list_init_7(set_up_test_data):
    check_function_calls_from("indirect_struct_list_init_7.c")


def test_clang_find_indirect_struct_list_init_ex1(set_up_test_data):
    check_function_calls_from("indirect_struct_list_init_ex1.c")


def test_clang_find_indirect_param_call_1(set_up_test_data):
    check_function_calls_from("indirect_param_call_1.c")


def test_clang_find_indirect_param_call_2(set_up_test_data):
    check_function_calls_from("indirect_param_call_2.c")


def test_clang_find_indirect_param_call_3(set_up_test_data):
    check_function_calls_from("indirect_param_call_3.c")


def test_clang_find_indirect_param_call_4(set_up_test_data):
    check_function_calls_from("indirect_param_call_4.c")


def test_clang_find_indirect_param_call_5(set_up_test_data):
    check_function_calls_from("indirect_param_call_5.c")


def test_clang_find_indirect_param_call_6(set_up_test_data):
    check_function_calls_from("indirect_param_call_6.c")


def test_clang_find_indirect_nested_call_1(set_up_test_data):
    check_function_calls_from("indirect_nested_call_1.c")


def test_clang_find_indirect_nested_call_2(set_up_test_data):
    check_function_calls_from("indirect_nested_call_2.c")


def test_clang_find_indirect_nested_call_3(set_up_test_data):
    check_function_calls_from("indirect_nested_call_3.c")


################################################################################


if __name__ == '__main__':
    pytest.main([__file__])

################################################################################
