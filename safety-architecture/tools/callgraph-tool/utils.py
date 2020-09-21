#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import csv
import os
import sys
import hashlib
import logging
import argparse
import clang_download
import subprocess

from colorlog import ColoredFormatter, default_log_colors

###############################################################################

LOG_SPAM = logging.DEBUG - 1
LOGGER_NAME = "xcgraph-logger"
_LOGGER = logging.getLogger(LOGGER_NAME)
_FILEDIR = os.path.dirname(os.path.realpath(__file__))

###############################################################################


def exit_unless_accessible(filename):
    if filename and not os.path.isfile(filename):
        _LOGGER.error(
            "File not found or no permissions: \"%s\"" % filename)
        sys.exit(1)

################################################################################


def setup_logging(verbosity=1):
    project_logger = logging.getLogger(LOGGER_NAME)

    if verbosity == 0:
        level = logging.NOTSET
    elif verbosity == 1:
        level = logging.INFO
    elif verbosity == 2:
        level = logging.DEBUG
    else:
        level = LOG_SPAM

    log_colors = default_log_colors
    if level < logging.DEBUG:
        logformat = \
            "%(log_color)s%(levelname)-8s%(reset)s "\
            "%(filename)s:%(lineno)d:%(funcName)s(): %(message)s"
    else:
        logformat = "%(log_color)s%(levelname)-8s%(reset)s %(message)s"

    default_log_colors['ERROR'] = 'bold_red'
    default_log_colors['INFO'] = 'fg_bold_white'
    default_log_colors['SPAM'] = 'fg_bold_black'
    default_log_colors['DEBUG'] = 'fg_white'
    formatter = ColoredFormatter(logformat, log_colors=log_colors)
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    logging.addLevelName(LOG_SPAM, "SPAM")
    project_logger.addHandler(stream)
    project_logger.setLevel(level)


################################################################################


def exec_cmd(cmd):
    command_str = " ".join(cmd)
    _LOGGER.debug("Running: %s" % command_str)
    ret = subprocess.run(cmd)
    if ret.returncode != 0:
        _LOGGER.debug("Command retuned error status: %s" % ret.returncode)
        _LOGGER.debug("stdout: %s" % ret.stdout)
        _LOGGER.debug("stderr: %s" % ret.stderr)


################################################################################


class CsvWriter():
    def __init__(self, filename):
        self.filename = filename
        self.fp = open(self.filename, 'w')
        self.writer = csv.writer(self.fp, delimiter=',', quoting=csv.QUOTE_ALL)

    def write_arr(self, elems):
        self.writer.writerow(elems)

    def close(self):
        self.fp.close()
        _LOGGER.info("Wrote: %s" % self.filename)


################################################################################
