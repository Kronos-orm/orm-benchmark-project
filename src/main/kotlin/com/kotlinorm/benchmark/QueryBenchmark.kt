package com.kotlinorm.benchmark

import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.benchmark.DataSourceHelper.dataSource
import com.kotlinorm.jpaBenchmark.JpaInitializer
import com.kotlinorm.kronosBenchmark.KronosExecutor
import com.kotlinorm.mybatisBenchmark.MybatisInitializer
import com.kotlinorm.mybatisBenchmark.dao.User
import kotlinx.benchmark.Benchmark
import kotlinx.benchmark.Scope
import kotlinx.benchmark.Setup
import kotlinx.benchmark.State
import kotlinx.benchmark.TearDown
import org.openjdk.jmh.annotations.Param

@State(Scope.Benchmark)
class QueryBenchmark {
    @Param("Jpa", "Kronos", "Mybatis")
    lateinit var ormType: String
    lateinit var executor: BenchmarkExecutor

    @Setup
    fun prepare() {
        executor = when (ormType) {
            "Jpa" -> JpaInitializer()
            "Kronos" -> KronosExecutor()
            "Mybatis" -> MybatisInitializer()
            else -> throw IllegalArgumentException("Unsupported ORM type: $ormType")
        }
        executor.init(dataSource)
        executor.executeInsert1000()
    }

    @Benchmark
    fun querySingleEntity() {
        executor.querySingleEntity()
    }

    @TearDown
    fun cleanup() {
        executor.onDestroy()
    }
}