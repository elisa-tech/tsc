#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
import sys
import re
import wget
import platform
from pathlib import Path
import shutil
import tarfile
import logging

################################################################################

LLVM_URL = 'https://github.com/llvm/llvm-project/releases/download'
RELEASE = '10.0.0'

################################################################################


def get_source_url():
    return "%s/llvmorg-%s/clang-%s.src.tar.xz" % (LLVM_URL, RELEASE, RELEASE)


def get_clang_url():
    plat = platform.platform()
    if 'Ubuntu-18.04' in plat and 'x86_64' in plat:
        url = "%s/llvmorg-%s/" \
            "clang+llvm-%s-x86_64-linux-gnu-ubuntu-18.04.tar.xz" \
            "" % (LLVM_URL, RELEASE, RELEASE)
        return url
    # else if
    #     ...
    else:
        sys.stderr.write("Error: unknown platfrom \"%s\"\n" % plat)
        sys.exit(1)


def rm_r(path):
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    elif os.path.exists(path):
        os.remove(path)


def prompt_if_exists(dstdir):
    if dstdir.exists():
        prompt = \
            "This will remove earlier content from \"%s\". "\
            "Are you sure? (y/N): " % dstdir
        if input(prompt) != 'y':
            print("Cancelled")
            sys.exit(0)


def update_clang(output_dir):
    # TODO: error checks, check signatures
    outpath = Path(output_dir)
    prompt_if_exists(outpath)
    rm_r(outpath)
    outpath.mkdir(parents=True, exist_ok=True)

    url = get_source_url()
    print("[+] Downloading: %s\n" % url)
    source_tar = wget.download(url, out=str(outpath))
    print("\n")
    print("[+] Extracting: %s" % source_tar)
    with tarfile.open(source_tar) as f:
        f.extractall(str(outpath))
    extdir = Path(Path(source_tar).stem).stem
    shutil.move(str(outpath / extdir), str(outpath / "src"))

    url = get_clang_url()
    print("[+] Downloading: %s\n" % url)
    source_tar = wget.download(url, out=str(outpath))
    print("\n")
    print("[+] Extracting: %s" % source_tar)
    with tarfile.open(source_tar) as f:
        f.extractall(str(outpath))
    extdir = Path(Path(source_tar).stem).stem
    shutil.move(str(outpath / extdir), str(outpath / "bin"))


def getargs():
    desc = \
        "Download clang release from https://github.com/llvm/llvm-project/ "\
        "and extract to OUTPUT_DIR"

    epil = "Example: ./%s" % \
        os.path.basename(__file__)
    parser = argparse.ArgumentParser(description=desc, epilog=epil)

    help = "set the destination folder, defaults to ./clang"
    parser.add_argument('--output-dir', nargs='?',
                        help=help, default='./clang')

    return parser.parse_args()

################################################################################


if __name__ == "__main__":
    args = getargs()
    update_clang(args.output_dir)

################################################################################
