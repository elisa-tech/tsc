# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import unittest

callgraphtool_path = os.path.dirname(os.path.abspath(__file__)) + '/../..'
sys.path.append(callgraphtool_path)

from build import valid_llvm_extensions, get_build_root  # noqa E402


def test_valid_llvm_extensions():
    assert '.ll' in valid_llvm_extensions()
    assert '.llvm' in valid_llvm_extensions()


def test_get_build_root():
    p1 = '~/work/project/buildlog1.txt'
    p2 = '/home/user/project/buildlog.txt'
    p3 = '~/buildlog.txt'
    p4 = '/buildlog.txt'
    p5 = '/'
    p6 = '~/'
    p7 = '/tmp'
    p8 = '/tmp/../'
    home = os.path.expanduser("~")
    assert home + '/work/project' == get_build_root(p1)
    assert '/home/user/project' == get_build_root(p2)
    assert home == get_build_root(p3)
    assert '/' == get_build_root(p4)
    assert '/' == get_build_root(p5)
    assert home == get_build_root(p6)
    assert '/tmp' == get_build_root(p7)
    assert '/' == get_build_root(p8)
