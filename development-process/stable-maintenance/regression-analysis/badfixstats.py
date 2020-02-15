#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2019 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: GPL-2.0-only

import re
import git
import csv
import argparse
import os
import sys

from pandas import DataFrame
from collections import OrderedDict
from datetime import datetime, timedelta

################################################################################


class GitStatistics:

    def __init__(self, gitdir, rev, inscopefile=""):
        self.gitdir = gitdir
        # Statistics are generated based on the git commit entries in the
        # specified git repository that match the given revision (range)
        self.rev = rev
        # Dictionary to store the report entries
        # Key: column header, Value: list of entries
        self.entries = {}
        # List of all column names
        self.allcolumns = []
        # GitPython Repo object
        self.repo = git.Repo(self.gitdir)
        # Set of commit hashes in self.repo between [beg,end]
        # Key: commit sha
        self.commitset = set()
        self._build_commitset()
        # Map commit summary to commit hash
        # Key: commit summary, Value: list of commits
        self.summarymap = {}
        self._build_summarymap()
        # Map upstream commit to commit in the selected branch
        # Key: upstream sha, Value: list of commits in the selected branch
        self.mapupstreamtocommit = {}
        # Map commit in the selected branch to upstream commit
        # Key: commit in the selected branch, Value: upstream commit sha
        self.mapcommittoupstream = {}
        self._build_upstreamindexes()
        # Set of commits that should be considered "in-scope"
        # Key: 12-digit commit sha
        self.inscopeset = set()
        self._build_inscopeset(inscopefile)
        # Map commit hash to tag name
        # Key: commit hash, Value: list of tag names
        self.tagmap = {}
        self._build_tagmap()
        # Map commit hash to list of names who signed-off the commit
        # Key: commit hash, Value: list of names
        self.signedoffmap = {}
        self._build_signedoffmap()

    def find_badfixes(self):
        for commit in list(self.repo.iter_commits(self.rev, reverse=True)):
            self._find_badfix(commit)

        self.allcolumns = list(self.entries.keys())
        # The order of self.allcolumns determines the order of the columns
        # in the CSV out file
        self.allcolumns.sort()

    def to_csv(self, filename):
        df = DataFrame(self.entries, columns=self.allcolumns)
        df.to_csv(path_or_buf=filename, quoting=csv.QUOTE_ALL,
                  sep=",", index=False, encoding='utf-8')

    def _get_long_commit_sha(self, sha):
        if not sha:
            return None
        if len(sha) >= 40:
            return sha
        try:
            return self.repo.git.rev_parse(sha)
        except git.GitCommandError:
            return None

    def _get_commit(self, commitsha):
        if not commitsha:
            return None
        try:
            return self.repo.commit(commitsha)
        except ValueError:
            return None

    def _find_badfix(self, commit):
        stampmap = OrderedDict()
        matched_by_list = []

        # First, match by sha
        for line in commit.message.splitlines():
            badfixsha, found_by, matched_by = self._check_line_badfix_sha(line)
            if matched_by:
                matched_by_list.append(matched_by)
            if badfixsha and badfixsha not in stampmap:
                stampmap[badfixsha] = found_by

        # Then, match by summary if the match by sha failed to produce at least
        # one pair of (badfixsha,commit)
        if not stampmap:
            for line in commit.message.splitlines():
                badfixsha, found_by, matched_by = self._check_line_badfix_summary(line)
                if matched_by:
                    matched_by_list.append(matched_by)
                if badfixsha and badfixsha not in stampmap:
                    stampmap[badfixsha] = found_by

        # If no regression was found, we still want to output ("stamp") the
        # commit; therefore, add an "empty" badfix
        if not stampmap:
            stampmap[""] = ""

        # Output ("stamp") all commits collected to stampmap
        for badfixsha in stampmap:
            found_by = stampmap[badfixsha]
            self._stamp_commit(badfixsha, commit, found_by, matched_by_list)

    def _stamp_commit(self, badfixsha, commit, found_by, matched_by_list):
        badfix_commit = self._get_commit(badfixsha)
        if not badfix_commit:
            found_by = ""
            badfix_lifetime_days = ""
            badfix_lifetime_days_decimal = ""
            badfix_tag = ""
            badfix_sha = ""
            badfix_datetime = ""
            badfix_signer = ""
        else:
            if badfix_commit.hexsha == commit.hexsha:
                text = \
                    "[+] Warning: ignored commit where badfix and fix are "\
                    "the same (%s:%s)" % (commit.hexsha, found_by)
                print(text)
                return
            badfix_timedelta = commit.committed_datetime - badfix_commit.committed_datetime
            badfix_lifetime_days = int(round(badfix_timedelta / timedelta(days=1)))
            badfix_lifetime_days_decimal = badfix_timedelta / timedelta(days=1)
            badfix_tag = self.tagmap.get(badfix_commit.hexsha, ["unknown"])[0]
            badfix_sha = badfix_commit.hexsha
            badfix_datetime = badfix_commit.committed_datetime
            badfix_signer = ";".join(self.signedoffmap.get(badfix_commit.hexsha, [""]))

        badfix_upstream_hexsha = self.mapcommittoupstream.get(badfix_sha, "")
        commit_upstream_hexsha = self.mapcommittoupstream.get(commit.hexsha, "")
        badfix_upstream_commit = self._get_commit(badfix_upstream_hexsha)
        commit_upstream_commit = self._get_commit(commit_upstream_hexsha)
        if not badfix_upstream_commit or not commit_upstream_commit:
            badfix_upstream_lifetime_days_decimal = ""
            badfix_upstream_lifetime_days = ""
        else:
            badfix_upstream_timedelta = \
                commit_upstream_commit.committed_datetime - \
                badfix_upstream_commit.committed_datetime
            badfix_upstream_lifetime_days_decimal = \
                badfix_upstream_timedelta / timedelta(days=1)
            badfix_upstream_lifetime_days = \
                int(round(badfix_upstream_timedelta / timedelta(days=1)))

        if not commit_upstream_commit:
            commit_upstream_committed = ""
            commit_latency_us_days_decimal = ""
            commit_latency_us_days = ""
        else:
            commit_upstream_committed = \
                commit_upstream_commit.committed_datetime
            commit_latency_us_timedelta = \
                commit.committed_datetime - commit_upstream_commit.committed_datetime
            commit_latency_us_days_decimal = \
                commit_latency_us_timedelta / timedelta(days=1)
            commit_latency_us_days = \
                int(round(commit_latency_us_timedelta / timedelta(days=1)))

        inscope = "1"
        if self.inscopeset:
            inscope = "1" if commit.hexsha[:12] in self.inscopeset else "0"
        commit_tag = self.tagmap.get(commit.hexsha, ["unknown"])[0]
        commit_signer = ";".join(self.signedoffmap.get(commit.hexsha, [""]))
        # Be aware that this is a rough estimation: not all commits
        # signed-off-by Sasha Levin are AUTOSEL patches
        commit_autosel = 1 if "Sasha Levin" in commit_signer else 0

        setcol = self.entries.setdefault
        setcol('Commit_hexsha', []).append(commit.hexsha)
        setcol('Commit_summary', []).append(commit.summary)
        setcol('Commit_datetime', []).append(commit.committed_datetime)
        setcol('Commit_tag', []).append(commit_tag)
        setcol('Commit_signedby', []).append(commit_signer)
        setcol('Commit_latency_upstream_stable_days', []).append(
            commit_latency_us_days)
        setcol('Commit_latency_upstream_stable_days_decimal', []).append(
            commit_latency_us_days_decimal)
        setcol('Commit_upstream_hexsha', []).append(commit_upstream_hexsha)
        setcol('Commit_upstream_committed', []).append(
            commit_upstream_committed)
        setcol('Commit_autosel', []).append(commit_autosel)
        setcol('Badfix_hexsha', []).append(badfix_sha)
        setcol('Badfix_datetime', []).append(badfix_datetime)
        setcol('Badfix_upstream_hexsha', []).append(badfix_upstream_hexsha)
        setcol('Badfix_lifetime_days', []).append(badfix_lifetime_days)
        setcol('Badfix_lifetime_days_decimal', []).append(
            badfix_lifetime_days_decimal)
        setcol('Badfix_tag', []).append(badfix_tag)
        setcol('Badfix_signedby', []).append(badfix_signer)
        setcol('Badfix_upstream_lifetime_days', []).append(
            badfix_upstream_lifetime_days)
        setcol('Badfix_upstream_lifetime_days_decimal', []).append(
            badfix_upstream_lifetime_days_decimal)
        setcol('Found_by', []).append(found_by)
        setcol('In_scope', []).append(inscope)
        setcol('Matched_by', []).append(";".join(matched_by_list))

    def _check_line_badfix_sha(self, line):
        RE_REVERT_SHA = re.compile(
            r'.*[Rr]evert.{0,10}commit.*\s+(?P<sha>[0-9a-f]{5,40})\b')
        RE_FIXES_SHA = re.compile(
            r'.*[Ff]ixes.{0,10}\s+(?P<sha>[0-9a-f]{5,40})\b')
        badfixsha = ""
        match = ""
        matched_by = ""
        if not match:
            # (1) Try matching lines like: "This reverts commit SHA_HERE"
            match = RE_REVERT_SHA.match(line)
            found_by = "revert_sha" if match else ""
        if not match:
            # (2) Try matching lines like: "Fixes: SHA_HERE"
            match = RE_FIXES_SHA.match(line)
            found_by = "fixes_sha" if match else ""
        if match:
            matched_by = found_by
            badfixsha = match.group('sha')
            badfixsha = self._get_long_commit_sha(badfixsha)
            if badfixsha not in self.commitset:
                # The Fixes-tag refers to a commit which is not in the set
                # of commits in the selected branch.
                # In most cases, the Fixes-tag refers to the upstream commit
                # which has been backported into the stable branch.
                upstreamsha = badfixsha
                # Trace back the referenced upstream commit to a commit in
                # the selected branch.
                badfixsha = ""
                fixes = self.mapupstreamtocommit.get(upstreamsha)
                if fixes:
                    # If there are many commits in the selected branch that
                    # refer the same upstream commit, select the last one on
                    # the list.
                    # (Which is the first commit in the select branch that
                    # refers the upstream commit)
                    badfixsha = fixes[-1]
        return (badfixsha, found_by, matched_by)

    def _check_line_badfix_summary(self, line):
        RE_REVERT_SUMMARY = re.compile(
            r'^\s*[Rr]evert\s*[\"\'(](?P<summary>.+)[\"\')]$')
        RE_FIXES_SUMMARY_1 = re.compile(
            r'^\s*[Ff]ixes.{0,10}\s*[0-9a-f]{5,40}:?\s*\(?["\'](?P<summary>.*)["\']\)?')
        RE_FIXES_SUMMARY_2 = re.compile(
            r'^\s*[Ff]ixes.{0,10}\s*[0-9a-f]{5,40}:?\s*\((?P<summary>.*)\)')
        RE_FIXES_SUMMARY_3 = re.compile(
            r'^\s*[Ff]ixes.{0,10}\s*[0-9a-f]{5,40}:?\s+(?P<summary>[^\(\"]+)$')
        badfix = ""
        match = ""
        matched_by = ""
        if not match:
            # (1) Try matching lines like: "Revert: 'summary here'"
            match = RE_REVERT_SUMMARY.match(line)
            found_by = "revert_summary" if match else ""
        if not match:
            # (2) Try matching lines like: "Fixes: SHA ("summary here")"
            match = RE_FIXES_SUMMARY_1.match(line)
            found_by = "fixes_summary_1" if match else ""
        if not match:
            # (3) Try matching lines like: "Fixes: SHA (summary here)"
            match = RE_FIXES_SUMMARY_2.match(line)
            found_by = "fixes_summary_2" if match else ""
        if not match:
            # (4) Try matching lines like: "Fixes: SHA summary here"
            match = RE_FIXES_SUMMARY_3.match(line)
            found_by = "fixes_summary_3" if match else ""
        if match:
            matched_by = found_by
            summary = match.group('summary')
            badfixes = self.summarymap.get(summary)
            if badfixes:
                # If there are many commits in the selected branch that refer
                # the same summary, select the last one on the list.
                # (Which is the first commit in the selected branch with the
                # specific commit summary message)
                # We acknowledge there's a possibility we mix-up commits that
                # have the same subject line, but such cases are rare enough
                # to not have a meaningful impact. The conditions required
                # for the mix-up to occur:
                #  (1) _check_line_badfix_sha() failed to find a match.
                #      That is, the commit SHA based match failed, and we had
                #      to revert to matching summary-lines
                #  (2) There are two or more regressions that have the same
                #      subject line (and the commits are not related)
                badfix = badfixes[-1]
                badfix = self._get_long_commit_sha(badfix)
                if badfix not in self.commitset:
                    badfix = ""
        return (badfix, found_by, matched_by)

    def _build_commitset(self):
        try:
            for commit in list(self.repo.iter_commits(self.rev)):
                sha = commit.hexsha
                self.commitset.add(sha)
        except git.GitCommandError as e:
            sys.stderr.write("Error: %s\n" % e)
            sys.exit(e.status)

    def _build_summarymap(self):
        for commit in list(self.repo.iter_commits(self.rev)):
            summary = commit.summary
            sha = commit.hexsha
            self.summarymap.setdefault(summary, []).append(sha)

    def _build_upstreamindexes(self):
        RE_UPSTREAM_1 = re.compile(
            # Negative lookbehind:
            # Match (1) that is not preceded by (2), (3), (4), or (5)
            # We need this because below is a valid upstream reference:
            #     commit HEXSHA1 upstream.
            # Whereas, this is not a valid upstream reference:
            #     This reverts commit HEXSHA2 which is
            #     commit HEXSHA1 upstream.
            r'(?<!reverts commit [0-9a-f]{40} which is)'    # (2)
            r'(?<!reverts commit [0-9a-f]{40}, which is)'   # (3)
            r'(?<!reverts commit [0-9a-f]{40} which was)'   # (4)
            r'(?<!reverts commit [0-9a-f]{40}, which was)'  # (5)
            r'$'
            r'\s*\[?\s*[Cc]omm?[it]{2}\s*(?P<sha>[0-9a-f]{10,40})\s+[Uu]pst?ream\.?\s*\]?\s*$',  # (1)
            re.MULTILINE)
        RE_UPSTREAM_2 = re.compile(
            r'(?<!reverts commit [0-9a-f]{40} which is)'    # (2)
            r'(?<!reverts commit [0-9a-f]{40}, which is)'   # (3)
            r'(?<!reverts commit [0-9a-f]{40} which was)'   # (4)
            r'(?<!reverts commit [0-9a-f]{40}, which was)'  # (5)
            r'$'
            r'^\s*\[?\s*[Uu]pst?ream\s+[Cc]omm?[it]{2}\s*(?P<sha>[0-9a-f]{40})',  # (1)
            re.MULTILINE)
        for commit in list(self.repo.iter_commits(self.rev)):
            match = ""
            if not match:
                match = RE_UPSTREAM_1.search(commit.message)
            if not match:
                match = RE_UPSTREAM_2.search(commit.message)
            if match:
                upstreamsha = match.group('sha')
                upstreamsha = self._get_long_commit_sha(upstreamsha)
                if not upstreamsha:
                    # _get_long_commit_sha() returns None if
                    # upstreamsha is not in the git tree. We'll ignore
                    # such upstream references.
                    continue
                sha = commit.hexsha
                self.mapupstreamtocommit.setdefault(
                    upstreamsha, []).append(sha)
                self.mapcommittoupstream[sha] = upstreamsha

    def _build_inscopeset(self, inscopefile):
        if not inscopefile:
            return
        with open(inscopefile) as inscopef:
            for line in inscopef:
                # Return first match (assume one hash per line)
                match = re.search(r'[0-9a-f]{12}', line)
                if not match:
                    sys.stderr.write("Warning: inscope line missing hash: %s" % line)
                    continue
                commit = match.group()
                self.inscopeset.add(commit)

    def _build_tagmap(self):
        RE_SHA_TAG = re.compile(
            r'^(?P<sha>[0-9a-f]{40})\srefs/tags/(?P<tag>[^\^]+)')
        try:
            refs = self.repo.git.show_ref("--tags", "-d")
        except git.GitCommandError:
            text = \
                "[+] Warning: unable to determine version information due to " \
                "target repository missing tags"
            print(text)
            refs = ""
        # The commits the tags directly point to
        for line in refs.splitlines():
            match = RE_SHA_TAG.match(line)
            if match:
                sha = match.group('sha')
                tag = match.group('tag')
                self.tagmap.setdefault(sha, []).append(tag)
        # The commits "in between" the tags:
        currtag = ["unknown"]
        for commit in list(self.repo.iter_commits(self.rev)):
            sha = commit.hexsha
            tag = self.tagmap.get(sha, currtag)[0]
            self.tagmap.setdefault(sha, []).append(tag)
            currtag = [tag]

    def _build_signedoffmap(self):
        RE_SIGNEDOFFBY = re.compile(r'^\s*[Ss]igned-off-by\s*[:;]\s*(?P<signer>.+)$')
        for commit in list(self.repo.iter_commits(self.rev)):
            for line in commit.message.splitlines():
                match = RE_SIGNEDOFFBY.match(line)
                if match:
                    signer = match.group('signer')
                    self.signedoffmap.setdefault(commit.hexsha, []).append(signer)

