<!--
SPDX-FileCopyrightText: 2020 callgraph-tool authors. All rights reserved

SPDX-License-Identifier: Apache-2.0
-->

# License and Copyright information in the callgraph-tool

We are doing our best to keep all the licensing and copyright information in place.
Please follow the guidelines bellow for your contributions. The requirement is installation
of `reuse` tool:
```
pip install reuse
```

## Contributions

All the copyright holders are kept in top-level [AUTHORS](../../AUTHORS) file. The information
about the people (developers) who contribute (or have contributed) the project are kept in 
[CONTRIBUTORS](../../CONTRIBUTORS) file. Make sure that you add your name in the first PR to
the tool.

## Licenses
We use Apache-2.0 license for all the files in the repository. The exception is `crix` core,
where original LLVM license is kept. This is available under name `LicenseRef-LLVM.txt` in the
[LICENSES](../../LICENSES) directory. 


## Guidelines

If you are modifying the existing file then there is in most cases no need for any action.
When adding the new file it is required to add licensing and copyright information. This can
be either done by simply copying the copyright and license information from other files in the
same format of using the `reuse` tool:
```
reuse addheader <NAME_OF_NEW_FILE>\
    --copyright "callgraph-tool authors. All rights reserved"\
    --license Apache-2.0
    --year <CURRENT_YEAR>\
    --style <FILE_STYLE>\
```

If you are adding multiple files or files that don't have editable header you can license the
entire directory  by adding the appropriate entry in ./reuse/dep5 file. For example, the copyright
and license information for entire contents of `doc` directory can be defined as:
```
Files: doc/*
Copyright: 2020 callgraph-tool authors. All rights reserved.
License: Apache-2.0
```

Before committing/pushing the file make sure that the reuse conformance is kept with:
```
reuse lint
```
There should be no warnings or errors in the tool output.
