package com.kotlinorm.benchmark

import com.alibaba.druid.pool.DruidDataSource
import javax.sql.DataSource

object DataSourceHelper {
    val dataSource: DataSource by lazy {
        DruidDataSource().apply {
            url =
                "mysql://localhost:3306/kronos-benchmark-test?useUnicode=true&characterEncoding=utf8&serverTimezone=UTC&useSSL=false&rewriteBatchedStatements=true"
            username = System.getenv("db.username")
            password = System.getenv("db.password")
            driverClassName = "com.mysql.cj.jdbc.Driver"
            initialSize = 5
            maxActive = 10
        }
    }
}