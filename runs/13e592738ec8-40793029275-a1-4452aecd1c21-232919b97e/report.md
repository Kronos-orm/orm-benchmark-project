# ORM benchmark: detailed results

## Measurement conditions

- Each scenario uses five independent JVM forks/blocks. All six adapters within a block share one runner VM and dedicated MySQL, in a fixed-seed randomized order.
- Queries fully materialize their result and include connection/session lifetime. Tables contain 1,000 / 100,000 rows; queries return 1 / 100 rows across entity / map / scalar and hot / uniform access.
- Writes time the first row-wise INSERT transaction on a reset empty table, including execution and COMMIT. TRUNCATE, object preparation and result checks occur outside timing.
- All measurement values are averaged within each fork. Five fork means determine the mean and Student t 95% interval; all samples and failure states remain available.
- Paired ratios are other latency / Kronos latency, using matching-block log-ratios and 95% intervals. The table n is the independent fork count.
- Environment evidence records the JDK, database image, driver, pool and caches. Separate correctness checks verify SQL, materialized values and resource lifetime.
- Reads: 5 × 2s warmup, 10 × 2s measurement; µs/query.
- Writes: 2000 warmup transactions, 300 SingleShot measurements, batch size = 1; µs/transaction.

| Environment | Configuration |
| --- | --- |
| jdk | `"21.0.10+7-LTS"` |
| javaVendor | `"Eclipse Adoptium"` |
| os | `"Linux 7.0.0-1017-azure"` |
| architecture | `"amd64"` |
| mysql | `"8.0.46"` |
| driver | `"MySQL Connector/J mysql-connector-j-9.7.0 (Revision: 0aade1f13bcc98faf7dda5c02e782481eb291f62)"` |
| pool | `{"isolation": "READ_COMMITTED", "housekeepingIntervalMillis": 86400000, "maximum": 1, "testWhileIdle": false, "initial": 1, "poolPreparedStatements": false, "autoCommit": true}` |
| innodb_buffer_pool_size | `"268435456"` |
| innodb_flush_log_at_trx_commit | `"1"` |
| sync_binlog | `"1"` |
| transaction_isolation | `"READ-COMMITTED"` |
| time_zone | `"+00:00"` |

## Dependency versions

| Component | Version |
| --- | --- |
| Kotlin | 2.4.21 |
| Kronos | 0.4.0 |
| MySQL Connector/J | 9.7.0 |
| Druid | 1.2.28 |
| Hibernate ORM | 7.4.14.Final |
| Jimmer | 0.12.4 |
| Ktorm | 4.2.1 |
| MyBatis-Plus | 3.5.18.1 |
| MyBatis core | 3.5.19 |
| KSP | 2.3.12 |
| Jackson | 2.22.4 |
| Jackson annotations | 2.22 |
| JMH | 1.37 |

## Scenario comparisons

### entity · 100,000 table rows · 1 returned · hot

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 171.364 | [112.628, 230.099] | 5 | 0.629 [0.567, 0.698] |
| Kronos | 268.237 | [203.284, 333.189] | 5 | 1.000 (reference) |
| Hibernate | 187.680 | [126.435, 248.926] | 5 | 0.691 [0.632, 0.755] |
| Jimmer | 191.527 | [129.200, 253.855] | 5 | 0.705 [0.641, 0.775] |
| Ktorm | 225.658 | [156.880, 294.437] | 5 | 0.834 [0.783, 0.888] |
| MyBatis-Plus | 228.143 | [162.156, 294.131] | 5 | 0.845 [0.800, 0.892] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-389cffd1c36614.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/19-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/19-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/19-read.pdf)


### entity · 1,000 table rows · 1 returned · hot

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 219.872 | [204.170, 235.574] | 5 | 0.676 [0.643, 0.710] |
| Kronos | 325.065 | [316.951, 333.178] | 5 | 1.000 (reference) |
| Hibernate | 239.417 | [227.668, 251.166] | 5 | 0.736 [0.717, 0.756] |
| Jimmer | 244.524 | [236.334, 252.714] | 5 | 0.752 [0.744, 0.760] |
| Ktorm | 277.333 | [264.334, 290.331] | 5 | 0.853 [0.832, 0.874] |
| MyBatis-Plus | 283.300 | [275.801, 290.800] | 5 | 0.872 [0.860, 0.883] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-66d2cf4c0c8b4b.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/08-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/08-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/08-read.pdf)


