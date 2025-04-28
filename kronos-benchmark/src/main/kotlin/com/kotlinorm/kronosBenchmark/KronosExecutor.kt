package com.kotlinorm.kronosBenchmark

import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.Kronos
import com.kotlinorm.KronosBasicWrapper
import com.kotlinorm.kronosBenchmark.pojo.User
import com.kotlinorm.orm.database.table
import com.kotlinorm.orm.insert.InsertClause.Companion.execute
import com.kotlinorm.orm.insert.insert
import com.kotlinorm.orm.select.select
import java.math.BigDecimal
import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime
import javax.sql.DataSource

class KronosExecutor() : BenchmarkExecutor {
    private lateinit var wrapper: KronosBasicWrapper
    private lateinit var users: List<User>

    override fun init(dataSource: DataSource, listOfMap: List<Map<String, Any>>) {
        prepareData(listOfMap)
        wrapper = KronosBasicWrapper(dataSource)
        Kronos.init {
            // 设置字段命名策略为驼峰命名
            fieldNamingStrategy = lineHumpNamingStrategy
            // 设置表命名策略为驼峰命名
            tableNamingStrategy = lineHumpNamingStrategy
            // 设置数据源提供器
            Kronos.dataSource = { wrapper }
            strictSetValue = true
            logPath = listOf()
        }
        Kronos.dataSource.table.syncTable<User>()
    }

    override fun prepareData(listOfMap: List<Map<String, Any>>) {
        // 预处理数据
        users = listOfMap.map { map ->
            User(
                uid = map["uid"] as Long,
                name = map["name"].toString(),
                age = map["age"] as Int,
                sex = map["sex"] as Boolean,
                height = map["height"] as Float,
                weight = map["weight"] as Float,
                score = map["score"] as Double,
                salary = map["salary"] as BigDecimal,
                birthday = LocalDate.parse(map["birthday"].toString()),
                email = map["email"].toString(),
                address = map["address"].toString(),
                comment = map["comment"] as ByteArray,
                version = map["version"] as Int,
                deleted = map["deleted"] as Boolean,
                createTime = LocalDateTime.ofInstant(map["createTime"] as Instant, java.time.ZoneOffset.UTC),
                updateTime = LocalDateTime.ofInstant(map["updateTime"] as Instant, java.time.ZoneOffset.UTC)
            )
        }
    }

    override fun querySingleEntity() {
        User(id = 1).select().by { it.id }.queryOne()
    }

    override fun querySingleMap() {
        User(id = 1).select().by { it.id }.queryMap()
    }

    override fun querySingleField() {
        User(id = 1).select { it.name }.by { it.id }.queryOne<String>()
    }

    override fun executeInsert() {
        users.insert().execute()
    }

    override fun onDestroy() {
        wrapper.table.truncateTable<User>()
    }
}