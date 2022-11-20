#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2019 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
# SPDX-FileCopyrightText: 2022 Henri Rosten
#
# SPDX-License-Identifier: GPL-2.0-only

import re
import git
import csv
import argparse
import os
import sys
import pickle
from pathlib import Path

import pandas as pd
from collections import OrderedDict
from datetime import datetime, timedelta

################################################################################

SCRIPT_DIR = Path(os.path.dirname(os.path.realpath(__file__)))

################################################################################


class GitStatistics:

    def __init__(self, gitdir, rev, indexfile, nomerges):
        self.gitdir = gitdir
        # Statistics are generated based on the git commit entries in the
        # specified git repository that match the given revision (range)
        self.rev = rev
        # Dictionary to store the report entries
        # Key: column header, Value: list of entries
        self.entries = {}
        # GitPython Repo object
        self.repo = git.Repo(self.gitdir)
        # Set of commit hashes in self.repo in range rev
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
        # Map commit hash to tag name
        # Key: commit hash, Value: tag name
        self.tagmap = self._build_tagmap(rev=rev)
        # Map commit hash to list of names who signed-off the commit
        # Key: commit hash, Value: list of names
        self.signedoffmap = {}
        self._build_signedoffmap()
        # Map upstream commit hash to upstream tag name
        self.upstreamtagmap = {}
        # The name of the file that stores the index on the disk.
        self.indexfilename = None if nomerges else indexfile
        # "index_on_disk" contains the (de-)serialized index data
        self.index_on_disk = {}
        # "index" is dictionary that maps upstream_hexsha to merge commit
        self.index = {}
        self._load_index()

    def find_badfixes(self):
        for commit in list(self.repo.iter_commits(self.rev, reverse=True)):
            self._find_badfix(commit)

        # Build the upstream tagmap now when the 'Commit_upstream_hexsha'
        # is known
        upstream_hexshas = self.entries['Commit_upstream_hexsha']
        self.upstreamtagmap = self._build_tagmap(hexsha_list=upstream_hexshas)
        self._stamp_upstream_tags()

        if self.indexfilename:
            print("[+] Finding merge commits, this might take several minutes "
                  "if the index is not up-to-date")
            self._find_upstream_merge_commits()
            self._add_final_columns()
            self._save_index()

    def to_csv(self, filename):
        df = pd.DataFrame(self.entries)
        # Sort columns alphabetically
        df = df.sort_index(axis=1)
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
                badfixsha, found_by, matched_by = self._check_line_badfix_summary(
                    line)
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
            badfix_lifetime_days = int(
                round(badfix_timedelta / timedelta(days=1)))
            badfix_lifetime_days_decimal = badfix_timedelta / timedelta(days=1)
            badfix_tag = self.tagmap.get(badfix_commit.hexsha, "unknown")
            badfix_sha = badfix_commit.hexsha
            badfix_datetime = badfix_commit.committed_datetime
            badfix_signer = ";".join(
                self.signedoffmap.get(badfix_commit.hexsha, [""]))

        badfix_upstream_hexsha = self.mapcommittoupstream.get(badfix_sha, "")
        commit_upstream_hexsha = self.mapcommittoupstream.get(
            commit.hexsha, "")
        badfix_upstream_commit = self._get_commit(badfix_upstream_hexsha)
        commit_upstream_commit = self._get_commit(commit_upstream_hexsha)
        if not badfix_upstream_commit or not commit_upstream_commit:
            badfix_upstream_lifetime_days_decimal = ""
            badfix_upstream_lifetime_days = ""
            badfix_upstream_datetime = ""
        else:
            badfix_upstream_datetime = badfix_upstream_commit.committed_datetime
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

        commit_tag = self.tagmap.get(commit.hexsha, "unknown")
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
        setcol('Commit_upstream_datetime', []).append(
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
        setcol('Badfix_upstream_datetime', []).append(badfix_upstream_datetime)

        setcol('Found_by', []).append(found_by)
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

    def _load_index(self):
        # Load an earlier index from the disk: index is dictionary that maps
        # upstream_hexsha to merge commit
        if self.indexfilename and os.path.isfile(self.indexfilename):
            with open(self.indexfilename, 'rb') as handle:
                self.index_on_disk = pickle.load(handle)
                self.index = self.index_on_disk.copy()
                fname = os.path.abspath(os.path.realpath(handle.name))
                print("[+] Note: using earlier index file: \"%s\"" % fname)

    def _save_index(self):
        # Save the index to disk, keeping the mappings required to later
        # re-build the data we collected now, while also retaining the data
        # that was originally available in the index
        keys = \
            self.entries['Commit_hexsha'] +\
            self.entries['Commit_upstream_hexsha']
        short_index = dict((k, self.index[k]) for k in keys if k in self.index)
        # Merge dictionaries short_index and index_on_disk
        self.index_on_disk.update(short_index)
        # Serialize the merged dictionary using pickle
        if self.indexfilename:
            with open(self.indexfilename, 'wb') as handle:
                pickle.dump(self.index_on_disk, handle,
                            protocol=pickle.HIGHEST_PROTOCOL)
                fname = os.path.abspath(os.path.realpath(handle.name))
                print("[+] Note: updated index to file: \"%s\"" % fname)

    def _find_merged_tree(self, merge_commit):
        if not merge_commit:
            return ""
        RE_MERGE = re.compile(
            r'^\s*Merge\s.*(?P<tree>(?:git:|https:|ssh:|\(|gitolite).+)\s*$')
        tree = ""
        summary = merge_commit.summary
        match = RE_MERGE.match(summary)
        if match:
            tree = match.group('tree')
        return tree

    def _stamp_upstream_merge_commit(self, merge_hexsha):
        setcol = self.entries.setdefault
        merge_commit = self._get_commit(merge_hexsha)
        merge_commit_dt = merge_commit.committed_datetime if merge_commit else ""

        # Find the source tree from the merge_commit message
        tree = self._find_merged_tree(merge_commit)

        setcol("Commit_upstream_merge_hexsha", []).append(merge_hexsha)
        setcol("Commit_upstream_merge_datetime", []).append(merge_commit_dt)
        setcol("Commit_upstream_merge_tree", []).append(tree)

    def _stamp_badfix_upstream_merge_commit(
            self, badfix_merge_hexsha, fix_merge_hexsha):
        setcol = self.entries.setdefault
        badfix_merge_commit = self._get_commit(badfix_merge_hexsha)
        fix_merge_commit = self._get_commit(fix_merge_hexsha)
        badfix_dt = badfix_merge_commit.committed_datetime if badfix_merge_commit else ""
        fix_dt = fix_merge_commit.committed_datetime if fix_merge_commit else ""
        if not badfix_dt or not fix_dt:
            badfix_upstream_merge_lifetime_days_decimal = ""
            badfix_upstream_merge_lifetime_days = ""
        else:
            badfix_upstream_merge_timedelta = fix_dt - badfix_dt
            badfix_upstream_merge_lifetime_days_decimal = \
                badfix_upstream_merge_timedelta / timedelta(days=1)
            badfix_upstream_merge_lifetime_days = \
                int(round(badfix_upstream_merge_timedelta / timedelta(days=1)))
        setcol("Badfix_upstream_merge_hexsha", []).append(badfix_merge_hexsha)
        setcol("Badfix_upstream_merge_datetime", []).append(badfix_dt)
        setcol("Badfix_upstream_merge_lifetime_days", []).append(
            badfix_upstream_merge_lifetime_days)
        setcol("Badfix_upstream_merge_lifetime_days_decimal", []).append(
            badfix_upstream_merge_lifetime_days_decimal)

    def _stamp_upstream_merge_latency(
            self, commit_datetime, commit_upstream_merge_datetime):

        setcol = self.entries.setdefault
        if not commit_datetime or not commit_upstream_merge_datetime:
            commit_latency_ums_days = ""
            commit_latency_ums_days_decimal = ""
        if commit_datetime and commit_upstream_merge_datetime:
            commit_latency_ums_timedelta = \
                commit_datetime - commit_upstream_merge_datetime
            commit_latency_ums_days_decimal = \
                commit_latency_ums_timedelta / timedelta(days=1)
            commit_latency_ums_days = \
                int(round(commit_latency_ums_timedelta / timedelta(days=1)))

        setcol("Commit_latency_upstream_merge_stable_days", []).append(
            commit_latency_ums_days)
        setcol("Commit_latency_upstream_merge_stable_days_decimal", []).append(
            commit_latency_ums_days_decimal)

    def _stamp_upstream_tags(self):
        setcol = self.entries.setdefault
        for commit in self.entries['Commit_upstream_hexsha']:
            tag = self.upstreamtagmap.get(commit, "")
            setcol('Commit_upstream_tag', []).append(tag)

        setcol = self.entries.setdefault
        for commit in self.entries['Badfix_upstream_hexsha']:
            tag = self.upstreamtagmap.get(commit, "")
            setcol('Badfix_upstream_tag', []).append(tag)

    def _add_final_columns(self):
        number_of_rows = len(self.entries['Commit_hexsha'])

        for i in range(number_of_rows):
            badfix_upstream_hexsha = self.entries['Badfix_upstream_hexsha'][i]
            badfix_merge_hexsha = ""
            if badfix_upstream_hexsha:
                badfix_merge_hexsha = self.index.get(
                    badfix_upstream_hexsha, "")
            commit_upstream_merge_hexsha = self.entries[
                'Commit_upstream_merge_hexsha'][i]
            self._stamp_badfix_upstream_merge_commit(
                badfix_merge_hexsha,
                commit_upstream_merge_hexsha)

            commit_datetime = self.entries['Commit_datetime'][i]
            commit_upstream_merge_datetime = self.entries['Commit_upstream_merge_datetime'][i]
            self._stamp_upstream_merge_latency(
                commit_datetime,
                commit_upstream_merge_datetime)

            i += 1

    def _find_upstream_merge_commits(self):
        # Iterate all the upstream commits and attempt to find the merge
        # commit that originally brought in the commit to the upstream
        # branch
        for upstream_hexsha in self.entries['Commit_upstream_hexsha']:
            merge_commit = ""
            upstream_tag = self.upstreamtagmap.get(upstream_hexsha, "")

            # We cannot determine the merge commit if upstream_hexsha or
            # upstream_tag are missing
            if not upstream_hexsha or not upstream_tag:
                self._stamp_upstream_merge_commit("")
                continue

            # Use the value from the index if it's already there
            if upstream_hexsha in self.index:
                merge_commit = self.index[upstream_hexsha]
                self._stamp_upstream_merge_commit(merge_commit)
                continue

            # Otherwise, try to find the merge commit as explained in:
            # https://stackoverflow.com/questions/8475448/
            ancestry_path_list = self.repo.git.rev_list(
                "%s..%s" % (upstream_hexsha, upstream_tag),
                ancestry_path=True, merges=True).split()

            first_parent_set = set(self.repo.git.rev_list(
                "%s..%s" % (upstream_hexsha, upstream_tag),
                first_parent=True, merges=True).split())

            for commit in reversed(ancestry_path_list):
                if commit in first_parent_set:
                    merge_commit = commit
                    break

            if merge_commit:
                # What commits were merged with the suspected merge_commit?
                merged_list = self.repo.git.rev_list(
                    "%s^1..%s^2" % (merge_commit, merge_commit)).split()

                if upstream_hexsha not in set(merged_list):
                    # We end up here if upstrem_hexsha was a direct commit to
                    # the target branch, a fast forward merge, or some
                    # other corner case. For all these cases, we simply
                    # leave the merge_commit empty. To update the index
                    # with the information that upstream_hexsha is not
                    # associated to any known merge_commit, we manually
                    # insert the upstream_hexsha to the merged_list and mark
                    # merge_commit as empty:
                    merge_commit = ""
                    merged_list = [upstream_hexsha]
                    # print("[+] Note: no merge found: %s" % upstream_hexsha)

                # Update the index
                # Store all the commits merged with merge_commit into an index:
                # Key: upstream_hexsha
                # Value: merge commit
                for commit in merged_list:
                    self.index[commit] = merge_commit

            # "stamp" the merge_commit (or empty value if it wasn't found)
            self._stamp_upstream_merge_commit(merge_commit)

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
            # (1)
            r'\s*\[?\s*[Cc]omm?[it]{2}\s*(?P<sha>[0-9a-f]{10,40})\s+[Uu]pst?ream\.?\s*\]?\s*$',
            re.MULTILINE)
        RE_UPSTREAM_2 = re.compile(
            r'(?<!reverts commit [0-9a-f]{40} which is)'    # (2)
            r'(?<!reverts commit [0-9a-f]{40}, which is)'   # (3)
            r'(?<!reverts commit [0-9a-f]{40} which was)'   # (4)
            r'(?<!reverts commit [0-9a-f]{40}, which was)'  # (5)
            r'$'
            # (1)
            r'^\s*\[?\s*[Uu]pst?ream\s+[Cc]omm?[it]{2}\s*(?P<sha>[0-9a-f]{40})',
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

    def _build_tagmap(self, rev=None, hexsha_list=[]):
        # Select commits based on revision range rev if specified
        if rev:
            hexsha_list = [str(i) for i in self.repo.iter_commits(rev)]
        # Otherwise, use the list of commits specified in hexsha_list
        if len(hexsha_list) <= 0:
            sys.stderr.write("Error: no commits in range: %s\n" % rev)
            sys.exit(1)
        # Remove non-unique elements preserving order
        tempdict = OrderedDict.fromkeys(hexsha_list)
        # Remove empty key if there is one
        tempdict.pop('', None)
        hexsha_list = list(tempdict)

        # We need to split the list into smaller lists and process
        # each sublist separately to not exceed the argument list
        # length limit
        hexsha_list_chunks = _split_list(hexsha_list, 10000)
        gitout = ''
        # Get the tags by calling git describe --contains for the list of commits
        for hexsha_chunk in hexsha_list_chunks:
            _status, out, err = self.repo.git.describe(
                hexsha_chunk,
                always=True,
                contains=True,
                with_extended_output=True)

            if err:
                # git describe might fail to find tags for commits
                # if the hexsha is incorrect. In such cases, git
                # runs successfully but outputs to stderr an error
                # message such as the following:
                #   "Could not get object for HEXSHA. Skipping.""
                # Here, we match such lines from the stderr and remove
                # the matching HEXSHAs from the hexsha_list
                err_list = re.findall(
                    r'Could not get object for ([0-9a-f]{10,40})',
                    err, re.MULTILINE)
                hexsha_list = [i for i in hexsha_list if i not in err_list]
            gitout += "\n"+out

        # Verify the resulting list of tags has as many elements as the
        # hexsha_list: that for each commit we found the tag
        tag_list = gitout.strip().splitlines()
        if tag_list and hexsha_list and (len(hexsha_list) != len(tag_list)):
            print("hexsha: %s != tag: %s" % (len(hexsha_list), len(tag_list)))
            sys.stderr.write(
                "Error: number of hexshas and tags does not match\n")
            sys.exit(1)

        # Build the tagmap:
        # Key: commit hexsha; Value: first tag that contains commit hexsha
        tagmap = {}
        pattern = re.compile(r'\b[0-9a-f]{10,40}\b')
        match = None
        for tag, hexsha in zip(tag_list, hexsha_list):
            # We used option --always in git describe, which makes the git
            # describe return commit hexsha if it fails to find the containing
            # tag. Here, we check if the tag looks like a hexsha value.
            # If it does, we assume it means the git describe --contains
            # failed to find the tag for this commit, and will not include
            # the value to the tagmap
            match = pattern.match(tag)
            if match:
                continue
            # Ignore everything after (and including) the
            # first '~' from the tag,
            # so e.g. 'v5.2-rc4~12^2~1^2~1^2~5' becomes 'v5.2-rc4'
            tag = tag.split('~', 1)[0]
            # From the resulting string, ignore everything after (and including)
            # the first '^'. This needs to be done, because annotated tags
            # are prefixed with '^0',
            # so e.g. 'v5.2^0' becomes 'v5.2'
            tagmap[hexsha] = tag.split('^', 1)[0]
        return tagmap

    def _build_signedoffmap(self):
        RE_SIGNEDOFFBY = re.compile(
            r'^\s*[Ss]igned-off-by\s*[:;]\s*(?P<signer>.+)$')
        for commit in list(self.repo.iter_commits(self.rev)):
            for line in commit.message.splitlines():
                match = RE_SIGNEDOFFBY.match(line)
                if match:
                    signer = match.group('signer')
                    self.signedoffmap.setdefault(
                        commit.hexsha, []).append(signer)


################################################################################

def _split_list(items, limit):
    return [items[i:i + limit] for i in range(0, len(items), limit)]


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
        "set the index file name, default is 'index.pickle' in the "\
        "directory containing the script "\
        "(\"index\" is a dictionary that maps hexsha to merge "\
        "commit; the script serializes/de-serializes the dictionary "\
        "in an attempt to avoid the relatively costly operation "\
        "of finding the merge "\
        "commit information). Note: the script will create "\
        "the index file if "\
        "it doesn't exist. Otherwise, the script updates the given "\
        "index file appending "\
        "any new merge commit mappings to the specified file."
    index_pickle = SCRIPT_DIR / "index.pickle"
    parser.add_argument(
        '--index-file', nargs='?', help=help, default=index_pickle)

    help = \
        "setting this flag changes the output csv so that merge-related " \
        "datapoints will not be included into the output. This will " \
        "improve the script execution time, due to completely " \
        "disabling the relatively costly operation of finding the merge " \
        "commit information."
    parser.add_argument('--no-merge-datapoints',
                        help=help, action='store_true')

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
    indexfile = args.index_file
    nomerges = args.no_merge_datapoints

    repo = repo if repo.endswith(".git") else os.path.join(repo, ".git")
    if (not (os.path.isdir(repo))):
        sys.stderr.write("Error: not a git repository: %s\n" % repo)
        sys.exit(1)

    print("[+] Reading commit history, this might take a few minutes")
    stats = GitStatistics(repo, rev, indexfile, nomerges)
    stats.find_badfixes()

    stats.to_csv(outfile)
    print("[+] Wrote file: %s" % outfile)

################################################################################
