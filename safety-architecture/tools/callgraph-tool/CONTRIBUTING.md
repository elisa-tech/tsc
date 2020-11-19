<!--
SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)

SPDX-License-Identifier: Apache-2.0
-->

# Contributing to Callgraph Tool
We appreciate your input! If you want to contribute to the project send us a pull request following the guidelines in this document.

## We Develop with Github
We use github to host code, to track issues and feature requests, as well as accept pull requests. 
Updating and extending docs as well as adding new tests is a good way to start contributing the project.
You might also want to check the [issue tracker](https://github.com/elisa-tech/workgroups/labels/callgraph-tool) for some known problems that are worth considering. 

## Pull requests
Pull requests are the best way to get the proposed changes into the codebase (we use [Github Flow](https://guides.github.com/introduction/flow/index.html)). 
Follow the checklists bellow:

1. Go to project home [page](https://github.com/elisa-tech/workgroups) and click the `Fork` button in the top-right corner. This will create
a `https://github.com/YOUR_GITHUB_USERNAME/workgroups` repository.

2. Checkout main repository into your working directory: 

```
cd $WORKDIR
git clone https://github.com/elisa-tech/workgroups.git
```

3. Add the fork as an additional origin:

```
git remote add my-origin https://github.com/YOUR_GITHUB_USERNAME/workgroups.git
git fetch my-origin
git checkout -b dev-branch my-origin/master
```

4. Develop the feature or fix a bug:
* If you've added code that should be tested, add tests.
* Ensure the test suite passes: check the main makefile target `make pre-push` still passes after your changes
* Ensure that you are in sync with the master branch
* Push the changes in your remote branch

5. Go to https://github.com/elisa-tech/workgroups. There should be a green `Compare & pull request` button. Use it to crate a pull request.

6. Wait for a review and acknowledge the possible comments.

## Commits

Commit messages should contain of short one-line description, optionally followed by an empty line and more verbose description. All the commits must be
signed. Use `git commit -s -m COMMIT_MESSAGE` to add a signature to your commit.

## Report bugs using Github's [issues](https://github.com/elisa-tech/workgroups/issues)
We use GitHub issues to track public bugs. Report a bug by [opening a new issue](https://github.com/elisa-tech/workgroups/issues).
The title of the issue should start with CG: and contain callgraph-tool label.

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

## Use a Consistent Coding Style
* You can try running `make style` for style unification

## License
By contributing, you agree that your contributions will be licensed under Apache 2.0 License.
