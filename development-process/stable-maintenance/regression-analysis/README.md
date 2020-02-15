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
| v4.19 to v4.19.104 | [linux_stable__v4.19-v4.19.104.csv__summary.html](linux_stable__v4.19-v4.19.104.csv__summary.html) | [linux_stable__v4.19-v4.19.104.csv](linux_stable__v4.19-v4.19.104.csv) |
| v4.14 to v4.14.171 | [linux_stable__v4.14-v4.14.171.csv__summary.html](linux_stable__v4.14-v4.14.171.csv__summary.html) | [linux_stable__v4.14-v4.14.171.csv](linux_stable__v4.14-v4.14.171.csv) |
|  v4.9 to v4.9.214  |   [linux_stable__v4.9-v4.9.214.csv__summary.html](linux_stable__v4.9-v4.9.214.csv__summary.html)   |   [linux_stable__v4.9-v4.9.214.csv](linux_stable__v4.9-v4.9.214.csv)   |
|  v4.4 to v4.4.214  |   [linux_stable__v4.4-v4.4.214.csv__summary.html](linux_stable__v4.4-v4.4.214.csv__summary.html)   |   [linux_stable__v4.4-v4.4.214.csv](linux_stable__v4.4-v4.4.214.csv)   |

## Summary

|      Version       |  Commits  |  Commits Tagged (%)  |  Regression <br>Rate (%)  |  Regression Rate<br>Range Estimation (%)  |  Zero-Lifetime Regressions <br>(lifetime <= 0) (%)  |  Half-life (days)  |
|:------------------:|:---------:|:--------------------:|:-------------------------:|:-----------------------------------------:|:---------------------------------------------------:|:------------------:|
| v4.19 to v4.19.104 |   12008   |         49%          |           3.8%            |                3.5% - 7.7%                |                         30%                         |         63         |
| v4.14 to v4.14.171 |   15699   |         44%          |           5.1%            |               4.4% - 11.6%                |                         26%                         |         78         |
|  v4.9 to v4.9.214  |   15762   |         41%          |           5.0%            |               4.5% - 12.3%                |                         25%                         |         90         |
|  v4.4 to v4.4.214  |   14301   |         37%          |           4.6%            |               4.1% - 12.6%                |                         28%                         |         82         |

## Missing Annotations

|      Version       |  Commits  |  Commits tagged  |  Commits tagged (%)  |
|:------------------:|:---------:|:----------------:|:--------------------:|
| v4.19 to v4.19.104 |   12008   |       5857       |         49%          |
| v4.14 to v4.14.171 |   15699   |       6901       |         44%          |
|  v4.9 to v4.9.214  |   15762   |       6417       |         41%          |
|  v4.4 to v4.4.214  |   14301   |       5227       |         37%          |

## Regression Lifetimes

|      Version       |  Regressions <br>(lifetime any)  |  Regressions <br>(lifetime == 0)  |  Regressions <br>(lifetime < 0)  |  Regressions <br>(lifetime <= 0) (%)  |
|:------------------:|:--------------------------------:|:---------------------------------:|:--------------------------------:|:-------------------------------------:|
| v4.19 to v4.19.104 |               649                |                191                |                5                 |                  30%                  |
| v4.14 to v4.14.171 |               1081               |                279                |                4                 |                  26%                  |
|  v4.9 to v4.9.214  |               1044               |                252                |                5                 |                  25%                  |
|  v4.4 to v4.4.214  |               912                |                253                |                2                 |                  28%                  |

## Multiple Fixes to One Regression

|      Version       |  Regressions <br>(lifetime > 0)  |  Regressions <br>(Fixes == 1)  |  Regressions <br>(Fixes == 2)  |  Regressions <br>(Fixes == 3)  |  Regressions <br>(Fixes >= 4)  |
|:------------------:|:--------------------------------:|:------------------------------:|:------------------------------:|:------------------------------:|:------------------------------:|
| v4.19 to v4.19.104 |               453                |              387               |               28               |               2                |               1                |
| v4.14 to v4.14.171 |               798                |              601               |               63               |               13               |               7                |
|  v4.9 to v4.9.214  |               787                |              638               |               50               |               10               |               4                |
|  v4.4 to v4.4.214  |               657                |              535               |               39               |               7                |               5                |