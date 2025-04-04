package com.kotlinorm.benchmark

import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.benchmark.DataSourceHelper.dataSource
import com.kotlinorm.jpaBenchmark.JpaInitializer
import com.kotlinorm.kronosBenchmark.KronosExecutor
import com.kotlinorm.mybatisBenchmark.MybatisInitializer
import kotlinx.benchmark.Benchmark
import kotlinx.benchmark.Param
import kotlinx.benchmark.Scope
import kotlinx.benchmark.Setup
import kotlinx.benchmark.State
import kotlinx.benchmark.TearDown
import net.datafaker.Faker

@State(Scope.Benchmark)
class InsertBenchmark {
    @Param("Jpa", "Kronos", "Mybatis")
    lateinit var ormType: String
    lateinit var executor: BenchmarkExecutor

    @Setup
    fun prepare() {
        val listOfUserMap = (0 until 1000).map { i ->
            mapOf(
                "name" to faker.name().fullName(),
                "age" to faker.number().numberBetween(18, 100),
            )
        }
        executor = when (ormType) {
            "Jpa" -> JpaInitializer()
            "Kronos" -> KronosExecutor()
            "Mybatis" -> MybatisInitializer()
            else -> throw IllegalArgumentException("Unsupported ORM type: $ormType")
        }
        executor.init(dataSource, listOfUserMap)
    }

    @Benchmark
    fun insert1000Users() {
        executor.executeInsert()
    }

    @TearDown
    fun cleanup() {
        executor.onDestroy()
    }
}