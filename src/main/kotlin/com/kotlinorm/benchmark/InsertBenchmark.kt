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
import kotlinx.datetime.LocalDate
import org.openjdk.jmh.annotations.Param

@State(Scope.Benchmark)
class InsertBenchmark {
    @Param("Jimmer", "Jpa", "Kronos", "Ktorm", "Mybatis")
    lateinit var ormType: String

    @Param("10000")
    lateinit var count: Integer

    lateinit var executor: BenchmarkExecutor

    @Setup
    fun prepare() {
        sync()
        val listOfUserMap = (0 until count.toInt()).map { i ->
            mapOf(
                "uid" to faker.random().nextLong(),
                "name" to faker.name().fullName(),
                "age" to faker.number().numberBetween(18, 100),
                "sex" to faker.random().nextBoolean(),
                "height" to faker.number().numberBetween(1.5, 2.0).toFloat(),
                "weight" to faker.number().numberBetween(40.0, 100.0).toFloat(),
                "score" to faker.number().randomDouble(2, 0, 100),
                "salary" to faker.number().randomDouble(2, 0, 1000000).toBigDecimal(),
                "birthday" to LocalDate.parse(faker.timeAndDate().birthday(18, 99, "yyyy-MM-dd")),
                "email" to faker.internet().emailAddress(),
                "address" to faker.address().fullAddress(),
                "comment" to faker.lorem().characters(100).toByteArray(),
                "version" to 0,
                "deleted" to false,
                "createTime" to faker.timeAndDate().past(),
                "updateTime" to faker.timeAndDate().past()
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