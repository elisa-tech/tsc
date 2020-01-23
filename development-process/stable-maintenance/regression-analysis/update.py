#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2019 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: GPL-2.0-only

from __future__ import print_function
import git
import shutil
import argparse
import csv
import os
import sys
from pathlib import Path
import subprocess
import pandas as pd
from tabulate import tabulate

################################################################################

LTS_VERSIONS = ["v4.19", "v4.14", "v4.9", "v4.4"]
SCRIPT_DIR = Path(os.path.abspath((os.path.dirname(__file__))))

################################################################################


def exec_cmd(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
    pipe = subprocess.Popen(
        cmd, shell=True, stdout=stdout, stderr=stderr, encoding='utf-8')
    stdout, stderr = pipe.communicate()
    if pipe.returncode != 0:
        raise ValueError(stderr)
    return stdout if stdout else None


def print_table(dict, out=sys.stdout):
    table = tabulate(
        dict,
        tablefmt="pipe",
        headers="keys",
        numalign="center",
        stralign="center")
    print(table, file=out)
    print("", file=out)


def generate_readme(
        dst,
        regression_charts,
        missing_annotations,
        regression_lifetimes,
        multiple_fixes):

    filename = dst / "README.md"
    with open(filename, 'w') as out:
        print("# Linux Kernel Regression Data\n", file=out)
        text = '''
Below sections summarize and visualize the data collected, as well
as provide links to download the raw data in CSV format.
        '''
        print(text, file=out)

        print("## Data\n", file=out)
        print_table(regression_charts, out)

        print("## Missing Annotations\n", file=out)
        print_table(missing_annotations, out)

        print("## Regression Lifetimes\n", file=out)
        print_table(regression_lifetimes, out)

        print("## Multiple Fixes to One Regression\n", file=out)
        print_table(multiple_fixes, out)

    return str(filename)


def summarize(db_list, dst):
    regression_charts = {}
    missing_annotations = {}
    regression_lifetimes = {}
    multiple_fixes = {}

    for db in db_list:
        df = pd.read_csv(
            db['fullfilename'], na_values=['None'], keep_default_na=True)
        commits = df.shape[0]
        if commits == 0:
            print("Warning: no commits: %s" % db['fullfilename'])
            continue
        fromtag = db['first_tag']
        totag = db['last_tag']

        chartname = "%s__summary.html" % db['filename']
        csvname = db['filename']
        setcol = regression_charts.setdefault
        setcol('Version', []).append("%s to %s" % (fromtag, totag))
        setcol('Regression HTML Charts', []).append(
            "[%s](%s)" % (chartname, chartname))
        setcol('Regression CSV Database', []).append(
            "[%s](%s)" % (csvname, csvname))

        tagged = df[df['Matched_by'].notnull()].shape[0]
        tagged_pct = '{:.0%}'.format(tagged / commits)
        setcol = missing_annotations.setdefault
        setcol('Version', []).append("%s to %s" % (fromtag, totag))
        setcol('Commits', []).append(commits)
        setcol('Commits_tagged', []).append(tagged)
        setcol('Commits_tagged (%)', []).append(tagged_pct)

        df_regrs = df[df['Badfix_hexsha'].notnull()]
        regrs = df_regrs.shape[0]
        if regrs == 0:
            print("Warning: no regressions: %s" % db['fullfilename'])
            continue
        regrs_eq_0 = df_regrs[df_regrs['Badfix_lifetime_days'] == 0].shape[0]
        regrs_lt_0 = df_regrs[df_regrs['Badfix_lifetime_days'] < 0].shape[0]
        regrs_le_0_pct = '{:.0%}'.format((regrs_eq_0 + regrs_lt_0) / regrs)
        setcol = regression_lifetimes.setdefault
        setcol('Version', []).append("%s to %s" % (fromtag, totag))
        setcol('Regressions <br>(lifetime any)', []).append(regrs)
        setcol('Regressions <br>(lifetime == 0)', []).append(regrs_eq_0)
        setcol('Regressions <br>(lifetime < 0)', []).append(regrs_lt_0)
        setcol('Regressions <br>(lifetime <= 0)(%)', []).append(regrs_le_0_pct)

        df_regrs_gt_0 = df_regrs[df_regrs['Badfix_lifetime_days'] > 0]
        regrs_gt_0 = df_regrs_gt_0.shape[0]
        dfg = df_regrs_gt_0.groupby(['Badfix_hexsha'])\
            .size()\
            .reset_index()\
            .rename(columns={0: 'count'})
        regrs_fixes_1 = dfg[dfg['count'] == 1].shape[0]
        regrs_fixes_2 = dfg[dfg['count'] == 2].shape[0]
        regrs_fixes_3 = dfg[dfg['count'] == 3].shape[0]
        regrs_fixes_ge_4 = dfg[dfg['count'] >= 4].shape[0]
        setcol = multiple_fixes.setdefault
        setcol('Version', []).append("%s to %s" % (fromtag, totag))
        setcol('Regressions <br>(lifetime > 0)', []).append(regrs_gt_0)
        setcol('Regressions <br>(Fixes == 1)', []).append(regrs_fixes_1)
        setcol('Regressions <br>(Fixes == 2)', []).append(regrs_fixes_2)
        setcol('Regressions <br>(Fixes == 3)', []).append(regrs_fixes_3)
        setcol('Regressions <br>(Fixes >= 4)', []).append(regrs_fixes_ge_4)

    return generate_readme(
        dst,
        regression_charts,
        missing_annotations,
        regression_lifetimes,
        multiple_fixes)


def update(dstfolder, gitdir):
    repo = git.Repo(gitdir)
    dst = SCRIPT_DIR / dstfolder
    dst.mkdir(parents=True, exist_ok=True)
    db_list = []
    warn = False

    for version in LTS_VERSIONS:
        tag_version_list = repo.git.tag(
            "%s.*" % version, "%s" % version,
            sort='creatordate', list=True).split('\n')
        if len(tag_version_list) <= 1:
            print("Warning: missing expected tags for \"%s\"" % version)
            warn = True
            continue
        first_tag = tag_version_list[0]
        last_tag = tag_version_list[-1]
        rev = "%s^..%s" % (first_tag, last_tag)
        outfilename = "linux_stable__%s-%s.csv" % (first_tag, last_tag)
        out = str(dst / outfilename)
        print("[+] Updating regression database: %s" % rev)
        cmd = "./badfixstats.py --git-dir %s --out %s %s" % (gitdir, out, rev)
        exec_cmd(cmd)
        db = {
            "first_tag": first_tag,
            "last_tag": last_tag,
            "fullfilename": out,
            "filename": outfilename,
        }
        db_list.append(db)
        cmd = "./badfixplot.py --include_plotlyjs cdn %s" % out
        exec_cmd(cmd)

    if warn:
        print("Are you sure you specified a linux-stable repository?")

    if db_list:
        print("[+] Creating summary")
        return summarize(db_list, dst)


def prompt_if_exists(dstfolder):
    if dstfolder.exists():
        prompt = \
            "This will remove earlier content from \"%s\". "\
            "Are you sure? (y/N): " % dstfolder
        if input(prompt) != 'y':
            print("Cancelled")
            sys.exit(0)


def rm_r(path):
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    elif os.path.exists(path):
        os.remove(path)


def exit_unless_exists(filename):
    if not os.path.isfile(filename):
        sys.stderr.write(
            "Error: script requires \"%s\", which was not found on "
            "the current dir.\n" % filename)
        sys.exit(1)


def getargs():
    desc = \
        "This script is a simple front-end to badfixstats.py and "\
        "badfixplot.py to make it easier to maintain and update the "\
        "kernel regression data. "\
        "Given a linux-stable git repository (GIT_DIR), this script calls "\
        "badfixstats.py and badfixplot.py to generate and visualize "\
        "regression database for specific LTS branches. "\
        "The script also generates a markdown page that summarizes the "\
        "collected data."

    epil = "Example: ./%s --git-dir ~/linux-stable -d ~/data" % \
        os.path.basename(__file__)
    parser = argparse.ArgumentParser(description=desc, epilog=epil)

    help = "file path to linux-stable git repository"
    parser.add_argument('--git-dir', required=True, help=help)

    help = "set the destination folder, defaults to ./data"
    parser.add_argument('-d', '--dst', nargs='?', help=help, default='./data')

    return parser.parse_args()

################################################################################


if __name__ == "__main__":
    if sys.version_info[0] < 3:
        sys.stderr.write("Error: script requires Python 3.x\n")
        sys.exit(1)

    args = getargs()
    dstdir = Path(args.dst)
    gitdir = args.git_dir

    gitdir = gitdir if gitdir.endswith(".git") else os.path.join(gitdir, ".git")
    if(not (os.path.isdir(gitdir))):
        sys.stderr.write("Error: not a git repository: %s\n" % gitdir)
        sys.exit(1)

    exit_unless_exists("badfixstats.py")
    exit_unless_exists("badfixplot.py")

    prompt_if_exists(dstdir)
    rm_r(dstdir)
    ret = update(dstdir, gitdir)
    if ret:
        print("[+] Done, see: %s" % ret)


################################################################################
