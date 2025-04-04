package com.kotlinorm.benchmark

import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.benchmark.DataSourceHelper.dataSource
import com.kotlinorm.jpaBenchmark.JpaInitializer
import com.kotlinorm.kronosBenchmark.KronosExecutor
import com.kotlinorm.kronosBenchmark.pojo.User
import com.kotlinorm.mybatisBenchmark.MybatisInitializer
import kotlinx.benchmark.Benchmark
import kotlinx.benchmark.Param
import kotlinx.benchmark.Scope
import kotlinx.benchmark.Setup
import kotlinx.benchmark.State
import kotlinx.benchmark.TearDown

@State(Scope.Benchmark)
class InsertBenchmark {
    @Param("Jpa", "Kronos", "Mybatis")
    lateinit var ormType: String
    lateinit var executor: BenchmarkExecutor

    @Setup
    fun prepare() {
        executor = when (ormType) {
            "Jpa" -> {
                JpaInitializer(
                    (0 until 1000).map { i ->
                        com.kotlinorm.jpaBenchmark.pojo.User(name = "testUser$i", age = (i + 18) % 100)
                    }
                )
            }
            "Kronos" -> {
                KronosExecutor(
                    (0 until 1000).map { i ->
                        User(name = "testUser$i", age = (i + 18) % 100)
                    }
                )
            }
            "Mybatis" -> {
                MybatisInitializer(
                    (0 until 1000).map { i ->
                        com.kotlinorm.mybatisBenchmark.dao.User(name = "testUser$i", age = (i + 18) % 100)
                    }
                )
            }
            else -> throw IllegalArgumentException("Unsupported ORM type: $ormType")
        }
        executor.init(dataSource)
    }

    @Benchmark
    fun insert1000Users() {
        executor.executeInsert1000()
    }

    @TearDown
    fun cleanup() {
        executor.onDestroy()
    }
}