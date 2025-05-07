# Benchmark Report

## InsertBenchmark.insertUsers

![com.kotlinorm.benchmark.InsertBenchmark.insertUsers Performance Chart](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/images/com_kotlinorm_benchmark_InsertBenchmark_insertUsers_count10000.png)

| ORM Type | Counts | Score (ops/s) | Error (±) |
----------|--------|---------------|-----------|
 Kronos | 10000 | 1.94 | ±0.04 |
 Mybatis | 10000 | 1.90 | ±0.01 |
 Ktorm | 10000 | 1.66 | ±0.01 |
 Jpa | 10000 | 0.45 | ±0.00 |
 Jimmer | 10000 | 0.07 | ±0.00 |


---
## QueryEntityBenchmark.querySingleEntity

![com.kotlinorm.benchmark.QueryEntityBenchmark.querySingleEntity Performance Chart](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/images/com_kotlinorm_benchmark_QueryEntityBenchmark_querySingleEntity_count100000.png)

| ORM Type | Counts | Score (ops/s) | Error (±) |
----------|--------|---------------|-----------|
 Jpa | 100000 | 5,684.59 | ±387.85 |
 Kronos | 100000 | 5,483.05 | ±394.12 |
 Jimmer | 100000 | 5,298.25 | ±251.04 |
 Ktorm | 100000 | 4,112.84 | ±141.46 |
 Mybatis | 100000 | 3,045.73 | ±166.96 |


---
## QueryFieldBenchmark.querySingleField

![com.kotlinorm.benchmark.QueryFieldBenchmark.querySingleField Performance Chart](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/images/com_kotlinorm_benchmark_QueryFieldBenchmark_querySingleField_count100000.png)

| ORM Type | Counts | Score (ops/s) | Error (±) |
----------|--------|---------------|-----------|
 Ktorm | 100000 | 7,246.90 | ±271.75 |
 Jimmer | 100000 | 7,124.14 | ±352.36 |
 Kronos | 100000 | 6,707.17 | ±547.52 |
 Jpa | 100000 | 5,890.41 | ±336.26 |
 Mybatis | 100000 | 3,265.44 | ±229.85 |


---
## QueryMapBenchmark.querySingleMap

![com.kotlinorm.benchmark.QueryMapBenchmark.querySingleMap Performance Chart](https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result/images/com_kotlinorm_benchmark_QueryMapBenchmark_querySingleMap_count100000.png)

| ORM Type | Counts | Score (ops/s) | Error (±) |
----------|--------|---------------|-----------|
 Ktorm | 100000 | 5,641.43 | ±301.99 |
 Jimmer | 100000 | 5,391.73 | ±249.48 |
 Kronos | 100000 | 5,330.97 | ±426.85 |
 Jpa | 100000 | 3,640.77 | ±140.45 |
 Mybatis | 100000 | 2,727.08 | ±153.82 |


---