### entity · 100,000 table rows · 100 returned · hot

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 385.696 | [314.583, 456.809] | 5 | 0.184 [0.181, 0.188] |
| Kronos | 2,089.542 | [1,720.532, 2,458.552] | 5 | 1.000 (reference) |
| Hibernate | 625.197 | [501.040, 749.353] | 5 | 0.299 [0.288, 0.310] |
| Jimmer | 510.863 | [412.219, 609.507] | 5 | 0.244 [0.238, 0.250] |
| Ktorm | 853.430 | [716.458, 990.402] | 5 | 0.409 [0.402, 0.416] |
| MyBatis-Plus | 575.319 | [472.958, 677.679] | 5 | 0.275 [0.269, 0.282] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-4f1c2af082c4df.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/12-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/12-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/12-read.pdf)


### entity · 1,000 table rows · 100 returned · hot

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 448.741 | [410.167, 487.315] | 5 | 0.189 [0.180, 0.200] |
| Kronos | 2,364.974 | [2,275.371, 2,454.576] | 5 | 1.000 (reference) |
| Hibernate | 734.890 | [694.204, 775.577] | 5 | 0.311 [0.304, 0.318] |
| Jimmer | 593.188 | [555.364, 631.012] | 5 | 0.251 [0.243, 0.258] |
| Ktorm | 964.638 | [917.663, 1,011.614] | 5 | 0.408 [0.399, 0.416] |
| MyBatis-Plus | 664.757 | [634.195, 695.320] | 5 | 0.281 [0.274, 0.289] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-ee0ea834af09f3.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/21-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/21-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/21-read.pdf)


### map · 100,000 table rows · 1 returned · hot

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 190.301 | [138.913, 241.688] | 5 | 0.651 [0.592, 0.716] |
| Kronos | 289.617 | [231.974, 347.261] | 5 | 1.000 (reference) |
| Hibernate | 203.340 | [150.468, 256.212] | 5 | 0.696 [0.646, 0.751] |
| Jimmer | 215.039 | [159.388, 270.691] | 5 | 0.736 [0.685, 0.792] |
| Ktorm | 244.659 | [187.264, 302.055] | 5 | 0.841 [0.804, 0.880] |
| MyBatis-Plus | 266.830 | [205.584, 328.077] | 5 | 0.917 [0.879, 0.958] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-2d7b0b8490cd48.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/11-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/11-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/11-read.pdf)


### map · 1,000 table rows · 1 returned · hot

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 203.624 | [144.863, 262.384] | 5 | 0.691 [0.648, 0.736] |
| Kronos | 292.205 | [220.387, 364.024] | 5 | 1.000 (reference) |
| Hibernate | 214.902 | [153.538, 276.266] | 5 | 0.730 [0.688, 0.774] |
| Jimmer | 224.406 | [160.485, 288.327] | 5 | 0.762 [0.719, 0.807] |
| Ktorm | 250.913 | [179.875, 321.951] | 5 | 0.852 [0.806, 0.901] |
| MyBatis-Plus | 264.974 | [192.736, 337.211] | 5 | 0.902 [0.867, 0.938] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-2fd6ff081830c5.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/23-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/23-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/23-read.pdf)


### map · 100,000 table rows · 100 returned · hot

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 473.293 | [377.284, 569.301] | 5 | 0.253 [0.230, 0.279] |
| Kronos | 1,859.816 | [1,605.711, 2,113.922] | 5 | 1.000 (reference) |
| Hibernate | 628.486 | [503.703, 753.269] | 5 | 0.336 [0.310, 0.364] |
| Jimmer | 601.262 | [524.708, 677.816] | 5 | 0.324 [0.310, 0.338] |
| Ktorm | 715.860 | [619.335, 812.384] | 5 | 0.385 [0.372, 0.399] |
| MyBatis-Plus | 659.187 | [578.946, 739.428] | 5 | 0.355 [0.342, 0.368] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-326098b24e79de.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/07-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/07-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/07-read.pdf)


