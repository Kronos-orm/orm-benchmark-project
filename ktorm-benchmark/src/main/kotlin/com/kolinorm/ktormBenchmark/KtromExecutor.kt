package com.kolinorm.ktormBenchmark

import com.kolinorm.ktormBenchmark.table.Users
import com.kotlinorm.BenchmarkExecutor
import org.ktorm.database.Database
import org.ktorm.dsl.BatchInsertStatementBuilder
import org.ktorm.dsl.batchInsert
import org.ktorm.dsl.eq
import org.ktorm.dsl.from
import org.ktorm.dsl.map
import org.ktorm.dsl.select
import org.ktorm.dsl.where
import org.ktorm.entity.find
import org.ktorm.entity.sequenceOf
import org.ktorm.logging.NoOpLogger
import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime
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
    private lateinit var batchInsertStatementBuilder: BatchInsertStatementBuilder<Users>.() -> Unit

    val Database.user get() = this.sequenceOf(Users)

    override fun init(dataSource: DataSource, listOfMap: List<Map<String, Any>>) {
        prepareData(listOfMap)
        database = Database.connect(dataSource, logger = NoOpLogger)
    }

    override fun prepareData(listOfMap: List<Map<String, Any>>) {
        users = listOfMap.toList()
        batchInsertStatementBuilder = {
            for (user in users) {
                item {
                    set(it.uid, user["uid"].toString().toLong())
                    set(it.name, user["name"].toString())
                    set(it.age, user["age"]?.toString()?.toInt())
                    set(it.sex, user["sex"].toString().toBoolean())
                    set(it.height, user["height"].toString().toFloat())
                    set(it.weight, user["weight"].toString().toFloat())
                    set(it.score, user["score"].toString().toDouble())
                    set(it.salary, user["salary"].toString().toBigDecimal())
                    set(it.birthday, LocalDate.parse(user["birthday"].toString()))
                    set(it.email, user["email"].toString())
                    set(it.address, user["address"].toString())
                    set(it.comment, user["comment"].toString().toByteArray())
                    set(it.version, user["version"].toString().toInt())
                    set(it.deleted, user["deleted"].toString().toBoolean())
                    set(it.createTime, LocalDateTime.ofInstant(user["createTime"] as Instant, java.time.ZoneOffset.UTC))
                    set(it.updateTime, LocalDateTime.ofInstant(user["updateTime"] as Instant, java.time.ZoneOffset.UTC))
                }
            }
        }
    }

    override fun querySingleEntity() {
        database.user.find { it.id eq 1 }
    }

    override fun querySingleMap() {
        database
            .from(Users)
            .select()
            .where { Users.id eq 1 }
            .map {
                Users.columns.associate { col -> col.name to it[col]!! }
            }
            .first()
    }

    override fun querySingleField() {
        database
            .from(Users)
            .select(Users.name)
            .where { Users.id eq 1 }
            .map { it[Users.name]!! }
            .first()
    }

    override fun executeInsert() {
        database.batchInsert(Users, batchInsertStatementBuilder)
    }

    override fun onDestroy() {
        database.useConnection { conn ->
            conn.createStatement().use { stmt ->
                stmt.executeUpdate("TRUNCATE TABLE tb_user")
            }
        }
    }
}