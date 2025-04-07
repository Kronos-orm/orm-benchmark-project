package com.kolinorm.ktormBenchmark

import com.kolinorm.ktormBenchmark.pojo.User
import com.kolinorm.ktormBenchmark.table.Users
import com.kotlinorm.BenchmarkExecutor
import org.ktorm.database.Database
import org.ktorm.dsl.eq
import org.ktorm.dsl.from
import org.ktorm.dsl.map
import org.ktorm.dsl.mapTo
import org.ktorm.dsl.select
import org.ktorm.dsl.where
import org.ktorm.entity.find
import org.ktorm.entity.first
import org.ktorm.entity.sequenceOf
import org.ktorm.logging.NoOpLogger
import javax.sql.DataSource

/**
 *@program: orm-benchmark-project
 *@author: Jieyao Lu
 *@description:
 *@create: 2025/4/7 10:19
 **/
class KtromExecutor : BenchmarkExecutor {

    private lateinit var database: Database
    private lateinit var users: List<Map<String, Any>>

    val Database.user get() = this.sequenceOf(Users)

    override fun init(dataSource: DataSource, listOfMap: List<Map<String, Any>>) {
        database = Database.connect(dataSource, logger = NoOpLogger)
    }

    override fun prepareData(listOfMap: List<Map<String, Any>>) {
        users = listOfMap.toList()
    }

    override fun querySingleEntity() {
        database.user.find { it.id eq 1 }

    }

    override fun querySingleMap() {
        val user = database.user.find { it.id eq 1 }
    }

    override fun executeInsert() {
        TODO("Not yet implemented")
    }

    override fun onDestroy() {
        TODO("Not yet implemented")
    }
}