### map · 1,000 table rows · 100 returned · hot

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 449.534 | [367.363, 531.706] | 5 | 0.252 [0.245, 0.259] |
| Kronos | 1,791.761 | [1,426.773, 2,156.750] | 5 | 1.000 (reference) |
| Hibernate | 603.002 | [489.410, 716.594] | 5 | 0.337 [0.328, 0.347] |
| Jimmer | 605.729 | [496.816, 714.642] | 5 | 0.339 [0.328, 0.351] |
| Ktorm | 676.235 | [555.327, 797.144] | 5 | 0.379 [0.365, 0.393] |
| MyBatis-Plus | 635.528 | [516.715, 754.342] | 5 | 0.355 [0.345, 0.366] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-a6306ac2ca9e0e.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/13-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/13-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/13-read.pdf)


### scalar · 100,000 table rows · 1 returned · hot

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 153.154 | [62.779, 243.530] | 5 | 0.703 [0.652, 0.758] |
| Kronos | 213.127 | [97.889, 328.365] | 5 | 1.000 (reference) |
| Hibernate | 158.635 | [64.840, 252.430] | 5 | 0.728 [0.674, 0.786] |
| Jimmer | 165.712 | [66.506, 264.919] | 5 | 0.758 [0.694, 0.827] |
| Ktorm | 167.816 | [68.147, 267.485] | 5 | 0.769 [0.710, 0.834] |
| MyBatis-Plus | 185.687 | [75.328, 296.046] | 5 | 0.851 [0.785, 0.923] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-ef799f203123da.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/06-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/06-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/06-read.pdf)


### scalar · 1,000 table rows · 1 returned · hot

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 137.471 | [52.093, 222.850] | 5 | 0.704 [0.644, 0.771] |
| Kronos | 189.971 | [87.505, 292.437] | 5 | 1.000 (reference) |
| Hibernate | 142.766 | [54.931, 230.602] | 5 | 0.733 [0.671, 0.800] |
| Jimmer | 147.696 | [57.808, 237.585] | 5 | 0.761 [0.707, 0.819] |
| Ktorm | 148.106 | [56.523, 239.689] | 5 | 0.760 [0.697, 0.828] |
| MyBatis-Plus | 164.061 | [67.798, 260.323] | 5 | 0.851 [0.808, 0.896] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-e8dd171fd78882.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/17-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/17-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/17-read.pdf)


### scalar · 100,000 table rows · 100 returned · hot

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 204.419 | [99.453, 309.384] | 5 | 0.633 [0.620, 0.647] |
| Kronos | 321.509 | [159.877, 483.141] | 5 | 1.000 (reference) |
| Hibernate | 212.237 | [102.544, 321.930] | 5 | 0.657 [0.640, 0.674] |
| Jimmer | 217.632 | [104.312, 330.952] | 5 | 0.672 [0.655, 0.690] |
| Ktorm | 229.650 | [111.496, 347.804] | 5 | 0.711 [0.699, 0.724] |
| MyBatis-Plus | 246.944 | [116.368, 377.519] | 5 | 0.761 [0.733, 0.789] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-162302f54f299e.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/16-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/16-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/16-read.pdf)


### scalar · 1,000 table rows · 100 returned · hot

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 187.422 | [91.878, 282.966] | 5 | 0.621 [0.595, 0.647] |
| Kronos | 302.219 | [149.562, 454.877] | 5 | 1.000 (reference) |
| Hibernate | 198.003 | [97.961, 298.046] | 5 | 0.656 [0.636, 0.677] |
| Jimmer | 199.220 | [95.093, 303.346] | 5 | 0.657 [0.631, 0.684] |
| Ktorm | 210.834 | [105.397, 316.272] | 5 | 0.700 [0.675, 0.725] |
| MyBatis-Plus | 225.799 | [106.936, 344.662] | 5 | 0.742 [0.721, 0.764] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-fb4c231795a654.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/03-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/03-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/03-read.pdf)


### entity · 100,000 table rows · 1 returned · uniform

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 174.905 | [116.410, 233.400] | 5 | 0.636 [0.575, 0.703] |
| Kronos | 271.114 | [206.735, 335.493] | 5 | 1.000 (reference) |
| Hibernate | 190.961 | [129.564, 252.357] | 5 | 0.696 [0.638, 0.759] |
| Jimmer | 193.687 | [132.423, 254.951] | 5 | 0.706 [0.648, 0.769] |
| Ktorm | 229.578 | [165.049, 294.107] | 5 | 0.842 [0.798, 0.888] |
| MyBatis-Plus | 231.167 | [164.770, 297.563] | 5 | 0.847 [0.800, 0.897] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-96581a4c38bf6f.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/22-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/22-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/22-read.pdf)


