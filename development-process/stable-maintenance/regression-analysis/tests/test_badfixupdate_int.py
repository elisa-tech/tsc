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
BADFIXUPDATE = TESTS_DIR / ".." / "update.py"


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
    cmd = [BADFIXUPDATE, "-h"]
    assert subprocess.run(cmd).returncode == 0


def test_badfixupdate_basic(set_up_test_data):
    """
    Test badfixupdate.py runs correctly
    """
    gitdir = TEST_DATA_DIR / "stable_4.19.2"
    dst = TEST_DATA_DIR / "update_data"
    cmd = [BADFIXUPDATE,
           "--git-dir", gitdir,
           "--dst", dst]
    print(cmd)
    cwd = TESTS_DIR / ".."
    assert subprocess.run(
        cmd,
        cwd=cwd).returncode == 0
    assert (dst / 'README.md').exists()


if __name__ == '__main__':
    pytest.main([__file__])
