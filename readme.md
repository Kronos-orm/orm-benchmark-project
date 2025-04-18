# Benchmark Report

## InsertBenchmark.insertUsers

![com.kotlinorm.benchmark.InsertBenchmark.insertUsers Performance Chart](./images/com_kotlinorm_benchmark_InsertBenchmark_insertUsers_count10000.png)

| ORM Type | Counts | Score (ops/s) | Error (±) |
----------|--------|---------------|-----------|
 Ktorm | 10000 | 9.86 | ±0.11 |
 Mybatis | 10000 | 9.52 | ±0.20 |
 Kronos | 10000 | 9.32 | ±0.19 |
 Jpa | 10000 | 0.66 | ±0.00 |
 Jimmer | 10000 | 0.08 | ±0.02 |


---
## QueryEntityBenchmark.querySingleEntity

![com.kotlinorm.benchmark.QueryEntityBenchmark.querySingleEntity Performance Chart](./images/com_kotlinorm_benchmark_QueryEntityBenchmark_querySingleEntity_count100000.png)

| ORM Type | Counts | Score (ops/s) | Error (±) |
----------|--------|---------------|-----------|
 Jpa | 100000 | 7,143.75 | ±201.61 |
 Jimmer | 100000 | 6,678.94 | ±181.75 |
 Kronos | 100000 | 6,674.42 | ±335.95 |
 Ktorm | 100000 | 6,036.34 | ±264.45 |
 Mybatis | 100000 | 3,387.89 | ±147.68 |


---
## QueryFieldBenchmark.querySingleField

![com.kotlinorm.benchmark.QueryFieldBenchmark.querySingleField Performance Chart](./images/com_kotlinorm_benchmark_QueryFieldBenchmark_querySingleField_count100000.png)

| ORM Type | Counts | Score (ops/s) | Error (±) |
----------|--------|---------------|-----------|
 Ktorm | 100000 | 7,228.47 | ±322.11 |
 Jimmer | 100000 | 6,879.50 | ±247.65 |
 Kronos | 100000 | 6,778.60 | ±230.03 |
 Jpa | 100000 | 5,775.03 | ±179.70 |
 Mybatis | 100000 | 3,161.99 | ±70.21 |


---
## QueryMapBenchmark.querySingleMap

![com.kotlinorm.benchmark.QueryMapBenchmark.querySingleMap Performance Chart](./images/com_kotlinorm_benchmark_QueryMapBenchmark_querySingleMap_count100000.png)

| ORM Type | Counts | Score (ops/s) | Error (±) |
----------|--------|---------------|-----------|
 Ktorm | 100000 | 7,224.59 | ±356.52 |
 Kronos | 100000 | 6,649.26 | ±267.41 |
 Jimmer | 100000 | 6,584.35 | ±204.54 |
 Jpa | 100000 | 5,136.80 | ±151.47 |
 Mybatis | 100000 | 3,074.66 | ±142.75 |


---