### entity · 1,000 table rows · 1 returned · uniform

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 223.634 | [216.072, 231.196] | 5 | 0.666 [0.603, 0.735] |
| Kronos | 336.066 | [313.268, 358.865] | 5 | 1.000 (reference) |
| Hibernate | 242.031 | [231.541, 252.521] | 5 | 0.721 [0.646, 0.803] |
| Jimmer | 253.493 | [244.662, 262.323] | 5 | 0.755 [0.731, 0.780] |
| Ktorm | 282.076 | [275.831, 288.321] | 5 | 0.840 [0.772, 0.914] |
| MyBatis-Plus | 295.402 | [272.354, 318.449] | 5 | 0.879 [0.868, 0.889] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-5ee33db85efb78.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/05-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/05-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/05-read.pdf)


### entity · 100,000 table rows · 100 returned · uniform

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 395.806 | [329.629, 461.983] | 5 | 0.189 [0.183, 0.196] |
| Kronos | 2,086.602 | [1,784.772, 2,388.432] | 5 | 1.000 (reference) |
| Hibernate | 634.064 | [512.304, 755.824] | 5 | 0.303 [0.285, 0.322] |
| Jimmer | 520.228 | [420.924, 619.532] | 5 | 0.248 [0.237, 0.260] |
| Ktorm | 856.174 | [725.929, 986.419] | 5 | 0.410 [0.405, 0.415] |
| MyBatis-Plus | 586.083 | [491.912, 680.253] | 5 | 0.281 [0.275, 0.286] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-beac2cd61f0db3.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/09-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/09-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/09-read.pdf)


### entity · 1,000 table rows · 100 returned · uniform

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 467.322 | [437.649, 496.994] | 5 | 0.197 [0.180, 0.216] |
| Kronos | 2,369.742 | [2,272.747, 2,466.738] | 5 | 1.000 (reference) |
| Hibernate | 733.649 | [693.500, 773.798] | 5 | 0.309 [0.300, 0.319] |
| Jimmer | 616.741 | [593.129, 640.353] | 5 | 0.260 [0.244, 0.278] |
| Ktorm | 1,023.645 | [923.310, 1,123.980] | 5 | 0.431 [0.380, 0.490] |
| MyBatis-Plus | 694.160 | [652.357, 735.964] | 5 | 0.293 [0.268, 0.320] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-2ebfbd994d716c.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/01-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/01-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/01-read.pdf)


### map · 100,000 table rows · 1 returned · uniform

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 192.676 | [140.269, 245.082] | 5 | 0.649 [0.591, 0.713] |
| Kronos | 293.817 | [236.986, 350.649] | 5 | 1.000 (reference) |
| Hibernate | 206.889 | [154.205, 259.573] | 5 | 0.698 [0.648, 0.752] |
| Jimmer | 219.109 | [164.996, 273.221] | 5 | 0.740 [0.692, 0.792] |
| Ktorm | 250.079 | [192.347, 307.812] | 5 | 0.847 [0.801, 0.895] |
| MyBatis-Plus | 266.177 | [207.589, 324.765] | 5 | 0.903 [0.869, 0.938] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-e85ec098659b5a.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/24-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/24-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/24-read.pdf)


### map · 1,000 table rows · 1 returned · uniform

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 204.483 | [145.551, 263.415] | 5 | 0.692 [0.646, 0.741] |
| Kronos | 292.883 | [222.101, 363.666] | 5 | 1.000 (reference) |
| Hibernate | 215.813 | [153.991, 277.636] | 5 | 0.730 [0.683, 0.780] |
| Jimmer | 225.097 | [160.618, 289.576] | 5 | 0.762 [0.713, 0.814] |
| Ktorm | 253.268 | [183.465, 323.070] | 5 | 0.859 [0.818, 0.903] |
| MyBatis-Plus | 267.770 | [195.494, 340.047] | 5 | 0.909 [0.873, 0.948] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-62e66b0fd40beb.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/14-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/14-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/14-read.pdf)


