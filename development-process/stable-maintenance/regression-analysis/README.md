<!--
SPDX-FileCopyrightText: 2019 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# Kernel Regression Analysis

This repository is a collection of scripts for Linux Stable Kernel regression analysis.

## Table of contents
* [Getting Started](#getting-started)
* [Building Regression Database](#building-regression-database)
* [Visualizing Regressions](#visualizing-regressions)
* [Merging Commits Between Branches](#merging-commits-between-branches)
* [Filtering Based on Kernel Configuration](#filtering-based-on-kernel-configuration)
* [Filtering Based on Contents of Specific Fields](#filtering-based-on-contents-of-specific-fields)
* [Updating Regression Database for a Set of Releases](#updating-regression-database-for-a-set-of-releases)

## Getting Started
Scripts require python3, git, and binutils (objdump):
```
$ sudo apt install python3 python3-pip git binutils
```

In addition, the scripts rely on a number of python packages specified in requirements.txt. You can install the required packages with:
```
$ pip3 install -r requirements.txt
```

You also need a copy of the stable kernel source repository:
```
$ git clone git://git.kernel.org/pub/scm/linux/kernel/git/stable/linux-stable.git
```

## Building Regression Database
[badfixstats.py](badfixstats.py) finds regressions from the kernel repository based on "Fixes" and "Revert" tags in the stable kernel git changelogs.

As an example, the below command finds regressions from the repository in local path ~/linux-stable between tags v4.19 and v4.19.74, producing the output to file linux-stable_v4.19-v4.19.74.csv:
```
$ ./badfixstats.py --git-dir ~/linux-stable --out linux-stable_v4.19-v4.19.74.csv v4.19^..v4.19.74
```
Output is a CSV database that lists all commits in the specified revision range in chronological order by commit time. For each commit, the CSV database includes fields such as: Commit_datetime, Commit_hexsha, and Commit_tag that specify the commit time, hexsha, and tag respectively. Fields such as Badfix_hexsha, Badfix_datetime, and Badfix_tag refer to regression (or badfix) that was fixed by the commit specified in Commit_hexsha field on the same row. That is, if Badfix_hexsha is not empty, it refers to regression commit that was fixed by Commit_hexsha. Otherwise, the associated Commit_hexsha is not a fix to an earlier regression. In general all fields with prefix "Badfix_" refer to the regression, whereas, all fields with prefix "Commit_" refer to a potential fix.

## Visualizing Regressions
[badfixplot.py](badfixplot.py) takes the CSV database output by [badfixstats.py](badfixstats.py) and visualizes the regressions in interactive html charts:
```
$ ./badfixplot.py linux-stable_v4.19-v4.19.74.csv
```
Output is a set of html files that visualize the regressions.

## Merging Commits Between Branches
[badfixcommon.py](badfixcommon.py) generates output that describes the overlap between two branches given two CSV database files as input. Script determines the overlaps based on upstream references on each line in the input CSV files.

As an example, the below command describes the overlap between specific tags in v4.19 and v4.14 branches assuming the input databases linux-stable_v4.19-v4.19.74.csv and linux-stable_v4.14-v4.14.145.csv have been created earlier with [badfixstats.py](badfixstats.py):
```
$ ./badfixcommon.py linux-stable_v4.19-v4.19.74.csv linux-stable_v4.14-v4.14.145.csv
```
Script outputs the following CSV files:
* csv1_unique.csv - commits that are unique in the first CSV input
* csv2_unique.csv - commits that are unique in the second CSV input
* common.csv - commits that are common between the two CSV input files based on upstream references
* merged.csv - commits that occur in either branch, but each commit is included only once

Each row in the "common" CSV output refers to a common commit in both branches. On each row, column names with postfix "__1" refer to the commit from the first input file, and column names with postfix "__2" refer to the commit from the second input file. So, for example, the column "Badfix_lifetime_days__1" specifies the regression's lifetime in the first branch. Similarly, "Badfix_lifetime_days__2" specifies the regression's lifetime in the second branch.

"Merged" commits are the combination of unique commits from the three categories: 1) commits that are unique in the first branch, 2) commits that are unique in the second branch, and 3) commits that are common between the branches. For the common commits, the merged set of commits needs to account for the fact that each commit includes data from two branches. The data selected for the "merged" branch is based on the following rules:
1. For the common commits that are not regressions in either branch: use the data from the branch where the commit first occurred
2. For the common commits that are regression in branch1 but not in branch2: use the data from the branch1
3. For the common commits that are regression in branch2 but not in branch1: use the data from the branch2
4. For the common commits that are regression in both branches: use the data from the branch where the commit first occurred

To visualize the regressions in the merged branch, the resulting merged.csv can be given as an input to [badfixplot.py](badfixplot.py). Moreover, to merge more than two pairs of branches, the resulting merged.csv can be combined with another branch by specifying the merged.csv as an input to the [badfixcommon.py](badfixcommon.py).

## Filtering Based on Kernel Configuration
[patchfilter-tool.py](patchfilter-tool.py) makes it possible to filter a set of patches to those that are relevant for a specific kernel configuration. That is, if a patch modifies source files not used in the kernel build, the patch can be labelled as not relevant for the specific kernel configuration. Based on this information, we can filter the regression database to include only those regressions that are relevant for the specific kernel configuration.

To filter the regression database based on the kernel configuration, first build the kernel tree using the kernel configuration of interest. Then, run the [patchfilter-tool.py](patchfilter-tool.py) specifying the kernel build tree and the git revision range:
```
$ ./patchfilter-tool.py --linux-dir ~/linux-stable/ v4.19..v4.19.74
[+] Reading objects from: ~/linux-stable/
[+] Wrote: objdump.txt
[+] Wrote: filelist.txt
[+] Wrote: patchlist.txt
```
We can then generate the regression database using [badfixstats.py](badfixstats.py) by specifying the generated patchlist.txt as --inscope argument:
```
$ ./badfixstats.py --inscope patchlist.txt --git-dir ~/linux-stable --out linux-stable_v4.19-v4.19.74.csv v4.19^..v4.19.74
```
In the generated CSV output, the field "In_scope" now indicates if the patch is relevant for the specific kernel configuration or not.

## Filtering Based on Contents of Specific Fields
To filter the [badfixstats.py](badfixstats.py) generated CSV output based on the contents of specific fields, we recommend installing csvquery (or similar) for running SQL queries on CSV files:
```
$ pip install --user csvquerytool

# Ensure the install directory is in the $PATH
$ export PATH=$PATH:'~/.local/bin'
```
As an example, the below command shows how to filter the data based on "Signed-off-by" tag assuming the input database linux-stable_v4.19-v4.19.74.csv has been created earlier with [badfixstats.py](badfixstats.py):
```
$ csvquery -q 'select * from csv where Commit_signedby like "%Greg Kroah-Hartman%" or Badfix_signedby like "%Greg Kroah-Hartman%"' linux-stable_v4.19-v4.19.74.csv
```
Similarly, the example below shows how to filter the data based on "In_scope" field:
```
$ csvquery -q 'select * from csv where In_scope == 1' linux-stable_v4.19-v4.19.74.csv
```
To visualize the filtered data, the resulting output can be redirected to a file which then can be given as an input to [badfixplot.py](badfixplot.py).

## Updating Regression Database for a Set of Releases
[update.py](update.py) is a simple front-end to badfixstats.py and badfixplot.py that makes it easier to update and maintain regression databases and visualizations for a set of LTS releases. Given a linux-stable git repository, update.py calls badfixstats.py and badfixplot.py to generate and visualize regression database for specific LTS branches and also generates a markdown page that summarizes the collected data.
```
$ ./update.py --git-dir ~/linux-stable
[+] Updating regression database: v4.19^..v4.19.88
[+] Updating regression database: v4.14^..v4.14.158
[+] Updating regression database: v4.9^..v4.9.206
[+] Updating regression database: v4.4^..v4.4.206
[+] Creating summary
[+] Done, see: ~/data/README.md
```

## License
This project is licensed under the GPL 2.0 license - see the [GPL-2.0-only.txt](LICENSES/GPL-2.0-only.txt) file for details.