################################################################################


def getargs():
    desc = \
        "Find \"bad fixes\" from a git repository analyzing commits specified "\
        "by REV. "\
        "A Bad fix is a commit introduced in a stable branch, that caused "\
        "regression and was reverted or re-fixed with another "\
        "commit. The script looks for cases where both the regression and the "\
        "fix (or revert) occur in the range of commits specified by REV."

    epil = "Example: ./%s --git-dir ~/linux-stable/ v4.19^..v4.19.65" %\
        os.path.basename(__file__)
    parser = argparse.ArgumentParser(description=desc, epilog=epil)

    help = "revision specifier, see git-rev-parse for viable options. "
    parser.add_argument('REV', nargs=1, help=help)

    help = "file path to git repository, defaults to current working directory"
    parser.add_argument('--git-dir', nargs='?', help=help, default='./')

    help = "set the output file name, default is 'badfixes.csv'"
    parser.add_argument('--out', nargs='?', help=help, default='badfixes.csv')

    help = \
        "file path to patchlist file, which contains commit hashes "\
        "(one per line) that should be considered in-scope. If omitted, "\
        "all commits are considered in-scope."
    parser.add_argument("--inscope", nargs='?', help=help)
    return parser.parse_args()

################################################################################


if __name__ == "__main__":
    if sys.version_info[0] < 3:
        sys.stderr.write("Error: script requires Python 3.x\n")
        sys.exit(1)

    args = getargs()
    rev = args.REV[0]
    repo = args.git_dir
    outfile = args.out
    inscopefile = args.inscope

    repo = repo if repo.endswith(".git") else os.path.join(repo, ".git")
    if(not (os.path.isdir(repo))):
        sys.stderr.write("Error: not a git repository: %s\n" % repo)
        sys.exit(1)

    print("[+] Reading commit history, this might take a few minutes")
    stats = GitStatistics(repo, rev, inscopefile)
    stats.find_badfixes()

    stats.to_csv(outfile)
    print("[+] Wrote file: %s" % outfile)

################################################################################
