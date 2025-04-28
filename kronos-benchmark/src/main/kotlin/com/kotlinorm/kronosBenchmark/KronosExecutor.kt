package com.kotlinorm.kronosBenchmark

import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.Kronos
import com.kotlinorm.KronosBasicWrapper
import com.kotlinorm.functions.bundled.exts.PolymerizationFunctions.count
import com.kotlinorm.kronosBenchmark.pojo.User
import com.kotlinorm.orm.database.table
import com.kotlinorm.orm.insert.InsertClause.Companion.execute
import com.kotlinorm.orm.insert.insert
import com.kotlinorm.orm.select.select
import com.kotlinorm.utils.Extensions.mapperTo
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
        users = listOfMap.map { User().fromMapData(it) }
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