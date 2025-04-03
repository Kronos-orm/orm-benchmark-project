package com.kotlinorm.benchmark

import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.benchmark.DataSourceHelper.dataSource
import com.kotlinorm.kronosBenchmark.KronosExecutor
import kotlinx.benchmark.Benchmark
import kotlinx.benchmark.Param
import kotlinx.benchmark.Scope
import kotlinx.benchmark.Setup
import kotlinx.benchmark.State
import kotlinx.benchmark.TearDown

@State(Scope.Benchmark)
class InsertBenchmark {
    @Param("Kronos")
    lateinit var ormType: String
    lateinit var executor: BenchmarkExecutor

    @Setup
    fun prepare() {
        executor = when (ormType) {
            "Kronos" -> KronosExecutor()
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