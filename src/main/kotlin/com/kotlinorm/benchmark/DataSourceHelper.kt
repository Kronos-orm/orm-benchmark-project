package com.kotlinorm.benchmark

import com.alibaba.druid.pool.DruidDataSource
import com.kotlinorm.kronosBenchmark.KronosExecutor
import javax.sql.DataSource

object DataSourceHelper {
    val dataSource: DataSource by lazy {
        DruidDataSource().apply {
            url =
                "jdbc:mysql://localhost:3306/test?useUnicode=true&characterEncoding=utf8&serverTimezone=UTC&useSSL=false&rewriteBatchedStatements=true"
//            username = System.getenv("db.username")
//            password = System.getenv("db.password")
            username = "root"
            password = "rootroot"
            driverClassName = "com.mysql.cj.jdbc.Driver"
            initialSize = 5
            maxActive = 10
        }
    }

    fun sync() {
        KronosExecutor().apply {
            init(dataSource, listOf())
        }
    }
}