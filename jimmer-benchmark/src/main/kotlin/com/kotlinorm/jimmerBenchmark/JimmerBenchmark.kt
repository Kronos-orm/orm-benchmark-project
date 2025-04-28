package com.kotlinorm.jimmerBenchmark

import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.jimmerBenchmark.pojo.User
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
import java.math.BigDecimal
import java.time.LocalDate
import java.time.LocalDateTime
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
//            addScalarProvider(ByteArrayScalarProvider())
            setScalarProvider(User::comment, ByteArrayScalarProvider())
        }
        prepareData(listOfMap)
    }

    override fun prepareData(listOfMap: List<Map<String, Any>>) {
        users = listOfMap.map { map ->
            new(User::class).by {
                uid = map["uid"] as Long
                name = map["name"].toString()
                age = map["age"] as Int
                sex = map["sex"] as Boolean
                height = map["height"] as Float
                weight = map["weight"] as Float
                score = map["score"] as Double
                salary = map["salary"] as BigDecimal
                birthday = map["birthday"] as LocalDate
                email = map["email"].toString()
                address = map["address"].toString()
                comment = map["comment"] as ByteArray
                version = map["version"] as Int
                deleted = map["deleted"] as Boolean
                createTime = map["createTime"] as LocalDateTime
                updateTime = map["updateTime"] as LocalDateTime
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
            select(table)
        }.fetchOne().let {
            mapOf(
                "id" to it.id,
                "uid" to it.uid,
                "name" to it.name,
                "age" to it.age,
                "sex" to it.sex,
                "height" to it.height,
                "weight" to it.weight,
                "score" to it.score,
                "salary" to it.salary,
                "birthday" to it.birthday,
                "email" to it.email,
                "address" to it.address,
                "comment" to it.comment,
                "version" to it.version,
                "deleted" to it.deleted,
                "createTime" to it.createTime,
                "updateTime" to it.updateTime
            )
        }
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