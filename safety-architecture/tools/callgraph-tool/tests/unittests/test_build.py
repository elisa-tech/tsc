# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import unittest

callgraphtool_path = os.path.dirname(os.path.abspath(__file__)) + '/../..'
sys.path.append(callgraphtool_path)

from build import valid_llvm_extensions  # noqa E402


def test_valid_llvm_extensions():
    assert '.ll' in valid_llvm_extensions()
    assert '.llvm' in valid_llvm_extensions()
