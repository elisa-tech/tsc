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


def check_function_calls_from(target_bc_file_name, cpp=False):
    target_bc_file = TEST_RESOURCES_DIR / target_bc_file_name
    assert Path(target_bc_file).exists()

    outfile = TEST_DATA_DIR / "calls.csv"
    if target_bc_file_name.endswith(".bclist"):
        target_bc_file = "@%s" % target_bc_file

    if cpp:
        cmd = [CG_BIN,
               "-cpp_linked_bitcode", target_bc_file,
               "-o", outfile,
               target_bc_file,
               ]
    else:
        cmd = [CG_BIN,
               "-o", outfile,
               target_bc_file,
               ]
    assert subprocess.run(cmd).returncode == 0
    assert Path(outfile).exists()

    # Check the generated contents matches expected
    assert EXPECTED.exists()
    df_expected = pd.read_csv(EXPECTED)
    caller_regex = "^%s" % target_bc_file_name.split(".")[0]
    df_expected = df_regex_filter(df_expected, "caller_filename", caller_regex)
    df_generated = pd.read_csv(outfile)
    # Remove entries where caller or callee function name begins with '__cxx'.
    # These are library functions we want to ignore in the tests:
    df_generated = df_generated[
        ~df_generated["caller_function"].str.startswith("__cxx", na=False) &
        ~df_generated["callee_function"].str.startswith("__cxx", na=False)]
    df_diff = test_utils.df_difference(df_expected, df_generated)
    assert df_diff.empty, test_utils.df_to_string(df_diff)


def test_help():
    cmd = [CG_BIN, "-h"]
    assert subprocess.run(cmd).returncode == 0


def test_cg_test_template(set_up_test_data):
    check_function_calls_from("cg-test-template.bclist")


def test_mlta_basic(set_up_test_data):
    check_function_calls_from("test-mlta-basic.bclist")


def test_mlta_arr(set_up_test_data):
    check_function_calls_from("test-mlta-arr.bclist")


def test_mlta_notassigned(set_up_test_data):
    check_function_calls_from("test-mlta-notassigned.bclist")


def test_mlta_assign_value(set_up_test_data):
    check_function_calls_from("test-mlta-assign-value.bclist")


def test_mlta_confinestore(set_up_test_data):
    check_function_calls_from("test-mlta-confinestore.bclist")


def test_mlta_memcpy(set_up_test_data):
    check_function_calls_from("test-mlta-memcpy.bclist")


def test_mlta_null(set_up_test_data):
    check_function_calls_from("test-mlta-null.bclist")


def test_mlta_x86_init(set_up_test_data):
    check_function_calls_from("test-mlta-x86-init.bclist")


def test_mlta_misc(set_up_test_data):
    check_function_calls_from("test-mlta-misc.bclist")


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


def test_same_funcname(set_up_test_data):
    check_function_calls_from("test-same-funcname.bclist")


def test_ta_mlta(set_up_test_data):
    check_function_calls_from("test-ta-mlta.bclist")


def test_union(set_up_test_data):
    check_function_calls_from("test-union.bclist")


def test_hello_cpp(set_up_test_data):
    check_function_calls_from("test-hello.bc", cpp=True)


def test_inheritance_basic_cpp(set_up_test_data):
    check_function_calls_from("test-inheritance-basic.bc", cpp=True)


def test_inheritance_global_cpp(set_up_test_data):
    check_function_calls_from("test-inheritance-global.bc", cpp=True)


def test_inheritance_multilevel_cpp(set_up_test_data):
    check_function_calls_from("test-inheritance-multilevel.bc", cpp=True)


def test_inheritance_multiple_1_cpp(set_up_test_data):
    check_function_calls_from("test-inheritance-multiple-1.bc", cpp=True)


def test_inheritance_multiple_2_cpp(set_up_test_data):
    check_function_calls_from("test-inheritance-multiple-2.bc", cpp=True)


def test_inheritance_multiple_3_cpp(set_up_test_data):
    check_function_calls_from("test-inheritance-multiple-3.bc", cpp=True)


def test_namespace_1_cpp(set_up_test_data):
    check_function_calls_from("test-namespace-1.bc", cpp=True)


def test_namespace_2_cpp(set_up_test_data):
    check_function_calls_from("test-namespace-2.bc", cpp=True)


def test_namespace_3_cpp(set_up_test_data):
    check_function_calls_from("test-namespace-3.bc", cpp=True)


def test_modules_cpp(set_up_test_data):
    check_function_calls_from("test-modules.linked.bc", cpp=True)


################################################################################
