<!--
SPDX-License-Identifier: CC-BY-SA-4.0
-->

# New Repository Notes

A new GitHub project comes with a Readme that should be filled out to help navigate the site and understand it's purpose.

## Security configuration

The GitHub project repository is not secure by default and a lot of online examples may not consider security posture.
The following are a few tips to improve the general security posture when starting a new repository.

### Repository settings

- Enable **"Require approval for all outside collaborators"** under Actions > General > Fork pull request workflows. This prevents automated workflow execution from unknown contributors.
- Add a `CODEOWNERS` file to require maintainer review on security-sensitive paths, especially `.github/workflows/*`.

### Workflow hardening

- **Triggers** — Prefer `pull_request` over `pull_request_target`. The latter runs with base branch privileges and can execute untrusted fork code.
- **Permissions** — Declare an explicit top-level `permissions` block in every workflow. Default to `contents: read` and only grant `write` where specifically needed.
- **Pin actions by SHA** — Use full commit hashes instead of mutable tags (e.g., `actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1` instead of `actions/checkout@v4`).
- **Disable credential persistence** — Set `persist-credentials: false` on checkout steps to limit token exposure.
- **Prevent script injection** — Never interpolate user-controlled values (`github.event.pull_request.head.ref`, PR titles, etc.) directly into `run:` blocks. Pass them through environment variables instead.

### Dependency and secret management

- Configure [Dependabot](https://docs.github.com/en/code-security/dependabot) for both application dependencies and `github-actions` to receive automated PRs for version bumps and CVE fixes.
- Use short-lived credentials (OIDC) where possible. Scope secrets to specific environments or jobs.
- Rotate any credentials immediately if a workflow compromise is suspected.

### Monitoring

- Enable repository audit logging.
- Watch for unexpected workflow triggers, especially from new or bot accounts.

### References

- [GitHub — Security hardening for GitHub Actions](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)
- [OpenSSF — GitHub Actions Security Best Practices](https://best.openssf.org/developers/github-actions)
- [OpenSSF — OSPS Baseline](https://best.openssf.org/)
- [ELISA AeroWG — GitHub Actions Security Best Practices](https://github.com/elisa-tech/wg-aerospace/blob/main/docs/github-actions-security-best-practices.md) (detailed reference with OSPS alignment mapping)

## Linting

The super linter project is one option to help with consistency and security of repository content.
The GitHub action linter specifically can help with setting **least privilege** and prevent unintended workflow privilege inheritance by a forked repository.
This is an example lint configuration that [runs as a workflow](https://github.com/elisa-tech/wg-aerospace/blob/main/.github/workflows/lint.yml).

The following can be setup locally to lint material before pushing to the repository (this assumes you have setup [a configuration env file](https://github.com/elisa-tech/wg-aerospace/blob/main/.github/super-linter.env)):

```bash
# Run once after checkout to setup the hook
cat > .git/hooks/pre-push <<'EOM'
#!/bin/sh

# Run the super-linter Docker container as a pre-push hook

echo "Running Super-Linter via Docker pre-push hook..."
docker run -e RUN_LOCAL=true -e LOG_LEVEL=ERROR --env-file "./.github/super-linter.env" -v "$(pwd)":/tmp/lint --rm ghcr.io/super-linter/super-linter:latest

# Check the exit status of the docker command.
# If it is non-zero, the linter failed and the push should be aborted.
if [ $? -ne 0 ]; then
  echo "Super-Linter failed. Push aborted."
  exit 1
else
  echo "Super-Linter passed. Proceeding with push."
  exit 0
fi
EOM
chmod +x .git/hooks/pre-push
```

## Licensing checks

The reuse tool can be used as part of automation or manually to help ensure the licensing is tagged on content.

- Add a license description file using the [`docker run --rm --volume $(pwd):/data fsfe/reuse download --all`](https://github.com/fsfe/reuse-tool?tab=readme-ov-file#usage) or manually under `./LICENSES/`
- Add any specific exception clarification language to [LICENSE](./LICENSE) or the specific file(s) under the license header.
- Locally cleanup licensing on your contribution - `docker run --rm --volume $(pwd):/data fsfe/reuse` to get a report.
  - Then if you are "not compliant", either manually add the SPDX headers or use the `reuse annotate` feature to help you. `reuse` does have a `--recursive` option that can be used for folders, however it marks everything.
  - Example: Updating individual markdown files - `docker run --rm --volume $(pwd):/data fsfe/reuse annotate --license CC-BY-SA-4.0 <filename>`
  - Example: Add details for binary files and items like `json` - `docker run --rm --volume $(pwd):/data fsfe/reuse annotate --license CC-BY-SA-4.0 --fallback-dot-license <filename>` . This creates a file with a `.license` suffix that has the SPDX tag

The tool has [various features](https://github.com/fsfe/reuse-tool?tab=readme-ov-file#usage) including automatically adding a license descriptions under `LICENSE/` if you had a new license type.

## Copyright

Some note should be included as part of the Readme or Contributing material about the Copyright practice. As an example:

```text
This project follows the [Developer Certificate of Origin](https://developercertificate.org/) approach for any contributions.
[How to add a contribution sign off.](https://tac.lfenergy.org/process/contribution_guidelines.html#contribution-sign-off)

All content is copyright as follows, unless noted in the individual file.
See [Linux Foundation copyright guidance](https://www.linuxfoundation.org/blog/blog/copyright-notices-in-open-source-software-projects) for guidance on this top level copyright claim that simplifies the developer workflow (i.e., it uses DCO to associate the claim.)

Copyright (c) The ELISA Aerospace Working Group Authors

Copyright (c) The ELISA Aerospace Working Group Contributors

Copyright (c) Contributors to the ELISA Aerospace Working Group

Note: Please refer to the [ELISA Technical Charter section 7](https://elisa.tech/wp-content/uploads/sites/19/2020/08/elisa_technical_charter_082620.pdf) for discussion on Intellectual Property roles related to Author vs Contributor.
```

### DCO sign-off in practice

Contributors must add a `Signed-off-by` line to every commit using the `--signoff` flag:

```bash
bash
git commit --signoff -m "Your commit message"
```

#### Fixing missed sign-offs

GitHub will flag pull requests with unsigned commits via the DCO check. To retroactively sign off, rebase with `--signoff`. For example, to fix the last 3 commits:

```bash
bash
git rebase HEAD~3 --signoff
git push origin --force

For a single most-recent commit:

bash
git commit --amend --signoff --no-edit
git push origin --force-with-lease
```

See the [ELISA Automotive WG contribution workflow](https://github.com/elisa-tech/wg-automotive#signing-off-and-dco) for an additional example.
