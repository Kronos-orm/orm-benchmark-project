package com.kotlinorm.kronosBenchmark

import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.Kronos
import com.kotlinorm.KronosBasicWrapper
import com.kotlinorm.kronosBenchmark.pojo.User
import com.kotlinorm.orm.delete.delete
import com.kotlinorm.orm.insert.InsertClause.Companion.execute
import com.kotlinorm.orm.insert.insert
import com.kotlinorm.orm.select.select
import javax.sql.DataSource

class KronosExecutor(
    private val users: List<User> = listOf()
) : BenchmarkExecutor {

    override fun init(dataSource: DataSource) {
        val wrapper = KronosBasicWrapper(dataSource)
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

    override fun querySingleEntity() {
        User(id = 1).select().by { it.id }.queryOne()
//        User(id = 1).select().by { it.id }.queryMap()
    }

    override fun executeInsert1000() {
        users.insert().execute()
    }

    override fun onDestroy() {
        User().delete().where { it.id != 1 }.execute()
    }
}