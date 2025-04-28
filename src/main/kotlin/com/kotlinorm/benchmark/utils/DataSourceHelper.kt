package com.kotlinorm.benchmark.utils

import com.alibaba.druid.pool.DruidDataSource
import com.kolinorm.ktormBenchmark.KtromExecutor
import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.jimmerBenchmark.JimmerBenchmark
import com.kotlinorm.jpaBenchmark.JpaExecutor
import com.kotlinorm.kronosBenchmark.KronosExecutor
import com.kotlinorm.mybatisBenchmark.MybatisExecutor
import java.time.LocalDate
import java.time.LocalDateTime
import javax.sql.DataSource

object DataSourceHelper {
    val globalExecutor = KronosExecutor()
    val dataSource: DataSource by lazy {
        DruidDataSource().apply {
            url =
                "jdbc:mysql://localhost:3306/kronos_benchmark?useUnicode=true&characterEncoding=utf8&serverTimezone=UTC&useSSL=false&rewriteBatchedStatements=true"
            username = System.getenv("db.username")
            password = System.getenv("db.password")
            driverClassName = "com.mysql.cj.jdbc.Driver"
            initialSize = 5
            maxActive = 10
        }
    }

    fun sync() {
        KronosExecutor().init(dataSource, listOf())
    }

    fun randomData(count: Int) = (0 until count).map { i ->
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
            "createTime" to LocalDateTime.ofInstant(faker.timeAndDate().past(), java.time.ZoneOffset.UTC),
            "updateTime" to LocalDateTime.ofInstant(faker.timeAndDate().past(), java.time.ZoneOffset.UTC)
        )
    }

    fun createExecutor(ormType: String, data: List<Map<String, Any>> = listOf()): BenchmarkExecutor {
        return when (ormType) {
            "Jimmer" -> JimmerBenchmark()
            "Jpa" -> JpaExecutor()
            "Kronos" -> KronosExecutor()
            "Ktorm" -> KtromExecutor()
            "Mybatis" -> MybatisExecutor()
            else -> throw IllegalArgumentException("Unsupported ORM type: $ormType")
        }.apply {
            init(dataSource, data)
        }
    }

    val dataPool by lazy {
        randomData(100000)
    }
}