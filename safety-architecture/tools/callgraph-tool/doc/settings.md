<!--
SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)

SPDX-License-Identifier: Apache-2.0
-->

# Settings File

## Using program options through file

All command line options can also be used through the settings file. In that case the callgraph tool receives all the settings through a JSON file with a single command line option _--file_. Short option names can also be used, but in that case, they need to begin with a single dash (see build log format option _-blf_ in the example bellow). Long options are also accepted with double dashes but this is not mandatory.

All options are placed under the _args_ object in form of a dictionary where key is the command line option and the value is the user setting for that option. In case that the option accepts multiple arguments these can be specified with the list (see _build_exclude_ option in the example bellow). In cases where the option does not require input value (action options) the value is empty string (see option view in the example bellow).

```
{
    "args":{
        "build": "/home/user/work/linux-5.5",
        "-blf": "ll_clang",
        "build_exclude": ["scripts", "tools"],
        "fast_build": ""
    } 
}
```

The settings file can be used to create reproducable environments. It also enables further customization of the tool behaviour without cluttering the command line too much.
