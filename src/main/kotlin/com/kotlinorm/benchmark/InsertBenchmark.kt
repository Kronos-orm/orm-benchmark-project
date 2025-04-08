package com.kotlinorm.benchmark

import com.kolinorm.ktormBenchmark.KtromExecutor
import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.benchmark.utils.DataSourceHelper.dataSource
import com.kotlinorm.benchmark.utils.DataSourceHelper.sync
import com.kotlinorm.benchmark.utils.faker
import com.kotlinorm.jpaBenchmark.JpaExecutor
import com.kotlinorm.kronosBenchmark.KronosExecutor
import com.kotlinorm.mybatisBenchmark.MybatisExecutor
import kotlinx.benchmark.Benchmark
import kotlinx.benchmark.Param
import kotlinx.benchmark.Scope
import kotlinx.benchmark.Setup
import kotlinx.benchmark.State
import kotlinx.benchmark.TearDown

@State(Scope.Benchmark)
class InsertBenchmark {
    @Param("Jpa", "Kronos", "Ktorm", "Mybatis")
    lateinit var ormType: String

    @Param("10000")
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
            "Jpa" -> JpaExecutor()
            "Kronos" -> KronosExecutor()
            "Mybatis" -> MybatisExecutor()
            "Ktorm" -> KtromExecutor()
            else -> throw IllegalArgumentException("Unsupported ORM type: $ormType")
        }
        executor.init(dataSource, listOfUserMap)
    }

    @Benchmark
    fun insertUsers() {
        executor.executeInsert()
    }

    @TearDown
    fun cleanup() {
        executor.onDestroy()
    }
}