package com.kotlinorm.jimmerBenchmark

import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.jimmerBenchmark.pojo.User
import org.babyfish.jimmer.sql.dialect.MySqlDialect
import org.babyfish.jimmer.sql.kt.KSqlClient
import org.babyfish.jimmer.sql.kt.newKSqlClient
import javax.sql.DataSource

/**
 * @description:
 * @author: lujieyao
 * @date: 2025/4/9
 */
class JimmerBenchmark : BenchmarkExecutor {

    private lateinit var sqlClient: KSqlClient
    private lateinit var users: List<User>

    override fun init(
        dataSource: DataSource,
        listOfMap: List<Map<String, Any>>
    ) {
        sqlClient = newKSqlClient {
            setConnectionManager { dataSource }
            setCaches { null }
            setDialect(MySqlDialect())
        }
    }

    override fun prepareData(listOfMap: List<Map<String, Any>>) {
        TODO("Not yet implemented")
    }

    override fun querySingleEntity() {
        TODO("Not yet implemented")
    }

    override fun querySingleMap() {
        TODO("Not yet implemented")
    }

    override fun executeInsert() {
        TODO("Not yet implemented")
    }

    override fun onDestroy() {
        TODO("Not yet implemented")
    }
}