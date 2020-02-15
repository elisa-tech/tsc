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

## Summary

|      Version       |  Commits  |  Commits Tagged (%)  |  Regression <br>Rate (%)  |  Regression Rate<br>Range Estimation (%)  |  Zero-Lifetime Regressions <br>(lifetime <= 0) (%)  |  Half-life (days)  |
|:------------------:|:---------:|:--------------------:|:-------------------------:|:-----------------------------------------:|:---------------------------------------------------:|:------------------:|
| v4.19 to v4.19.98  |   10901   |         45%          |           3.9%            |                3.6% - 8.5%                |                         29%                         |         63         |
| v4.14 to v4.14.167 |   15049   |         42%          |           5.1%            |               4.4% - 12.2%                |                         26%                         |         77         |
|  v4.9 to v4.9.211  |   15308   |         40%          |           5.1%            |               4.5% - 12.8%                |                         24%                         |         91         |
|  v4.4 to v4.4.211  |   13973   |         36%          |           4.6%            |               4.1% - 12.9%                |                         28%                         |         80         |

## Missing Annotations

|      Version       |  Commits  |  Commits tagged  |  Commits tagged (%)  |
|:------------------:|:---------:|:----------------:|:--------------------:|
| v4.19 to v4.19.98  |   10901   |       4948       |         45%          |
| v4.14 to v4.14.167 |   15049   |       6368       |         42%          |
|  v4.9 to v4.9.211  |   15308   |       6047       |         40%          |
|  v4.4 to v4.4.211  |   13973   |       4962       |         36%          |

## Regression Lifetimes

|      Version       |  Regressions <br>(lifetime any)  |  Regressions <br>(lifetime == 0)  |  Regressions <br>(lifetime < 0)  |  Regressions <br>(lifetime <= 0) (%)  |
|:------------------:|:--------------------------------:|:---------------------------------:|:--------------------------------:|:-------------------------------------:|
| v4.19 to v4.19.98  |               591                |                165                |                5                 |                  29%                  |
| v4.14 to v4.14.167 |               1045               |                266                |                4                 |                  26%                  |
|  v4.9 to v4.9.211  |               1025               |                244                |                5                 |                  24%                  |
|  v4.4 to v4.4.211  |               893                |                250                |                2                 |                  28%                  |

## Multiple Fixes to One Regression

|      Version       |  Regressions <br>(lifetime > 0)  |  Regressions <br>(Fixes == 1)  |  Regressions <br>(Fixes == 2)  |  Regressions <br>(Fixes == 3)  |  Regressions <br>(Fixes >= 4)  |
|:------------------:|:--------------------------------:|:------------------------------:|:------------------------------:|:------------------------------:|:------------------------------:|
| v4.19 to v4.19.98  |               421                |              359               |               26               |               2                |               1                |
| v4.14 to v4.14.167 |               775                |              588               |               58               |               13               |               7                |
|  v4.9 to v4.9.211  |               776                |              631               |               48               |               10               |               4                |
|  v4.4 to v4.4.211  |               641                |              523               |               37               |               7                |               5                |