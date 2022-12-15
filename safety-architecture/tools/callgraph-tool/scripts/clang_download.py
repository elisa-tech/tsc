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
import distro
from pathlib import Path
import shutil
import tarfile
import logging

################################################################################

LLVM_URL = 'https://github.com/llvm/llvm-project/releases/download'
RELEASE = '11.0.0'

################################################################################


def get_source_url():
    return "%s/llvmorg-%s/clang-%s.src.tar.xz" % (LLVM_URL, RELEASE, RELEASE)


def get_clang_url():
    plat = platform.platform()
    if 'x86_64' in platform.platform() and \
            distro.id() == 'ubuntu' and distro.version() == '20.04':
        url = "%s/llvmorg-%s/" \
            "clang+llvm-%s-x86_64-linux-gnu-ubuntu-20.04.tar.xz" \
            "" % (LLVM_URL, RELEASE, RELEASE)
        return url
    elif 'x86_64' in platform.platform() and \
            distro.id() == 'ubuntu' and \
            (distro.version() == '18.04' or distro.version() == '16.04'):
        url = "%s/llvmorg-%s/" \
            "clang+llvm-%s-x86_64-linux-gnu-ubuntu-16.04.tar.xz" \
            "" % (LLVM_URL, RELEASE, RELEASE)
        return url
    # elif
    #     ...
    else:
        sys.stderr.write("Error: unknown platfrom \"%s\"\n" % plat)
        print("%s" % platform.system())
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
        def is_within_directory(directory, target):
            
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
        
            prefix = os.path.commonprefix([abs_directory, abs_target])
            
            return prefix == abs_directory
        
        def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
        
            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                if not is_within_directory(path, member_path):
                    raise Exception("Attempted Path Traversal in Tar File")
        
            tar.extractall(path, members, numeric_owner=numeric_owner) 
            
        
        safe_extract(f, str(outpath))
    extdir = Path(Path(source_tar).stem).stem
    shutil.move(str(outpath / extdir), str(outpath / "src"))

    url = get_clang_url()
    print("[+] Downloading: %s\n" % url)
    source_tar = wget.download(url, out=str(outpath))
    print("\n")
    print("[+] Extracting: %s" % source_tar)
    with tarfile.open(source_tar) as f:
        def is_within_directory(directory, target):
            
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
        
            prefix = os.path.commonprefix([abs_directory, abs_target])
            
            return prefix == abs_directory
        
        def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
        
            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                if not is_within_directory(path, member_path):
                    raise Exception("Attempted Path Traversal in Tar File")
        
            tar.extractall(path, members, numeric_owner=numeric_owner) 
            
        
        safe_extract(f, str(outpath))
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
