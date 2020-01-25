<!--
SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# Linux Kernel Regression Data


Below sections summarize and visualize the data collected, as well
as provide links to download the raw data in CSV format.
        
## Data

|      Version       |                                       Regression HTML Charts                                       |                        Regression CSV Database                         |
|:------------------:|:--------------------------------------------------------------------------------------------------:|:----------------------------------------------------------------------:|
| v4.19 to v4.19.98  |  [linux_stable__v4.19-v4.19.98.csv__summary.html](linux_stable__v4.19-v4.19.98.csv__summary.html)  |  [linux_stable__v4.19-v4.19.98.csv](linux_stable__v4.19-v4.19.98.csv)  |
| v4.14 to v4.14.167 | [linux_stable__v4.14-v4.14.167.csv__summary.html](linux_stable__v4.14-v4.14.167.csv__summary.html) | [linux_stable__v4.14-v4.14.167.csv](linux_stable__v4.14-v4.14.167.csv) |
|  v4.9 to v4.9.211  |   [linux_stable__v4.9-v4.9.211.csv__summary.html](linux_stable__v4.9-v4.9.211.csv__summary.html)   |   [linux_stable__v4.9-v4.9.211.csv](linux_stable__v4.9-v4.9.211.csv)   |
|  v4.4 to v4.4.211  |   [linux_stable__v4.4-v4.4.211.csv__summary.html](linux_stable__v4.4-v4.4.211.csv__summary.html)   |   [linux_stable__v4.4-v4.4.211.csv](linux_stable__v4.4-v4.4.211.csv)   |

## Missing Annotations

|      Version       |  Commits  |  Commits_tagged  |  Commits_tagged (%)  |
|:------------------:|:---------:|:----------------:|:--------------------:|
| v4.19 to v4.19.98  |   10910   |       4962       |         45%          |
| v4.14 to v4.14.167 |   15061   |       6389       |         42%          |
|  v4.9 to v4.9.211  |   15327   |       6083       |         40%          |
|  v4.4 to v4.4.211  |   13985   |       4985       |         36%          |

## Regression Lifetimes

|      Version       |  Regressions <br>(lifetime any)  |  Regressions <br>(lifetime == 0)  |  Regressions <br>(lifetime < 0)  |  Regressions <br>(lifetime <= 0)(%)  |
|:------------------:|:--------------------------------:|:---------------------------------:|:--------------------------------:|:------------------------------------:|
| v4.19 to v4.19.98  |               591                |                165                |                5                 |                 29%                  |
| v4.14 to v4.14.167 |               1045               |                266                |                4                 |                 26%                  |
|  v4.9 to v4.9.211  |               1026               |                245                |                5                 |                 24%                  |
|  v4.4 to v4.4.211  |               894                |                251                |                2                 |                 28%                  |

## Multiple Fixes to One Regression

|      Version       |  Regressions <br>(lifetime > 0)  |  Regressions <br>(Fixes == 1)  |  Regressions <br>(Fixes == 2)  |  Regressions <br>(Fixes == 3)  |  Regressions <br>(Fixes >= 4)  |
|:------------------:|:--------------------------------:|:------------------------------:|:------------------------------:|:------------------------------:|:------------------------------:|
| v4.19 to v4.19.98  |               421                |              359               |               26               |               2                |               1                |
| v4.14 to v4.14.167 |               775                |              589               |               59               |               12               |               7                |
|  v4.9 to v4.9.211  |               776                |              631               |               48               |               10               |               4                |
|  v4.4 to v4.4.211  |               641                |              523               |               37               |               7                |               5                |