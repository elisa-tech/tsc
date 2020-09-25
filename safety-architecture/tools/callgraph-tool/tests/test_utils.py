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
