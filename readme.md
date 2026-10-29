# ORM benchmark · 性能对比

JVM · MySQL · 26 scenarios · 6 adapters · 5 independent blocks

[English analysis](https://github.com/Kronos-orm/orm-benchmark-project/blob/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/report-en.md) · [中文详细分析](https://github.com/Kronos-orm/orm-benchmark-project/blob/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/report-zh-CN.md) · [Statistics JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/analysis/summary.json) · [Raw evidence](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/evidence.zip)

## Overview

Completed fork runs: **780 / 780**. Failed: 0; not run: 0. Figures show fork means and 95% mean intervals.

## 实验概览

已完成 **780 / 780** 个 fork；失败 0，未运行 0。图中展示独立 fork 均值与 95% 均值区间。

JDK: `21.0.10+7-LTS` · MySQL: `8.0.46`

## Key scenarios · 关键场景

### entity · 100,000 table rows · 1 returned · uniform

![entity · 100,000 table rows · 1 returned · uniform](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/22-read.png)

[Data and raw references · 明细](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-96581a4c38bf6f.json)

### entity · 100,000 table rows · 100 returned · uniform

![entity · 100,000 table rows · 100 returned · uniform](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/09-read.png)

[Data and raw references · 明细](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-beac2cd61f0db3.json)

### First transaction on reset empty table · 100 rows

![First transaction on reset empty table · 100 rows](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/10-write.png)

[Data and raw references · 明细](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/write-555800087b5048.json)

## Method · 方法

All adapters use the same SQL workload, data, driver and pool settings. Complete result checks run before measurement. Measurements are averaged within each fork; paired comparisons use the same block.

各适配器使用相同 SQL 工作量、数据、驱动与连接池配置，测量前完整核对结果。先在 fork 内汇总，再按同一 block 配对比较。

[Method and parameters](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/methodology.md) · [CSV](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/analysis/summary.csv)