### map · 100,000 table rows · 100 returned · uniform

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 462.384 | [402.251, 522.517] | 5 | 0.249 [0.240, 0.259] |
| Kronos | 1,858.021 | [1,600.451, 2,115.592] | 5 | 1.000 (reference) |
| Hibernate | 617.695 | [535.141, 700.249] | 5 | 0.333 [0.328, 0.337] |
| Jimmer | 624.041 | [548.570, 699.512] | 5 | 0.336 [0.320, 0.353] |
| Ktorm | 697.707 | [604.857, 790.557] | 5 | 0.376 [0.373, 0.378] |
| MyBatis-Plus | 669.579 | [600.732, 738.427] | 5 | 0.361 [0.347, 0.376] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-f7b70658d1b820.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/26-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/26-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/26-read.pdf)


### map · 1,000 table rows · 100 returned · uniform

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 453.450 | [370.526, 536.375] | 5 | 0.252 [0.243, 0.261] |
| Kronos | 1,803.401 | [1,443.437, 2,163.366] | 5 | 1.000 (reference) |
| Hibernate | 605.652 | [494.743, 716.560] | 5 | 0.337 [0.326, 0.347] |
| Jimmer | 609.844 | [502.162, 717.526] | 5 | 0.339 [0.329, 0.350] |
| Ktorm | 680.494 | [555.822, 805.167] | 5 | 0.378 [0.366, 0.390] |
| MyBatis-Plus | 637.846 | [518.555, 757.136] | 5 | 0.354 [0.344, 0.365] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-f29228c447ee49.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/04-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/04-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/04-read.pdf)


### scalar · 100,000 table rows · 1 returned · uniform

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 156.196 | [65.956, 246.435] | 5 | 0.709 [0.655, 0.767] |
| Kronos | 215.567 | [102.311, 328.823] | 5 | 1.000 (reference) |
| Hibernate | 162.611 | [69.328, 255.895] | 5 | 0.739 [0.686, 0.797] |
| Jimmer | 168.914 | [70.432, 267.397] | 5 | 0.765 [0.702, 0.833] |
| Ktorm | 170.509 | [72.343, 268.675] | 5 | 0.774 [0.719, 0.835] |
| MyBatis-Plus | 188.087 | [81.863, 294.311] | 5 | 0.858 [0.810, 0.909] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-56a2ae6589f36d.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/20-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/20-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/20-read.pdf)


### scalar · 1,000 table rows · 1 returned · uniform

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 139.944 | [51.956, 227.933] | 5 | 0.696 [0.621, 0.779] |
| Kronos | 194.628 | [91.577, 297.679] | 5 | 1.000 (reference) |
| Hibernate | 143.283 | [56.565, 230.001] | 5 | 0.718 [0.657, 0.785] |
| Jimmer | 147.890 | [55.001, 240.779] | 5 | 0.734 [0.651, 0.828] |
| Ktorm | 150.019 | [58.027, 242.011] | 5 | 0.750 [0.679, 0.827] |
| MyBatis-Plus | 165.681 | [67.606, 263.756] | 5 | 0.834 [0.773, 0.900] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-fbc4325c64ade1.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/18-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/18-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/18-read.pdf)


### scalar · 100,000 table rows · 100 returned · uniform

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 209.192 | [102.030, 316.353] | 5 | 0.632 [0.610, 0.654] |
| Kronos | 328.669 | [166.701, 490.637] | 5 | 1.000 (reference) |
| Hibernate | 216.424 | [105.431, 327.418] | 5 | 0.654 [0.634, 0.674] |
| Jimmer | 222.822 | [107.309, 338.335] | 5 | 0.672 [0.647, 0.697] |
| Ktorm | 234.220 | [118.107, 350.334] | 5 | 0.712 [0.708, 0.716] |
| MyBatis-Plus | 253.954 | [119.168, 388.739] | 5 | 0.762 [0.719, 0.808] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-e7c5aad6299971.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/15-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/15-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/15-read.pdf)


### scalar · 1,000 table rows · 100 returned · uniform

Unit: us/query

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 187.960 | [97.103, 278.817] | 5 | 0.606 [0.559, 0.656] |
| Kronos | 307.906 | [171.449, 444.363] | 5 | 1.000 (reference) |
| Hibernate | 200.414 | [105.331, 295.497] | 5 | 0.647 [0.617, 0.678] |
| Jimmer | 200.327 | [100.389, 300.264] | 5 | 0.643 [0.598, 0.690] |
| Ktorm | 210.954 | [106.310, 315.598] | 5 | 0.676 [0.620, 0.737] |
| MyBatis-Plus | 224.041 | [101.839, 346.243] | 5 | 0.707 [0.609, 0.821] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/read-3d3c85d0a4d9fb.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/02-read.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/02-read.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/02-read.pdf)


