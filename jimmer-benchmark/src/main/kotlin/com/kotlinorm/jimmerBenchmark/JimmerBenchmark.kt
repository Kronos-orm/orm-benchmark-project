package com.kotlinorm.jimmerBenchmark

import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.jimmerBenchmark.pojo.User
import com.kotlinorm.jimmerBenchmark.pojo.age
import com.kotlinorm.jimmerBenchmark.pojo.by
import com.kotlinorm.jimmerBenchmark.pojo.id
import com.kotlinorm.jimmerBenchmark.pojo.name
import org.babyfish.jimmer.kt.new
import org.babyfish.jimmer.sql.ast.mutation.SaveMode
import org.babyfish.jimmer.sql.dialect.MySqlDialect
import org.babyfish.jimmer.sql.kt.KSqlClient
import org.babyfish.jimmer.sql.kt.ast.expression.eq
import org.babyfish.jimmer.sql.kt.newKSqlClient
import org.babyfish.jimmer.sql.runtime.ConnectionManager
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
            setConnectionManager(
                ConnectionManager.simpleConnectionManager(dataSource)
            )
            setCaches { null }
            setDialect(MySqlDialect())
            setDefaultBatchSize(10000)
            setDefaultListBatchSize(10000)
        }
        prepareData(listOfMap)
    }

    override fun prepareData(listOfMap: List<Map<String, Any>>) {
        users = listOfMap.map { map ->
            new(User::class).by {
                name = map["name"] as String
                age = map["age"] as Int
            }
        }
    }

    override fun querySingleEntity() {
        sqlClient.createQuery(User::class) {
            where(table.id eq 1)
            select(table)
        }.fetchOne()
    }

    override fun querySingleMap() {
        sqlClient.createQuery(User::class) {
            where(table.id eq 1)
            select(
                table.id,
                table.name,
                table.age
            )
        }.fetchOne()
    }

    override fun querySingleField() {
        sqlClient.createQuery(User::class) {
            where(table.id eq 1)
            select(table.name)
        }.fetchOne()
    }

    override fun executeInsert() {
        sqlClient.entities.saveEntities(users) {
            setMode(SaveMode.INSERT_ONLY)
        }
    }

    override fun onDestroy() {
        sqlClient.javaClient.connectionManager.execute { conn ->
            conn.createStatement().use { stmt ->
                stmt.executeUpdate("TRUNCATE TABLE tb_user")
            }
            null
        }
    }
}