# Benchmark Report

## InsertBenchmark.insertUsers

![com.kotlinorm.benchmark.InsertBenchmark.insertUsers Performance Chart](./images/com_kotlinorm_benchmark_InsertBenchmark_insertUsers_count10000.png)

| ORM Type | Counts | Score (ops/s) | Error (±) |
----------|--------|---------------|-----------|
 Ktorm | 10000 | 9.81 | ±0.16 |
 Mybatis | 10000 | 9.43 | ±0.17 |
 Kronos | 10000 | 9.26 | ±0.25 |
 Jpa | 10000 | 0.68 | ±0.00 |


---
## QueryEntityBenchmark.querySingleEntity

![com.kotlinorm.benchmark.QueryEntityBenchmark.querySingleEntity Performance Chart](./images/com_kotlinorm_benchmark_QueryEntityBenchmark_querySingleEntity_count100000.png)

| ORM Type | Counts | Score (ops/s) | Error (±) |
----------|--------|---------------|-----------|
 Jpa | 100000 | 7,264.50 | ±310.52 |
 Kronos | 100000 | 6,699.26 | ±217.46 |
 Ktorm | 100000 | 6,191.73 | ±323.29 |
 Mybatis | 100000 | 3,451.82 | ±97.80 |


---
## QueryFieldBenchmark.querySingleField

![com.kotlinorm.benchmark.QueryFieldBenchmark.querySingleField Performance Chart](./images/com_kotlinorm_benchmark_QueryFieldBenchmark_querySingleField_count100000.png)

| ORM Type | Counts | Score (ops/s) | Error (±) |
----------|--------|---------------|-----------|
 Ktorm | 100000 | 7,465.53 | ±234.11 |
 Kronos | 100000 | 6,826.51 | ±384.19 |
 Jpa | 100000 | 5,701.55 | ±115.01 |
 Mybatis | 100000 | 3,230.08 | ±154.53 |


---
## QueryMapBenchmark.querySingleMap

![com.kotlinorm.benchmark.QueryMapBenchmark.querySingleMap Performance Chart](./images/com_kotlinorm_benchmark_QueryMapBenchmark_querySingleMap_count100000.png)

| ORM Type | Counts | Score (ops/s) | Error (±) |
----------|--------|---------------|-----------|
 Ktorm | 100000 | 7,463.69 | ±299.62 |
 Kronos | 100000 | 6,774.36 | ±307.45 |
 Jpa | 100000 | 5,071.59 | ±164.87 |
 Mybatis | 100000 | 3,165.63 | ±122.75 |


---