### First transaction on reset empty table · 100 rows

Unit: us/transaction

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 21,534.790 | [20,871.232, 22,198.347] | 5 | 0.777 [0.767, 0.788] |
| Kronos | 27,701.035 | [26,765.454, 28,636.617] | 5 | 1.000 (reference) |
| Hibernate | 23,030.796 | [22,241.965, 23,819.627] | 5 | 0.831 [0.825, 0.838] |
| Jimmer | 24,731.373 | [24,080.821, 25,381.926] | 5 | 0.893 [0.883, 0.903] |
| Ktorm | 24,977.061 | [24,134.384, 25,819.738] | 5 | 0.902 [0.898, 0.905] |
| MyBatis-Plus | 41,377.573 | [40,322.375, 42,432.770] | 5 | 1.494 [1.478, 1.510] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/write-555800087b5048.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/10-write.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/10-write.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/10-write.pdf)


### First transaction on reset empty table · 1 rows

Unit: us/transaction

| Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos) |
| --- | ---: | ---: | ---: | ---: |
| JDBC | 1,458.634 | [936.786, 1,980.481] | 5 | 0.839 [0.761, 0.925] |
| Kronos | 1,729.519 | [1,153.584, 2,305.454] | 5 | 1.000 (reference) |
| Hibernate | 1,748.788 | [1,118.669, 2,378.907] | 5 | 1.006 [0.939, 1.077] |
| Jimmer | 1,703.838 | [1,151.123, 2,256.552] | 5 | 0.986 [0.942, 1.032] |
| Ktorm | 1,589.726 | [1,014.156, 2,165.297] | 5 | 0.914 [0.835, 1.001] |
| MyBatis-Plus | 1,790.049 | [1,164.799, 2,415.300] | 5 | 1.031 [0.981, 1.085] |

[JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/cases/write-1665681faf2a53.json) · [PNG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/25-write.png) · [SVG](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/25-write.svg) · [PDF](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/figures/25-write.pdf)



## Run and reproduction evidence

UTC: 2026-10-29T00:19:04.660463+00:00 — 2026-10-29T01:32:27.854476+00:00

Coverage: {"failedForkRuns": 0, "notRunForkRuns": 0, "passedForkRuns": 780, "plannedForkRuns": 780, "scenarioStates": {"COMPLETE": 156, "FAILED": 0, "NOT_RUN": 0, "PARTIAL": 0}}

[Kronos source / Kronos源码](https://github.com/Kronos-orm/Kronos-orm/tree/13e592738ec885ec6a233737ef501c221ab1daa4) · [Benchmark source / 基准源码](https://github.com/Kronos-orm/orm-benchmark-project/tree/1497bd730b6d598879fb09774fe6d48e4c9e2f03) · [Execution controller source / 执行控制器源码](https://github.com/Kronos-orm/orm-benchmark-project/tree/64aee4260df853cf8d6d6b25c883abb6240b4b01) · [Producer run / 构建运行](https://github.com/Kronos-orm/orm-benchmark-project/actions/runs/40637176946/attempts/1) · [Measurement run / 测量运行](https://github.com/Kronos-orm/orm-benchmark-project/actions/runs/40793029275/attempts/1)

- [English analysis (Markdown)](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/report-en.md)
- [中文详细分析 (Markdown)](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/report-zh-CN.md)
- [Statistics JSON](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/analysis/summary.json)
- [Statistics CSV](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/analysis/summary.csv)
- [Methodology](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/methodology.md)
- [Commands](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/commands.jsonl)
- [Build manifest](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/build-manifest.json)
- [Source snapshot](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/source-4452aecd1c213bf5-jvm.tar.gz)
- [Diagnostics index](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/diagnostics-index.json)
- [Real-secret scan receipts and derivation hashes](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/audit-provenance.json)
- [Execution controller source snapshot](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/controller-source-64aee4260df853cf.tar.gz)
- [Frozen execution protocol](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/execution-protocol.json)
- [Shared execution context](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/execution-context.json)

[English analysis](https://github.com/Kronos-orm/orm-benchmark-project/blob/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/report-en.md) · [中文详细分析](https://github.com/Kronos-orm/orm-benchmark-project/blob/result/runs/13e592738ec8-40793029275-a1-4452aecd1c21-232919b97e/report-zh-CN.md)
