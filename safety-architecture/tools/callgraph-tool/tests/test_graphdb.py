# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import pytest
import os
import sys
import tempfile

ROOT_FOLDER = os.path.dirname(os.path.realpath(__file__))
sys.path.append(ROOT_FOLDER + '/..')

from db import GraphDb  # noqa E402


def test_db_creation():
    db = GraphDb("")


def test_db_save_failing():
    db = GraphDb("")
    with pytest.raises(NameError):
        db.save()


def test_db_open_failing():
    db = GraphDb("")
    with pytest.raises(NameError):
        db.open()


def test_db_save():
    file = tempfile.NamedTemporaryFile(delete=True)
    db = GraphDb(file.name)
    db.save()


def test_db_save_and_open():
    file = tempfile.NamedTemporaryFile(delete=True)
    db = GraphDb(file.name)
    db.save()
    db.open()


if __name__ == '__main__':
    pytest.main([__file__])
