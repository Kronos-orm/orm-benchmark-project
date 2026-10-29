package com.kotlinorm.jimmerBenchmark

import com.kotlinorm.BenchmarkExecutor
import com.kotlinorm.FixtureRow
import com.kotlinorm.jimmerBenchmark.pojo.*
import org.babyfish.jimmer.kt.new
import org.babyfish.jimmer.sql.ast.mutation.SaveMode
import org.babyfish.jimmer.sql.dialect.MySqlDialect
import org.babyfish.jimmer.sql.kt.KSqlClient
import org.babyfish.jimmer.sql.kt.ast.expression.*
import org.babyfish.jimmer.sql.kt.newKSqlClient
import org.babyfish.jimmer.sql.runtime.ConnectionManager
import javax.sql.DataSource

class JimmerBenchmark : BenchmarkExecutor {
    private lateinit var dataSource: DataSource
    private lateinit var client: KSqlClient
    private var users: List<User> = emptyList()

    override fun init(dataSource: DataSource) {
        this.dataSource = dataSource
        client = newKSqlClient {
            setConnectionManager(ConnectionManager.simpleConnectionManager(dataSource))
            setDialect(MySqlDialect())
            setCaches { /* No entity, association or property caches are configured. */ }
            setScalarProvider(User::comment, ByteArrayScalarProvider())
        }
    }

    override fun queryEntities(firstId: Int, rowCount: Int): List<Any> =
        client.createQuery(User::class) {
            where(table.id ge firstId, table.id lt firstId + rowCount)
            orderBy(table.id.asc())
            select(table)
        }.execute()

    override fun queryMaps(firstId: Int, rowCount: Int): List<Map<String, Any?>> =
        client.createQuery(User::class) {
            where(table.id ge firstId, table.id lt firstId + rowCount)
            orderBy(table.id.asc())
            select(table)
        }.execute().map {
            // Jimmer has no native map result: entity + explicit conversion is disclosed.
            linkedMapOf(
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

    override fun queryNames(firstId: Int, rowCount: Int): List<String> =
        client.createQuery(User::class) {
            where(table.id ge firstId, table.id lt firstId + rowCount)
            orderBy(table.id.asc())
            select(table.name)
        }.execute()

    override fun prepareInsert(rows: List<FixtureRow>) {
        users = rows.map { row -> new(User::class).by {
                id = row.id
                uid = row.uid
                name = row.name
                age = row.age
                sex = row.sex
                height = row.height
                weight = row.weight
                score = row.score
                salary = row.salary
                birthday = row.birthday
                email = row.email
                address = row.address
                comment = row.comment
                version = row.version
                deleted = row.deleted
                createTime = row.createTime
                updateTime = row.updateTime
        } }
    }

    override fun insertTransaction(): Int = dataSource.connection.use { connection ->
        connection.autoCommit = false
        try {
            val entities = client.entities.forConnection(connection)
            val affected = users.sumOf { user ->
                entities.save(user, SaveMode.INSERT_ONLY).totalAffectedRowCount
            }
            connection.commit()
            affected
        } catch (failure: Throwable) {
            connection.rollback()
            throw failure
        }
    }

    override fun close() { users = emptyList() }
}
