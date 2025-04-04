package com.kotlinorm.kronosBenchmark

import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.Kronos
import com.kotlinorm.KronosBasicWrapper
import com.kotlinorm.kronosBenchmark.pojo.User
import com.kotlinorm.orm.database.table
import com.kotlinorm.orm.insert.InsertClause.Companion.execute
import com.kotlinorm.orm.insert.insert
import com.kotlinorm.orm.select.select
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
    }

    override fun prepareData(listOfMap: List<Map<String, Any>>) {
        // 预处理数据
        users = listOfMap.map { map ->
            User(
                name = map["name"] as String,
                age = map["age"] as Int
            )
        }
    }

    override fun querySingleEntity() {
        User(id = 1).select().by { it.id }.queryOne()
    }

    override fun executeInsert() {
        users.insert().execute()
    }

    override fun onDestroy() {
        wrapper.table.truncateTable<User>()
    }
}