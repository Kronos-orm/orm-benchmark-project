package com.kotlinorm.benchmark

import com.kolinorm.ktormBenchmark.KtromExecutor
import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.benchmark.utils.DataSourceHelper.dataSource
import com.kotlinorm.benchmark.utils.DataSourceHelper.sync
import com.kotlinorm.benchmark.utils.faker
import com.kotlinorm.jimmerBenchmark.JimmerBenchmark
import com.kotlinorm.jpaBenchmark.JpaExecutor
import com.kotlinorm.kronosBenchmark.KronosExecutor
import com.kotlinorm.mybatisBenchmark.MybatisExecutor
import kotlinx.benchmark.Benchmark
import kotlinx.benchmark.Scope
import kotlinx.benchmark.Setup
import kotlinx.benchmark.State
import kotlinx.benchmark.TearDown
import org.openjdk.jmh.annotations.Param

@State(Scope.Benchmark)
class QueryMapBenchmark {
    @Param("Jimmer", "Jpa", "Kronos", "Ktorm", "Mybatis")
    lateinit var ormType: String

    @Param("100000")
    lateinit var count: Integer

    lateinit var executor: BenchmarkExecutor

    @Setup
    fun prepare() {
        sync()
        val listOfUserMap = (0 until count.toInt()).map { i ->
            mapOf(
                "name" to faker.name().fullName(),
                "age" to faker.number().numberBetween(18, 100),
            )
        }
        executor = when (ormType) {
            "Jimmer" -> JimmerBenchmark()
            "Jpa" -> JpaExecutor()
            "Kronos" -> KronosExecutor()
            "Ktorm" -> KtromExecutor()
            "Mybatis" -> MybatisExecutor()
            else -> throw IllegalArgumentException("Unsupported ORM type: $ormType")
        }
        executor.init(dataSource, listOfUserMap)
        executor.executeInsert()
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