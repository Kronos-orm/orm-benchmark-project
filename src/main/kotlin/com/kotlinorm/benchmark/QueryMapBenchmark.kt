package com.kotlinorm.benchmark

import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.benchmark.utils.DataSourceHelper.createExecutor
import com.kotlinorm.benchmark.utils.DataSourceHelper.dataPool
import com.kotlinorm.benchmark.utils.DataSourceHelper.dataSource
import com.kotlinorm.benchmark.utils.DataSourceHelper.globalExecutor
import com.kotlinorm.benchmark.utils.DataSourceHelper.randomData
import com.kotlinorm.benchmark.utils.DataSourceHelper.sync
import kotlinx.benchmark.Benchmark
import kotlinx.benchmark.Measurement
import kotlinx.benchmark.Scope
import kotlinx.benchmark.Setup
import kotlinx.benchmark.State
import kotlinx.benchmark.TearDown
import kotlinx.benchmark.Warmup
import org.openjdk.jmh.annotations.Fork
import org.openjdk.jmh.annotations.Param
import java.util.concurrent.*

@State(Scope.Benchmark)
@Warmup(iterations = 5)
@Measurement(iterations = 10, time = 1, timeUnit = TimeUnit.SECONDS)
@Fork(1)
class QueryMapBenchmark {
    @Param("Jimmer", "Jpa", "Kronos", "Ktorm", "Mybatis")
    lateinit var ormType: String

    @Param("100000")
    lateinit var count: Integer

    lateinit var executor: BenchmarkExecutor

    @Setup
    fun prepare() {
        sync()
        val listOfUserMap = dataPool.slice(0..<count.toInt()).toList()
        globalExecutor.init(dataSource, listOfUserMap)
        globalExecutor.executeInsert()
        executor = createExecutor(ormType)
    }

    @Benchmark
    fun querySingleMap() {
        executor.querySingleMap()
    }

    @TearDown
    fun cleanup() {
        executor.onDestroy()
    }
}